"use client";

// Detalle de una venta (RF-26, FR-045 a FR-049): ítems con cantidad, precio, descuentos y
// quién los autorizó; totales; tasa y su fecha; pagos, vueltos y sobrepago; cliente y
// anulación. El Admin ve además el costo y el margen y puede anular (RF-27); el Vendedor
// solo abre sus ventas de hoy y nunca recibe costos.
import { formatDate, formatDateTime, formatPercent, formatQuantity, formatRate, formatUsd, formatVes } from "@sht/shared";
import { Ban } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { RequireAuth } from "@/components/require-auth";
import { VoidSaleDialog } from "@/components/sales/void-sale-dialog";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { StatusChip } from "@/components/ui/status-chip";
import { ApiError, apiFetch } from "@/lib/api/client";
import type { Schemas } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/use-auth";
import { methodLabel } from "@/lib/sales";
import type { Sale } from "@/lib/sales";

type Discount = Schemas["DiscountOut"];

const KIND_LABELS: Record<string, string> = {
  sale_payment: "Pago",
  change: "Vuelto",
  void_refund: "Devolución por anulación",
  void_change: "Vuelto recuperado por anulación",
};

const METHOD_LABELS: Record<string, string> = { pin: "con PIN", request: "por solicitud", admin_self: "el administrador vendió" };

function discountText(discount: Discount): string {
  const value = discount.type === "percent" ? formatPercent(discount.value) : `${formatUsd(discount.value)} USD`;
  const who = discount.authorized_by ? `, autorizó ${discount.authorized_by.full_name} (${METHOD_LABELS[discount.method ?? ""] ?? discount.method})` : ", sin autorización: para revisar";
  return `Descuento ${value}: −${formatUsd(discount.amount_usd)} USD${who}`;
}

function isAdminSale(sale: Sale): sale is Schemas["SaleAdmin"] {
  return "cost_usd" in sale;
}

