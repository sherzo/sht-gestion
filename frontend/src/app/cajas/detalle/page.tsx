"use client";

// Detalle de una caja (`?id=`; RF-27, RF-31 a RF-33; FR-018, FR-019, FR-023 a FR-025;
// research R6, R7, R9 y R13 de la etapa 1.4): datos de apertura y cierre, cuadre por método
// con lo contado y las diferencias, movimientos con su referencia y su venta, egresos, ventas
// anuladas después del cierre y operaciones que llegaron después. El Admin anula egresos con
// la caja abierta y cierra desde aquí la caja de otro equipo (caja huérfana), con
// observación obligatoria. El Vendedor llega aquí solo a la caja de su equipo o a un cierre
// suyo de hoy.
import { formatDate, formatDateTime, parseDecimalInput } from "@sht/shared";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { OutflowList } from "@/components/cash/outflow-list";
import { ReconciliationTable } from "@/components/cash/reconciliation-table";
import { RequireAuth } from "@/components/require-auth";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import type { Column } from "@/components/ui/data-table";
import { TextAreaField } from "@/components/ui/field";
import { StatusChip } from "@/components/ui/status-chip";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/use-auth";
import { CASH_KIND_LABELS, closeAsAdmin, formatMethodAmount, getCashSession, reconcile, toCents } from "@/lib/cash";
import type { CashMovement, CashSessionDetail } from "@/lib/cash";
import { getDevice } from "@/lib/device/device-store";
import type { DeviceRecord } from "@/lib/device/device-store";
import { methodLabel, paymentMethod } from "@/lib/sales";

const NOTE_MIN = 5;
const NOTE_MAX = 500;

