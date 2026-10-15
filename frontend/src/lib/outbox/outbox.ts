// Cola de salida del mostrador (FR-017; ADR-0003, research R4 de la etapa 1.3). Toda
// operación (abrir caja, vender) se guarda primero en IndexedDB y después se envía, haya o
// no conexión: un solo camino de código. Cada operación lleva un UUIDv7 que el servidor
// usa como clave de idempotencia, así que reintentar nunca duplica una venta.
import { uuidv7 } from "@sht/shared";
import { liveQuery } from "dexie";
import { useEffect, useState } from "react";

import { ApiError, apiFetch } from "@/lib/api/client";
import { getDevice, localDb } from "@/lib/device/device-store";
import type { OutboxRecord } from "@/lib/device/device-store";

const BASE_DELAY_MS = 30_000;
const MAX_DELAY_MS = 5 * 60_000;
// Las operaciones enviadas se conservan unos días como historial local y luego se borran.
const KEEP_SENT_MS = 7 * 24 * 60 * 60_000;

let flushing: Promise<boolean> | null = null;
let retryTimer: ReturnType<typeof setTimeout> | null = null;
let failures = 0;
let started = false;
// Usuario con sesión en este equipo: solo se envían sus ventas (R17 de la etapa 1.3).
let currentUserId: string | null = null;

/** Rechazo permanente: el servidor lo guardó y lo repetirá igual (research R4). */
function isPermanent(error: ApiError): boolean {
  return error.status === 409 || error.status === 422 || error.code === "device_revoked";
}

/** Guarda la operación en la cola y empieza a enviarla. Devuelve su id. */
export async function enqueue(type: string, payload: Record<string, unknown>): Promise<string> {
  const id = uuidv7();
  await localDb().outbox.add({
    id,
    type,
    payload,
    createdAt: new Date().toISOString(),
    status: "pending",
    result: null,
    error: null,
    attempts: 0,
    userId: currentUserId,
  });
  void flush();
  return id;
}

async function sendOne(record: OutboxRecord, token: string): Promise<"done" | "stop"> {
  const outbox = localDb().outbox;
  try {
    const result = await apiFetch<unknown>("/sync/operations", {
      method: "POST",
      body: {
        id: record.id,
        operation_type: record.type,
        schema_version: 1,
        created_at: record.createdAt,
        payload: record.payload,
      },
      headers: { "X-Device-Token": token },
    });
    await outbox.update(record.id, { status: "sent", result, error: null, attempts: record.attempts + 1 });
    return "done";
  } catch (error) {
    if (error instanceof ApiError && isPermanent(error)) {
      await outbox.update(record.id, {
        status: "rejected",
        error: { code: error.code, message: error.message },
        attempts: record.attempts + 1,
      });
      return "done";
    }
    // Sin conexión, error del servidor o sesión vencida: se reintenta después.
    await outbox.update(record.id, { attempts: record.attempts + 1 });
    return "stop";
  }
}

/**
 * Una venta queda a nombre del usuario que la envía (R17): la de otro vendedor espera a
 * que su dueño vuelva a ingresar, en lugar de rechazarse y perderse. La apertura de caja
 * se envía con cualquier sesión, porque las ventas de esa caja dependen de ella.
 */
export function waitsForOwner(record: OutboxRecord): boolean {
  return record.type === "sale.create" && record.userId !== currentUserId;
}

/** Envía en orden las operaciones pendientes; devuelve false si hay que reintentar. */
async function runFlush(): Promise<boolean> {
  const device = await getDevice();
  if (!device || !currentUserId) return true;
  const pending = await localDb().outbox.where("status").equals("pending").sortBy("createdAt");
  for (const record of pending) {
    if (waitsForOwner(record)) continue;
    if ((await sendOne(record, device.token)) === "stop") return false;
  }
  const cutoff = new Date(Date.now() - KEEP_SENT_MS).toISOString();
  await localDb().outbox.where("createdAt").below(cutoff).and((record) => record.status === "sent").delete();
  return true;
}

/** Una sola ejecución a la vez; al terminar programa el próximo intento, con espera
 * creciente mientras siga fallando. */
export function flush(): Promise<boolean> {
  flushing ??= runFlush()
    .then((ok) => {
      scheduleRetry(!ok);
      return ok;
    })
    .finally(() => {
      flushing = null;
    });
  return flushing;
}

function scheduleRetry(failed: boolean): void {
  if (retryTimer) clearTimeout(retryTimer);
  failures = failed ? failures + 1 : 0;
  const delay = Math.min(BASE_DELAY_MS * 2 ** Math.max(failures - 1, 0), MAX_DELAY_MS);
  retryTimer = setTimeout(() => void flush(), delay);
}

/** Arranca los reintentos: al volver la conexión y periódicamente (sin Background Sync). */
export function startOutbox(userId: string): void {
  currentUserId = userId;
  if (typeof window === "undefined") return;
  if (!started) {
    started = true;
    window.addEventListener("online", () => void flush());
  }
  void flush();
}

/** Espera el resultado de una operación de la cola; null si sigue pendiente al vencer el plazo. */
export async function waitFor(id: string, timeoutMs = 15_000): Promise<OutboxRecord | null> {
  const deadline = Date.now() + timeoutMs;
  for (;;) {
    const record = await localDb().outbox.get(id);
    if (record && record.status !== "pending") return record;
    if (Date.now() >= deadline) return null;
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
}

/** Operaciones pendientes y rechazadas, más recientes primero, actualizadas en vivo. */
export function useOutboxAttention(): OutboxRecord[] {
  const [records, setRecords] = useState<OutboxRecord[]>([]);
  useEffect(() => {
    const subscription = liveQuery(() =>
      localDb().outbox.where("status").anyOf("pending", "rejected").reverse().sortBy("createdAt"),
    ).subscribe({ next: setRecords, error: () => setRecords([]) });
    return () => subscription.unsubscribe();
  }, []);
  return records;
}

/** Cuántas operaciones están pendientes de envío o rechazadas. */
export function usePendingCount(): number {
  return useOutboxAttention().length;
}

/** Quita de la lista una operación rechazada que el usuario ya revisó. */
export async function dismissRejected(id: string): Promise<void> {
  const record = await localDb().outbox.get(id);
  if (record?.status === "rejected") await localDb().outbox.delete(id);
}

/** true si quedan operaciones sin enviar (aviso antes de cerrar sesión, ADR-0003). */
export async function hasPending(): Promise<boolean> {
  return (await localDb().outbox.where("status").equals("pending").count()) > 0;
}
