"use client";

// Pendientes del Admin (RN-19/FR-019b): salidas del Almacén por aprobar, conteos listos
// para revisión y alertas (RN-14: anulaciones de compras que conservaron el costo). Aprobar genera el movimiento con el stock de ese momento; rechazar exige
// un motivo que el Almacén verá.
import { formatCost, formatDate, formatDateTime, formatQuantity, formatRate, formatUsd } from "@sht/shared";
import { Check, X } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";

import { AppShell } from "@/components/app-shell";
import { RequireAuth } from "@/components/require-auth";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import type { Column } from "@/components/ui/data-table";
import { Dialog } from "@/components/ui/dialog";
import { TextAreaField } from "@/components/ui/field";
import { ApiError, apiFetch } from "@/lib/api/client";
import type { Schemas } from "@/lib/api/client";
import { ADJUSTMENT_REASON_LABELS } from "@/lib/products";
import { scopeLabel } from "@/lib/stock-counts";
import type { CountSummary } from "@/lib/stock-counts";

type AdjustmentRequest = Schemas["AdjustmentRequestOut"];
type RequestPage = Schemas["AdjustmentRequestPage"];

function quantity(request: AdjustmentRequest, value: string): string {
  return `${formatQuantity(value, request.product.unit.decimals)} ${request.product.unit.code}`;
}

function AdjustmentRequests() {
  const [requests, setRequests] = useState<AdjustmentRequest[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [approving, setApproving] = useState<AdjustmentRequest | null>(null);
  const [rejecting, setRejecting] = useState<AdjustmentRequest | null>(null);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const page = await apiFetch<RequestPage>("/inventory/adjustment-requests", { query: { status: "pending", page_size: 100 } });
      setRequests(page.items);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No se pudieron cargar los pendientes");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function decide(request: AdjustmentRequest, action: "approve" | "reject", body?: unknown) {
    setBusy(true);
    setError(null);
    try {
      await apiFetch(`/inventory/adjustment-requests/${request.id}/${action}`, { method: "POST", body });
      setNotice(action === "approve" ? `Salida de ${request.product.sku} aprobada.` : `Salida de ${request.product.sku} rechazada.`);
      setApproving(null);
      setRejecting(null);
      setReason("");
      await load();
    } catch (caught) {
      if (caught instanceof ApiError && caught.code === "negative_stock") {
        setError(
          `No se puede aprobar: el stock de ${request.product.sku} ya no alcanza. Recházala con un motivo para que el Almacén registre la cantidad correcta.`,
        );
      } else {
        setError(caught instanceof ApiError ? caught.message : "No se pudo completar la operación");
      }
      setApproving(null);
    } finally {
      setBusy(false);
    }
  }

  function onReject(event: FormEvent) {
    event.preventDefault();
    if (rejecting && reason.trim()) void decide(rejecting, "reject", { reason });
  }

  const columns: Column<AdjustmentRequest>[] = [
    {
      key: "product",
      header: "Producto",
      render: (request) => (
        <Link href={`/productos/ficha/?id=${request.product.id}`} className="text-primary underline-offset-2 hover:underline">
          <span className="block text-sm text-ink-muted">{request.product.sku}</span>
          {request.product.name}
        </Link>
      ),
    },
    {
      key: "quantity",
      header: "Salida",
      className: "tabular-nums",
      render: (request) => (
        <>
          <span className="text-danger">{quantity(request, request.quantity_delta)}</span>
          <span className="block text-sm text-ink-muted">Stock actual: {quantity(request, request.product.stock)}</span>
        </>
      ),
    },
    {
      key: "reason",
      header: "Motivo",
      render: (request) => (
        <>
          {ADJUSTMENT_REASON_LABELS[request.adjustment_reason]}
          {request.note && <span className="block text-sm text-ink-muted">{request.note}</span>}
        </>
      ),
    },
    {
      key: "who",
      header: "Solicitó",
      render: (request) => (
        <>
          {request.requested_by.full_name}
          <span className="block text-sm text-ink-muted">{formatDateTime(request.requested_at)}</span>
        </>
      ),
    },
    {
      key: "actions",
      header: "Decisión",
      render: (request) => (
        <span className="flex flex-wrap gap-2">
          <Button onClick={() => setApproving(request)}>
            <Check aria-hidden className="size-4" /> Aprobar
          </Button>
          <Button variant="secondary" onClick={() => setRejecting(request)}>
            <X aria-hidden className="size-4" /> Rechazar
          </Button>
        </span>
      ),
    },
  ];

  return (
    <section aria-labelledby="pendientes-ajustes" className="flex flex-col gap-3">
      <h2 id="pendientes-ajustes" className="text-xl font-semibold">
        Salidas de inventario por aprobar
      </h2>
      {notice && <Alert variant="success">{notice}</Alert>}
      {error && <Alert variant="danger">{error}</Alert>}
      {requests && (
        <DataTable caption="Salidas por aprobar" columns={columns} rows={requests} rowKey={(request) => request.id} emptyMessage="No hay salidas pendientes." />
      )}
      <Dialog open={approving !== null} title="Aprobar salida" onClose={() => setApproving(null)}>
        {approving && (
          <>
            <p>
              Se descontarán <strong>{quantity(approving, approving.quantity_delta.replace("-", ""))}</strong> de{" "}
              {approving.product.name} (stock actual: {quantity(approving, approving.product.stock)}).
            </p>
            <div className="flex flex-wrap gap-2">
              <Button loading={busy} onClick={() => decide(approving, "approve")}>
                Aprobar
              </Button>
              <Button variant="secondary" onClick={() => setApproving(null)}>
                Cancelar
              </Button>
            </div>
          </>
        )}
      </Dialog>
      <Dialog open={rejecting !== null} title="Rechazar salida" onClose={() => setRejecting(null)}>
        <form onSubmit={onReject} className="flex flex-col gap-4" noValidate>
          <TextAreaField
            label="Motivo del rechazo"
            required
            maxLength={500}
            hint="El Almacén verá este motivo en sus solicitudes."
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
          <div className="flex flex-wrap gap-2">
            <Button type="submit" variant="danger" loading={busy} disabled={!reason.trim()}>
              Rechazar
            </Button>
            <Button variant="secondary" onClick={() => setRejecting(null)}>
              Cancelar
            </Button>
          </div>
        </form>
      </Dialog>
    </section>
  );
}

