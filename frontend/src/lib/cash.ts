// Caja del mostrador: cuadre, egresos y cierre (RF-31 a RF-33; research R1, R3, R4 y R6 de
// la etapa 1.4). El esperado se calcula en el equipo con `computeReconciliation` de
// @sht/shared, la misma lógica del servidor, sobre los movimientos del detalle de la caja.
// Egresos y cierre viajan por la cola de salida, como la apertura y la venta.
import { computeReconciliation, formatDecimal, formatVes, uuidv7 } from "@sht/shared";
import type { ReconciliationRowResult } from "@sht/shared";

import { apiFetch } from "@/lib/api/client";
import type { Schemas } from "@/lib/api/client";
import type { DeviceRecord } from "@/lib/device/device-store";
import { deviceFetch } from "@/lib/device/use-device";
import { enqueue, waitFor } from "@/lib/outbox/outbox";
import type { OutboxRecord } from "@/lib/device/device-store";
import { methodLabel, PAYMENT_METHODS } from "@/lib/sales";

export type CashSessionDetail = Schemas["CashSessionDetail"];
export type CashSessionClosed = Schemas["CashSessionClosed"];
export type CashSessionSummary = Schemas["CashSessionSummary"];
export type CashOutflow = Schemas["CashOutflowOut"];
export type CashMovement = Schemas["CashMovementOut"];
export type ReconciliationRow = Schemas["ReconciliationRowOut"];

export const CASH_KIND_LABELS: Record<string, string> = {
  sale_payment: "Cobro",
  change: "Vuelto",
  void_refund: "Devolución por anulación",
  void_change: "Vuelto recuperado por anulación",
};

/** Monto en la moneda de su método: `Bs 1.234,56`, `12,50 USD`, `12,50 USDT`. */
export function formatMethodAmount(amount: string, currency: string): string {
  return currency === "VES" ? formatVes(amount) : `${formatDecimal(amount, 2)} ${currency}`;
}

/** Monto con punto decimal y hasta 2 decimales en céntimos exactos (sin `number`, ADR-0004). */
export function toCents(value: string): bigint {
  const match = /^(-?)(\d+)(?:\.(\d{1,2}))?$/.exec(value.trim());
  if (!match) throw new Error(`Monto inválido: ${value}`);
  const cents = BigInt(match[2]) * 100n + BigInt((match[3] ?? "").padEnd(2, "0"));
  return match[1] === "-" ? -cents : cents;
}

export function isCashMethod(code: string): boolean {
  return code === "cash_ves" || code === "cash_usd";
}

/** Detalle de la caja; con el equipo, para que el Vendedor vea la caja abierta de su equipo. */
export function getCashSession(id: string, device?: DeviceRecord | null): Promise<CashSessionDetail> {
  return device ? deviceFetch<CashSessionDetail>(device, `/cash-sessions/${id}`) : apiFetch<CashSessionDetail>(`/cash-sessions/${id}`);
}

/**
 * Cuadre calculado en el equipo (FR-007) con los movimientos y egresos del detalle. En una
 * caja abierta coincide con el del servidor; `counted` (montos con punto decimal) agrega
 * la diferencia en vivo, y un método sin contado cuenta como 0,00.
 */
export function reconcile(detail: CashSessionDetail, counted: Record<string, string> | null = null): (ReconciliationRowResult & { method_name: string })[] {
  const rows = computeReconciliation(
    PAYMENT_METHODS.map((method) => ({ code: method.code, currency: method.currency })),
    {
      opening_float_ves: detail.opening_float_ves,
      opening_float_usd: detail.opening_float_usd,
      movements: detail.movements
        .filter((movement) => !movement.after_close)
        .map((movement) => ({ method: movement.method, currency: movement.currency, kind: movement.kind, amount: movement.amount })),
      outflows: detail.outflows.map((outflow) => ({ method: outflow.method, amount: outflow.amount, voided: outflow.void !== null })),
      counted,
    },
  );
  return rows.map((row) => ({ ...row, method_name: methodLabel(row.method) }));
}

export type QueueOutcome<T> = { ok: true; result: T } | { ok: false; message: string };

async function sendThroughOutbox<T>(type: string, payload: Record<string, unknown>, pendingMessage: string): Promise<QueueOutcome<T>> {
  const id = await enqueue(type, payload);
  const record: OutboxRecord | null = await waitFor(id);
  if (record === null) return { ok: false, message: pendingMessage };
  if (record.status === "rejected") return { ok: false, message: record.error?.message ?? "La operación fue rechazada" };
  return { ok: true, result: record.result as T };
}

/** Registra un egreso por la cola (RF-32); la referencia solo en métodos que no son efectivo. */
export function enqueueOutflow(sessionId: string, method: string, amount: string, reason: string, reference: string | null): Promise<QueueOutcome<CashOutflow>> {
  return sendThroughOutbox<CashOutflow>(
    "cash_outflow.create",
    { id: uuidv7(), cash_session_id: sessionId, method, amount, reason, reference },
    "El egreso quedó pendiente de envío: se enviará al volver la conexión.",
  );
}

/** Cierra la caja del equipo por la cola (RF-31): envía el esperado que vio el usuario. */
export function enqueueClose(
  sessionId: string,
  rows: ReconciliationRowResult[],
  counted: Record<string, string>,
  note: string | null,
): Promise<QueueOutcome<CashSessionClosed>> {
  return sendThroughOutbox<CashSessionClosed>(
    "cash_session.close",
    {
      cash_session_id: sessionId,
      counts: rows.map((row) => ({ method: row.method, device_expected: row.expected, counted: counted[row.method] ?? "0.00" })),
      note,
    },
    "El cierre quedó pendiente de envío: se enviará al volver la conexión.",
  );
}

/** El Admin anula un egreso con la caja abierta (RF-33). */
export function voidOutflow(id: string, reason: string): Promise<CashOutflow> {
  return apiFetch<CashOutflow>(`/cash-outflows/${id}/void`, { method: "POST", body: { reason } });
}

/** El Admin cierra la caja de otro equipo (caja huérfana, R6); la observación es obligatoria. */
export function closeAsAdmin(sessionId: string, counted: Record<string, string>, note: string, device: DeviceRecord | null): Promise<CashSessionClosed> {
  const body = { counts: PAYMENT_METHODS.map((method) => ({ method: method.code, counted: counted[method.code] ?? "0.00" })), note };
  const options = { method: "POST" as const, body };
  return device
    ? deviceFetch<CashSessionClosed>(device, `/cash-sessions/${sessionId}/close`, options)
    : apiFetch<CashSessionClosed>(`/cash-sessions/${sessionId}/close`, options);
}
