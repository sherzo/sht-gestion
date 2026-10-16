"use client";

// Cierre de la caja del equipo (RF-31, RF-33; FR-008 a FR-010, FR-014; research R4 de la
// etapa 1.4): no se cierra con operaciones de la caja pendientes de envío o rechazadas sin
// descartar. Muestra el esperado por método, pide lo contado (efectivo) o verificado
// (electrónicos), calcula la diferencia en vivo y exige una observación si hay alguna. El
// cierre viaja por la cola con el esperado que vio el usuario; el servidor lo recalcula.
import { formatDate, formatDateTime, parseDecimalInput } from "@sht/shared";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { ReconciliationTable } from "@/components/cash/reconciliation-table";
import { RequireAuth } from "@/components/require-auth";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { TextAreaField } from "@/components/ui/field";
import { ApiError } from "@/lib/api/client";
import { CASH_KIND_LABELS, enqueueClose, formatMethodAmount, getCashSession, isCashMethod, reconcile, toCents } from "@/lib/cash";
import type { CashSessionDetail } from "@/lib/cash";
import type { DeviceRecord } from "@/lib/device/device-store";
import { useCounterDevice } from "@/lib/device/use-device";
import { useCashSessionAttention, waitsForOwner } from "@/lib/outbox/outbox";
import { PAYMENT_METHODS } from "@/lib/sales";

const NOTE_MIN = 5;
const NOTE_MAX = 500;
const OPERATION_LABELS: Record<string, string> = { "sale.create": "Venta", "cash_outflow.create": "Egreso" };

/** Cobros, vueltos y devoluciones de un método electrónico, para cotejar con el banco (FR-009). */
function ElectronicMovements({ detail }: { detail: CashSessionDetail }) {
  const electronic = PAYMENT_METHODS.filter((method) => !isCashMethod(method.code))
    .map((method) => ({ method, movements: detail.movements.filter((movement) => movement.method === method.code && !movement.after_close) }))
    .filter((group) => group.movements.length > 0);
  if (electronic.length === 0) return null;
  return (
    <section className="flex flex-col gap-2">
      <h2 className="text-lg font-semibold">Pagos electrónicos para verificar</h2>
      {electronic.map(({ method, movements }) => (
        <details key={method.code} className="rounded-xl border border-line bg-surface p-3">
          <summary className="min-h-11 cursor-pointer content-center font-medium">
            {method.name} ({movements.length})
          </summary>
          <ul className="mt-2 flex flex-col gap-1">
            {movements.map((movement, index) => (
              <li key={`${movement.sale.id}-${movement.kind}-${index}`} className="flex flex-wrap justify-between gap-2 border-t border-line pt-1">
                <span>
                  {movement.sale.number} · {CASH_KIND_LABELS[movement.kind] ?? movement.kind} · Ref. {movement.reference ?? "—"}
                </span>
                <span className="font-medium">{formatMethodAmount(movement.amount, movement.currency)}</span>
              </li>
            ))}
          </ul>
        </details>
      ))}
    </section>
  );
}