function CountsReady() {
  const [counts, setCounts] = useState<CountSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<CountSummary[]>("/stock-counts", { query: { status: "ready_for_review" } })
      .then(setCounts)
      .catch((caught) => setError(caught instanceof ApiError ? caught.message : "No se pudieron cargar los conteos"));
  }, []);

  const columns: Column<CountSummary>[] = [
    {
      key: "count",
      header: "Conteo",
      render: (count) => (
        <Link href={`/inventario/conteo/?id=${count.id}`} className="font-medium text-primary underline-offset-2 hover:underline">
          {scopeLabel(count.scope)}
          {count.notes && <span className="block text-sm font-normal text-ink-muted">{count.notes}</span>}
        </Link>
      ),
    },
    { key: "progress", header: "Anotados", className: "tabular-nums", render: (count) => `${count.lines_counted} de ${count.lines_total}` },
    {
      key: "ready",
      header: "Listo desde",
      render: (count) => (count.ready_at ? formatDateTime(count.ready_at) : "—"),
    },
  ];

  return (
    <section aria-labelledby="pendientes-conteos" className="flex flex-col gap-3">
      <h2 id="pendientes-conteos" className="text-xl font-semibold">
        Conteos listos para revisión
      </h2>
      {error && <Alert variant="danger">{error}</Alert>}
      {counts && <DataTable caption="Conteos listos para revisión" columns={columns} rows={counts} rowKey={(count) => count.id} emptyMessage="No hay conteos por revisar." />}
    </section>
  );
}

type AlertItem = Schemas["AlertOut"];

type SaleProduct = { sku: string; name: string; quantity?: string; stock_after?: string; sale_price_usd?: string; server_price_usd?: string | null };

// Textos de las alertas de venta (research R6 de la etapa 1.3): la venta se registró igual.
const SALE_ALERT_TITLES: Record<string, string> = {
  negative_stock: "Stock negativo por venta",
  price_mismatch: "Precio distinto al vigente",
  total_mismatch: "Total distinto",
  rate_mismatch: "Tasa distinta a la cargada",
  discount_review: "Descuento para revisar",
  inactive_user_sync: "Vendedor desactivado",
};