/** Cierre de una caja de otro equipo por el Admin (FR-018): observación siempre obligatoria. */
function AdminClose({ detail, device, onClosed }: { detail: CashSessionDetail; device: DeviceRecord | null; onClosed: (closed: CashSessionDetail) => void }) {
  const [texts, setTexts] = useState<Record<string, string>>({});
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const counted = useMemo(() => {
    const values: Record<string, string> = {};
    for (const [method, text] of Object.entries(texts)) {
      const parsed = text.trim() ? parseDecimalInput(text, 2) : null;
      if (parsed !== null) values[method] = parsed;
    }
    return values;
  }, [texts]);
  const invalid = Object.values(texts).some((text) => text.trim() && parseDecimalInput(text, 2) === null);
  const negative = Object.values(counted).some((value) => toCents(value) < 0n);
  const rows = reconcile(detail, counted);
  const noteOk = note.trim().length >= NOTE_MIN && note.trim().length <= NOTE_MAX;

  async function submit() {
    setSaving(true);
    setError(null);
    try {
      onClosed(await closeAsAdmin(detail.id, counted, note.trim(), device));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No se pudo cerrar la caja");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="flex flex-col gap-3 rounded-xl border border-line bg-surface p-4">
      <h2 className="text-lg font-semibold">Cerrar esta caja desde aquí</h2>
      <p className="text-ink-muted">
        Para una caja que su equipo ya no puede cerrar (dañado, perdido o revocado). Queda marcada como cerrada fuera del equipo; si el equipo
        tenía ventas sin enviar, se registrarán igual y recibirás una alerta.
      </p>
      <ReconciliationTable
        rows={rows}
        caption="Cierre de la caja por el administrador"
        counting={{ values: texts, onChange: (method, text) => setTexts((current) => ({ ...current, [method]: text })) }}
      />
      <TextAreaField
        label="Observación (obligatoria)"
        value={note}
        maxLength={NOTE_MAX}
        hint={`De ${NOTE_MIN} a ${NOTE_MAX} caracteres: por qué se cierra fuera del equipo y cualquier diferencia.`}
        onChange={(event) => setNote(event.target.value)}
      />
      {error && <Alert variant="danger">{error}</Alert>}
      <Button loading={saving} disabled={invalid || negative || !noteOk} onClick={() => void submit()}>
        Cerrar esta caja
      </Button>
    </section>
  );
}

function CashSessionView() {
  const id = useSearchParams().get("id");
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [detail, setDetail] = useState<CashSessionDetail | null>(null);
  const [device, setDevice] = useState<DeviceRecord | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id) return;
    try {
      const local = (await getDevice()) ?? null;
      setDevice(local);
      setDetail(await getCashSession(id, local));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No se pudo cargar la caja");
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!id) return <Alert variant="danger">Falta la caja.</Alert>;
  if (error) return <Alert variant="danger">{error}</Alert>;
  if (!detail) return <p className="text-ink-muted">Cargando la caja…</p>;

  const open = detail.status === "open";
  const ownDevice = device?.id === detail.device.id;
  const movementColumns: Column<CashMovement>[] = [
    {
      key: "sale",
      header: "Venta",
      render: (movement) => (
        <Link href={`/ventas/detalle/?id=${movement.sale.id}`} className="font-semibold text-primary underline-offset-2 hover:underline">
          {movement.sale.number}
        </Link>
      ),
    },
    { key: "when", header: "Hora", render: (movement) => <span className="tabular-nums">{formatDateTime(movement.occurred_at)}</span> },
    {
      key: "kind",
      header: "Movimiento",
      render: (movement) => (
        <>
          {CASH_KIND_LABELS[movement.kind] ?? movement.kind}
          {movement.after_close && <span className="block text-sm text-warning">Llegó después del cierre</span>}
        </>
      ),
    },
    { key: "method", header: "Método", render: (movement) => methodLabel(movement.method) },
    { key: "reference", header: "Referencia", render: (movement) => movement.reference ?? "—" },
    { key: "amount", header: "Monto", className: "text-right tabular-nums", render: (movement) => formatMethodAmount(movement.amount, movement.currency) },
  ];

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="text-2xl font-bold">
          Caja de {detail.device.name} ({detail.device.series})
        </h1>
        <span className="flex flex-wrap gap-1">
          {open ? <StatusChip variant="pending" label="Abierta" /> : <StatusChip variant="confirmed" label="Cerrada" />}
          {detail.has_differences && <StatusChip variant="needs_review" label="Con diferencias" />}
          {detail.closed_outside_device && <StatusChip variant="inactive" label="Cerrada fuera del equipo" />}
        </span>
      </div>
      <dl className="grid gap-2 rounded-xl border border-line bg-surface p-4 sm:grid-cols-2">
        <div>
          <dt className="text-sm text-ink-muted">Apertura</dt>
          <dd>
            {formatDateTime(detail.opened_at)} por {detail.opened_by.full_name} (día {formatDate(detail.business_date)})
          </dd>
        </div>
        <div>
          <dt className="text-sm text-ink-muted">Fondo inicial</dt>
          <dd>
            {formatMethodAmount(detail.opening_float_ves, "VES")} y {formatMethodAmount(detail.opening_float_usd, "USD")}
          </dd>
        </div>
        {detail.closed_at && (
          <div>
            <dt className="text-sm text-ink-muted">Cierre</dt>
            <dd>
              {formatDateTime(detail.closed_at)} por {detail.closed_by?.full_name}
              {detail.closed_outside_device && ` desde ${detail.closed_from_device?.name ?? "un navegador que no es equipo"}`}
            </dd>
          </div>
        )}
        {detail.closing_note && (
          <div>
            <dt className="text-sm text-ink-muted">Observación</dt>
            <dd>{detail.closing_note}</dd>
          </div>
        )}
      </dl>
      {detail.opened_on_previous_day && <Alert variant="warning">La caja sigue abierta desde el {formatDate(detail.business_date)}.</Alert>}

      <section className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold">{open ? "Esperado por método" : "Cuadre del cierre"}</h2>
        <ReconciliationTable rows={detail.reconciliation} caption="Cuadre de la caja por método de pago" />
      </section>

      {isAdmin && open && ownDevice && (
        <Alert variant="info">
          Esta es la caja de este equipo:{" "}
          <Link href="/caja/cierre/" className="font-semibold underline">
            ciérrala desde Caja
          </Link>
          .
        </Alert>
      )}
      {isAdmin && open && !ownDevice && <AdminClose detail={detail} device={device} onClosed={(closed) => setDetail(closed)} />}

      <section className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold">Movimientos</h2>
        <DataTable
          caption="Cobros, vueltos y devoluciones de la caja"
          columns={movementColumns}
          rows={detail.movements}
          rowKey={(movement) => `${movement.sale.id}-${movement.kind}-${movement.method}-${movement.occurred_at}-${movement.amount}`}
          emptyMessage="Sin movimientos en esta caja."
        />
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold">Egresos</h2>
        <OutflowList outflows={detail.outflows} canVoid={isAdmin && open} onChanged={() => void load()} />
      </section>

      {detail.voided_after_close.length > 0 && (
        <section className="flex flex-col gap-2">
          <h2 className="text-lg font-semibold">Ventas anuladas después del cierre</h2>
          <p className="text-sm text-ink-muted">El cierre no cambia: el dinero se devolvió en otra caja.</p>
          <ul className="flex flex-col gap-1">
            {detail.voided_after_close.map((item) => (
              <li key={item.sale.id}>
                <Link href={`/ventas/detalle/?id=${item.sale.id}`} className="font-semibold text-primary underline-offset-2 hover:underline">
                  {item.sale.number}
                </Link>{" "}
                anulada el {formatDateTime(item.voided_at)}
                {item.refund_cash_session && (
                  <>
                    ; devolución en{" "}
                    <Link href={`/cajas/detalle/?id=${item.refund_cash_session.id}`} className="underline">
                      la caja de {item.refund_cash_session.device.name}
                    </Link>
                  </>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {detail.post_close_operations.length > 0 && (
        <section className="flex flex-col gap-2">
          <h2 className="text-lg font-semibold">Operaciones que llegaron después del cierre</h2>
          <p className="text-sm text-ink-muted">Se crearon en el equipo antes del cierre y se registraron sin cambiar el cuadre guardado.</p>
          <ul className="flex flex-col gap-1">
            {detail.post_close_operations.map((operation) => (
              <li key={operation.id}>
                {operation.type === "sale" ? (
                  <Link href={`/ventas/detalle/?id=${operation.id}`} className="font-semibold text-primary underline-offset-2 hover:underline">
                    Venta {operation.number}
                  </Link>
                ) : (
                  <span className="font-semibold">
                    Egreso {methodLabel(operation.method ?? "")} {formatMethodAmount(operation.amount ?? "0", paymentMethod(operation.method ?? "").currency)}
                  </span>
                )}{" "}
                creada el {formatDateTime(operation.occurred_at)}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

export default function CashSessionDetailPage() {
  return (
    <RequireAuth roles={["admin", "seller"]}>
      <AppShell>
        <Suspense fallback={null}>
          <CashSessionView />
        </Suspense>
      </AppShell>
    </RequireAuth>
  );
}