function CloseForm({ device, sessionId }: { device: DeviceRecord; sessionId: string }) {
  const router = useRouter();
  const attention = useCashSessionAttention(sessionId);
  const [detail, setDetail] = useState<CashSessionDetail | null>(null);
  const [texts, setTexts] = useState<Record<string, string>>({});
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      setDetail(await getCashSession(sessionId, device));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No se pudo cargar la caja");
    }
  }, [device, sessionId]);

  // Se pide el detalle de nuevo cuando la cola termina de enviar lo de esta caja.
  const pendingCount = attention.length;
  useEffect(() => {
    void load();
  }, [load, pendingCount]);

  const counted = useMemo(() => {
    const values: Record<string, string> = {};
    for (const [method, text] of Object.entries(texts)) {
      const parsed = text.trim() ? parseDecimalInput(text, 2) : null;
      if (parsed !== null) values[method] = parsed;
    }
    return values;
  }, [texts]);
  const invalid = Object.entries(texts).some(([, text]) => text.trim() && parseDecimalInput(text, 2) === null);
  const negative = Object.values(counted).some((value) => toCents(value) < 0n);

  if (error) return <Alert variant="danger">{error}</Alert>;
  if (!detail) return <p className="text-ink-muted">Cargando la caja…</p>;

  const rows = reconcile(detail, counted);
  const hasDifference = rows.some((row) => row.difference !== null && toCents(row.difference) !== 0n);
  const noteOk = note.trim().length === 0 ? !hasDifference : note.trim().length >= NOTE_MIN && note.trim().length <= NOTE_MAX;
  const blocked = attention.length > 0;

  async function submit() {
    setSaving(true);
    setError(null);
    const outcome = await enqueueClose(sessionId, rows, counted, note.trim() || null);
    setSaving(false);
    if (!outcome.ok) {
      setError(outcome.message);
      return;
    }
    router.push(`/caja/?cerrada=${sessionId}`);
  }

  return (
    <div className="flex flex-col gap-4">
      <p>
        Caja abierta por <strong>{detail.opened_by.full_name}</strong> el {formatDateTime(detail.opened_at)}.
      </p>
      {detail.opened_on_previous_day && <Alert variant="warning">Esta caja está abierta desde el {formatDate(detail.business_date)}.</Alert>}
      {blocked && (
        <Alert variant="warning">
          <p className="font-semibold">Antes de cerrar hay que enviar o descartar estas operaciones de la caja:</p>
          <ul className="mt-1 list-disc pl-5">
            {attention.map((record) => (
              <li key={record.id}>
                {OPERATION_LABELS[record.type] ?? record.type} del {formatDateTime(record.createdAt)}:{" "}
                {record.status === "rejected"
                  ? `rechazada (${record.error?.message ?? "sin detalle"}); quítala en "Pendientes de envío"`
                  : waitsForOwner(record)
                    ? "espera a que el usuario que la hizo vuelva a ingresar en este equipo"
                    : "pendiente de envío"}
              </li>
            ))}
          </ul>
          <p className="mt-1">Si el usuario no puede volver, el administrador puede cerrar esta caja desde Cajas.</p>
        </Alert>
      )}
      <ReconciliationTable
        rows={rows}
        caption="Cierre de caja: esperado, contado y diferencia por método"
        counting={{ values: texts, onChange: (method, text) => setTexts((current) => ({ ...current, [method]: text })) }}
      />
      <p className="text-sm text-ink-muted">Un campo en blanco cuenta como 0,00. Contado en efectivo; verificado contra el banco o el lote en los demás.</p>
      <ElectronicMovements detail={detail} />
      <TextAreaField
        label={hasDifference ? "Observación (obligatoria: hay diferencias)" : "Observación (opcional)"}
        value={note}
        maxLength={NOTE_MAX}
        hint={`De ${NOTE_MIN} a ${NOTE_MAX} caracteres. Explica las diferencias, por ejemplo un cambio de moneda en la gaveta.`}
        error={hasDifference && note.trim().length > 0 && note.trim().length < NOTE_MIN ? `Escribe al menos ${NOTE_MIN} caracteres` : undefined}
        onChange={(event) => setNote(event.target.value)}
      />
      {error && <Alert variant="danger">{error}</Alert>}
      <Button loading={saving} disabled={blocked || invalid || negative || !noteOk} onClick={() => void submit()}>
        Confirmar cierre
      </Button>
      <p className="text-sm text-ink-muted">El cierre no se puede modificar después: una corrección se hace con un movimiento nuevo en la próxima caja.</p>
    </div>
  );
}

function CloseContent() {
  const device = useCounterDevice();
  return (
    <AppShell>
      <h1 className="mb-4 text-2xl font-bold">Cerrar caja</h1>
      {device.status === "loading" && <p className="text-ink-muted">Cargando…</p>}
      {device.status === "offline" && <Alert variant="warning">{device.message}</Alert>}
      {(device.status === "unregistered" || device.status === "revoked") && (
        <Alert variant="warning">Este navegador no es un equipo de mostrador vigente: el administrador puede cerrar la caja desde Cajas.</Alert>
      )}
      {device.status === "ready" &&
        (device.server.open_cash_session ? (
          <CloseForm device={device.local} sessionId={device.server.open_cash_session.id} />
        ) : (
          <Alert variant="info">Este equipo no tiene la caja abierta.</Alert>
        ))}
    </AppShell>
  );
}

export default function CloseCashPage() {
  return (
    <RequireAuth roles={["admin", "seller"]}>
      <CloseContent />
    </RequireAuth>
  );
}
