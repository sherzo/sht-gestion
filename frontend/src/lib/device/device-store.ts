// Datos locales del equipo de mostrador en IndexedDB (ADR-0003; research R3, R4 y R5 de la
// etapa 1.3): la identidad del equipo con su token y su contador de ventas, y la cola de
// salida. Sobreviven a recargas y cierres de la app; borrar los datos del navegador
// obliga a registrar el equipo de nuevo (FR-004).
import Dexie from "dexie";
import type { Table } from "dexie";

export type DeviceRecord = {
  key: "current";
  id: string;
  name: string;
  series: string;
  token: string;
  /** Próximo correlativo de venta de la serie (RN-11). */
  nextSequence: number;
};

export type OutboxStatus = "pending" | "sent" | "rejected";

export type OutboxRecord = {
  id: string;
  type: string;
  payload: Record<string, unknown>;
  /** Hora del equipo al crear la operación (ISO con zona). */
  createdAt: string;
  status: OutboxStatus;
  result: unknown;
  error: { code: string; message: string } | null;
  attempts: number;
};

class MostradorDb extends Dexie {
  device!: Table<DeviceRecord, string>;
  outbox!: Table<OutboxRecord, string>;

  constructor() {
    super("sht-mostrador");
    this.version(1).stores({ device: "key", outbox: "id, status, createdAt" });
  }
}

let instance: MostradorDb | null = null;

/** La base local; solo existe en el navegador (el sitio es un export estático). */
export function localDb(): MostradorDb {
  instance ??= new MostradorDb();
  return instance;
}

export async function getDevice(): Promise<DeviceRecord | null> {
  return (await localDb().device.get("current")) ?? null;
}

export async function saveDevice(device: Omit<DeviceRecord, "key">): Promise<void> {
  await localDb().device.put({ ...device, key: "current" });
  // Pide al navegador no borrar los datos locales por falta de espacio (ADR-0003).
  try {
    await navigator.storage?.persist?.();
  } catch {
    // Si el navegador no lo permite, la app sigue funcionando.
  }
}

export async function clearDevice(): Promise<void> {
  await localDb().device.delete("current");
}

/** Toma el siguiente correlativo de la serie y lo reserva (RN-11). */
export async function takeSequenceNumber(): Promise<number> {
  const db = localDb();
  return db.transaction("rw", db.device, async () => {
    const device = await db.device.get("current");
    if (!device) throw new Error("Este equipo no está registrado");
    await db.device.update("current", { nextSequence: device.nextSequence + 1 });
    return device.nextSequence;
  });
}

/** Alinea el contador con el último correlativo que registró el servidor (research R5). */
export async function syncSequence(serverLast: number): Promise<void> {
  const db = localDb();
  await db.transaction("rw", db.device, async () => {
    const device = await db.device.get("current");
    if (device && device.nextSequence <= serverLast) {
      await db.device.update("current", { nextSequence: serverLast + 1 });
    }
  });
}