function saleAlertDetail(alert: AlertItem): string {
  const details = alert.details as Record<string, unknown>;
  const products = (details.products as SaleProduct[] | undefined) ?? [];
  switch (alert.type) {
    case "negative_stock":
      return products.map((item) => `${item.sku} ${item.name}: quedó en ${item.stock_after}`).join("; ") + ". Revisa el inventario con un conteo o una compra.";
    case "price_mismatch":
      return products
        .map((item) => `${item.sku}: vendido a ${formatUsd(item.sale_price_usd ?? "0")} USD; vigente ${item.server_price_usd ? `${formatUsd(item.server_price_usd)} USD` : "sin precio"}`)
        .join("; ");
    case "total_mismatch":
      return `El equipo calculó ${formatUsd(String(details.device_total_usd))} USD y el servidor ${formatUsd(String(details.server_total_usd))} USD. Saldo sin cubrir: ${formatUsd(String(details.balance_usd))} USD.`;
    case "rate_mismatch":
      return `La venta usó ${formatRate(String(details.sale_rate))}; la tasa cargada del ${formatDate(String(details.rate_date))} es ${details.loaded_rate ? formatRate(String(details.loaded_rate)) : "ninguna"}.`;
    case "discount_review":
      return `${String(details.seller)} aplicó un descuento sin autorización válida (por ejemplo, sin conexión). La venta no cambia; para corregirla se anula.`;
    default:
      return `${String(details.seller ?? "")}`;
  }
}

function AlertDescription({ alert }: { alert: AlertItem }) {
  if (alert.entity_type === "sale") {
    return (
      <>
        <span className="block font-medium">
          {SALE_ALERT_TITLES[alert.type] ?? alert.type} en la venta {alert.sale?.number}
        </span>
        <span className="block text-sm text-ink-muted">{saleAlertDetail(alert)}</span>
        <Link href={`/ventas/detalle/?id=${alert.entity_id}`} className="text-sm text-primary underline-offset-2 hover:underline">
          Ver la venta
        </Link>
      </>
    );
  }
  const details = alert.details as Record<string, string | null>;
  return (
    <>
      <span className="block font-medium">Anulación de la compra {details.purchase_number}: se conservó el costo de {details.sku}</span>
      <span className="block text-sm text-ink-muted">
        Stock {details.stock_before} → {details.stock_after}. Costo conservado: {details.cost_kept ? formatCost(details.cost_kept) : "—"} USD.
        Revisa el costo del producto con un conteo o la próxima compra.
      </span>
      <Link href={`/compras/detalle/?id=${alert.entity_id}`} className="text-sm text-primary underline-offset-2 hover:underline">
        Ver la compra
      </Link>
    </>
  );
}

function Alerts() {
  const [alerts, setAlerts] = useState<AlertItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    apiFetch<Schemas["AlertPage"]>("/alerts", { query: { status: "open", page_size: 100 } })
      .then((page) => setAlerts(page.items))
      .catch((caught) => setError(caught instanceof ApiError ? caught.message : "No se pudieron cargar las alertas"));
  }, []);

  useEffect(load, [load]);

  async function resolve(alert: AlertItem) {
    try {
      await apiFetch(`/alerts/${alert.id}/resolve`, { method: "POST" });
      load();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No se pudo marcar la alerta");
    }
  }

  const columns: Column<AlertItem>[] = [
    {
      key: "what",
      header: "Alerta",
      render: (alert) => <AlertDescription alert={alert} />,
    },
    { key: "when", header: "Fecha", render: (alert) => formatDateTime(alert.created_at) },
    {
      key: "actions",
      header: "Acciones",
      render: (alert) => (
        <Button variant="secondary" onClick={() => resolve(alert)}>
          <Check aria-hidden className="size-4" /> Marcar revisada
        </Button>
      ),
    },
  ];

  return (
    <section aria-labelledby="pendientes-alertas" className="flex flex-col gap-3">
      <h2 id="pendientes-alertas" className="text-xl font-semibold">
        Alertas
      </h2>
      {error && <Alert variant="danger">{error}</Alert>}
      {alerts && <DataTable caption="Alertas" columns={columns} rows={alerts} rowKey={(alert) => alert.id} emptyMessage="No hay alertas por revisar." />}
    </section>
  );
}

function PendingContent() {
  return (
    <AppShell>
      <h1 className="mb-4 text-2xl font-bold">Pendientes</h1>
      <div className="flex flex-col gap-8">
        <AdjustmentRequests />
        <CountsReady />
        <Alerts />
      </div>
    </AppShell>
  );
}

export default function PendingPage() {
  return (
    <RequireAuth roles={["admin"]}>
      <PendingContent />
    </RequireAuth>
  );
}