function SaleDetail() {
  const id = useSearchParams().get("id");
  const { user } = useAuth();
  const [sale, setSale] = useState<Sale | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [voiding, setVoiding] = useState(false);

  useEffect(() => {
    if (!id) return;
    apiFetch<Sale>(`/sales/${id}`)
      .then(setSale)
      .catch((caught) => setError(caught instanceof ApiError ? caught.message : "No se pudo cargar la venta"));
  }, [id]);

  if (error) return <Alert variant="danger">{error}</Alert>;
  if (!sale) return <p className="text-ink-muted">Cargando…</p>;
  const admin = isAdminSale(sale) ? sale : null;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-2xl font-bold">Venta {sale.number}</h1>
          <p className="text-ink-muted">
            {formatDateTime(sale.occurred_at)} · {sale.seller.full_name} · {sale.device.name}
          </p>
        </div>
        <span className="flex flex-wrap gap-2">
          {sale.status === "voided" && <StatusChip variant="voided" />}
          {sale.needs_review && <StatusChip variant="needs_review" />}
        </span>
      </div>
      {sale.void && (
        <Alert variant="danger">
          Anulada por {sale.void.voided_by.full_name} el {formatDateTime(sale.void.voided_at)}: {sale.void.reason}
          {sale.void.refund_cash_session && (
            <span className="block">
              Devolución registrada en la caja de {sale.void.refund_cash_session.device.name}
              {sale.void.refund_cash_session.id !== sale.cash_session_id && " (la caja de la venta ya estaba cerrada)"}.{" "}
              {user?.role === "admin" && (
                <Link href={`/cajas/detalle/?id=${sale.void.refund_cash_session.id}`} className="font-semibold underline">
                  Ver la caja
                </Link>
              )}
            </span>
          )}
        </Alert>
      )}
      {sale.customer && (
        <p>
          Cliente: <strong>{sale.customer.name}</strong>
          {sale.customer.document_id && ` · ${sale.customer.document_id}`}
          {sale.customer.phone && ` · ${sale.customer.phone}`}
        </p>
      )}

      <ul className="flex flex-col divide-y divide-line rounded-xl border border-line bg-surface">
        {sale.items.map((item) => {
          const costed = admin?.items.find((line) => line.id === item.id);
          return (
            <li key={item.id} className="flex flex-col gap-1 p-3">
              <div className="flex flex-wrap justify-between gap-2">
                <span>
                  <span className="block text-sm text-ink-muted">{item.product.sku}</span>
                  <span className="font-medium">{item.product.name}</span>
                </span>
                <span className="text-right tabular-nums">
                  <span className="block">
                    {formatQuantity(item.quantity, item.product.unit_decimals)} {item.product.unit_code} × {formatUsd(item.unit_price_usd)}
                  </span>
                  <span className="block font-semibold">{formatUsd(item.line_total_usd)} USD</span>
                </span>
              </div>
              {item.entered_unit === "cm" && <p className="text-sm text-ink-muted">Escrito en centímetros.</p>}
              {item.item_discount && <p className="text-sm text-success">{discountText(item.item_discount)}</p>}
              {item.allocated_sale_discount_usd !== "0.00" && (
                <p className="text-sm text-ink-muted">Parte del descuento total: −{formatUsd(item.allocated_sale_discount_usd)} USD</p>
              )}
              {item.server_price_usd && <p className="text-sm text-warning">El precio vigente era {formatUsd(item.server_price_usd)} USD.</p>}
              {costed && (
                <p className="text-sm text-ink-muted">
                  Costo {costed.unit_cost_usd ? `${formatUsd(costed.unit_cost_usd)} USD` : "sin costo"} · Margen{" "}
                  {costed.margin_usd ? `${formatUsd(costed.margin_usd)} USD` : "—"}
                </p>
              )}
            </li>
          );
        })}
      </ul>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="flex flex-col gap-1 rounded-xl border border-line bg-surface p-4 tabular-nums">
          {sale.discount && <p className="text-success">{discountText(sale.discount)}</p>}
          <p className="text-2xl font-bold">Total {formatUsd(sale.total_usd)} USD</p>
          <p className="text-xl font-semibold text-primary">{formatVes(sale.total_ves)}</p>
          <p className="text-sm text-ink-muted">
            Tasa BCV {formatRate(sale.exchange_rate)} del {formatDate(sale.exchange_rate_date)}
          </p>
          {admin && admin.margin_usd && (
            <p className="text-sm text-ink-muted">
              Costo {formatUsd(admin.cost_usd ?? "0")} USD · Margen {formatUsd(admin.margin_usd)} USD
            </p>
          )}
        </div>
        <div className="flex flex-col gap-1 rounded-xl border border-line bg-surface p-4">
          <h2 className="font-semibold">Pagos</h2>
          <ul className="flex flex-col gap-1 tabular-nums">
            {sale.payments.map((payment, index) => (
              <li key={`${payment.kind}-${index}`} className="flex justify-between gap-2">
                <span>
                  {KIND_LABELS[payment.kind]}: {methodLabel(payment.method)}
                  {payment.reference && <span className="block text-sm text-ink-muted">Ref. {payment.reference}</span>}
                </span>
                <span className="text-right">
                  {payment.currency === "VES" ? formatVes(payment.amount) : `${formatUsd(payment.amount)} ${payment.currency}`}
                  {payment.currency === "VES" && <span className="block text-sm text-ink-muted">{formatUsd(payment.amount_usd)} USD</span>}
                </span>
              </li>
            ))}
          </ul>
          {sale.overpaid_usd !== "0.00" && <p className="text-sm text-ink-muted">Sobrepago: {formatUsd(sale.overpaid_usd)} USD (el cliente dejó la diferencia).</p>}
        </div>
      </div>

      <div className="flex flex-wrap gap-3">
        <Link href="/ventas/" className="inline-flex min-h-11 items-center rounded-lg border border-line px-4 font-semibold hover:bg-neutral-100">
          Volver a ventas
        </Link>
        {user?.role === "admin" && sale.status !== "voided" && (
          <Button variant="danger" onClick={() => setVoiding(true)}>
            <Ban aria-hidden className="size-4" /> Anular venta
          </Button>
        )}
      </div>
      <VoidSaleDialog sale={sale} open={voiding} onClose={() => setVoiding(false)} onVoided={setSale} />
    </div>
  );
}

export default function SaleDetailPage() {
  return (
    <RequireAuth roles={["admin", "seller"]}>
      <AppShell>
        <Suspense fallback={<p className="text-ink-muted">Cargando…</p>}>
          <SaleDetail />
        </Suspense>
      </AppShell>
    </RequireAuth>
  );
}
