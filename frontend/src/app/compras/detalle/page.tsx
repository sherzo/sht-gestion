"use client";

// Compra confirmada o anulada (RF-14, RN-14/FR-016 a FR-020), solo lectura: líneas con su
// costo final, gastos, tasa, totales y quién la registró, confirmó o anuló. El Admin puede
// anularla con la vista previa del efecto en stock y costo.
import { formatCost, formatDate, formatDateTime, formatPercent, formatQuantity, formatUsd, formatVes } from "@sht/shared";
import { ArrowLeft, Ban } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { PurchaseTotals } from "@/components/purchases/purchase-totals";
import { VoidDialog } from "@/components/purchases/void-dialog";
import { RequireAuth } from "@/components/require-auth";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import type { Column } from "@/components/ui/data-table";
import { StatusChip } from "@/components/ui/status-chip";
import { ApiError, apiFetch } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/use-auth";
import { PURCHASE_STATUS } from "@/lib/purchases";
import type { Purchase, PurchaseCharge, PurchaseItem } from "@/lib/purchases";

function PurchaseDetail({ id }: { id: string }) {
  const router = useRouter();
  const params = useSearchParams();
  const { user } = useAuth();
  const [purchase, setPurchase] = useState<Purchase | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(params.get("confirmada") ? "Compra confirmada: el stock y el costo ya se actualizaron." : null);
  const [voiding, setVoiding] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await apiFetch<Purchase>(`/purchases/${id}`);
      if (data.status === "draft") {
        router.replace(`/compras/editar/?id=${id}`);
        return;
      }
      setPurchase(data);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No se pudo cargar la compra");
    }
  }, [id, router]);

  useEffect(() => {
    void load();
  }, [load]);

  if (error) return <Alert variant="danger">{error}</Alert>;
  if (!purchase) return <p className="text-ink-muted">Cargando…</p>;

  const ves = purchase.currency === "VES";
  const itemColumns: Column<PurchaseItem>[] = [
    {
      key: "product",
      header: "Producto",
      render: (item) => (
        <Link href={`/productos/ficha/?id=${item.product.id}`} className="text-primary underline-offset-2 hover:underline">
          <span className="block text-sm text-ink-muted">{item.product.sku}</span>
          {item.product.name}
        </Link>
      ),
    },
    {
      key: "quantity",
      header: "Cantidad",
      className: "tabular-nums",
      render: (item) => `${formatQuantity(item.quantity, item.product.unit.decimals)} ${item.product.unit.code}`,
    },
    {
      key: "cost",
      header: ves ? "Costo unitario (Bs)" : "Costo unitario (USD)",
      className: "tabular-nums",
      render: (item) => (ves && item.unit_cost_ves ? formatVes(item.unit_cost_ves) : formatCost(item.unit_cost_usd)),
    },
    { key: "total", header: "Total (USD)", className: "tabular-nums", render: (item) => formatUsd(item.line_total_usd) },
    { key: "allocated", header: "Gasto asignado", className: "tabular-nums", render: (item) => formatUsd(item.allocated_charges_usd) },
    {
      key: "landed",
      header: "Costo final por unidad (USD)",
      className: "tabular-nums font-semibold",
      render: (item) => formatCost(item.landed_unit_cost_usd),
    },
  ];
  const chargeColumns: Column<PurchaseCharge>[] = [
    { key: "description", header: "Gasto", render: (charge) => charge.description },
    {
      key: "value",
      header: "Valor",
      className: "tabular-nums",
      render: (charge) =>
        charge.charge_type === "percent" && charge.percent
          ? `${formatPercent(charge.percent)} de la factura`
          : charge.currency === "VES" && charge.amount
            ? formatVes(charge.amount)
            : `${formatUsd(charge.amount ?? "0")} USD`,
    },
    { key: "usd", header: "En USD", className: "tabular-nums", render: (charge) => formatUsd(charge.amount_usd) },
  ];

  return (
    <>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Compra {purchase.number}</h1>
          <p className="text-ink-muted">
            {purchase.supplier.name} · {formatDate(purchase.purchase_date)}
            {purchase.supplier_invoice_number && ` · Factura ${purchase.supplier_invoice_number}`}
          </p>
        </div>
        <span className="flex flex-wrap items-center gap-3">
          <StatusChip variant={PURCHASE_STATUS[purchase.status]?.chip ?? "confirmed"} />
          {user?.role === "admin" && purchase.status === "confirmed" && (
            <Button variant="danger" onClick={() => setVoiding(true)}>
              <Ban aria-hidden className="size-5" /> Anular
            </Button>
          )}
        </span>
      </div>
      <div className="mb-4 flex flex-col gap-2">
        {notice && <Alert variant="success">{notice}</Alert>}
        {purchase.void && (
          <Alert variant="warning">
            Anulada el {formatDateTime(purchase.void.voided_at)} por {purchase.void.voided_by?.full_name ?? "—"}. Motivo: {purchase.void.reason}
          </Alert>
        )}
      </div>
      <div className="flex flex-col gap-4">
        <DataTable caption="Productos de la compra" columns={itemColumns} rows={purchase.items} rowKey={(item) => item.id} emptyMessage="Sin productos." />
        {purchase.charges.length > 0 && (
          <section aria-labelledby="charges-title">
            <h2 id="charges-title" className="mb-2 text-lg font-semibold">
              Gastos (repartidos por valor)
            </h2>
            <DataTable caption="Gastos de la compra" columns={chargeColumns} rows={purchase.charges} rowKey={(charge) => charge.id} emptyMessage="" />
          </section>
        )}
        <PurchaseTotals purchase={purchase} />
        <dl className="grid gap-2 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-ink-muted">Registró</dt>
            <dd>
              {purchase.created_by?.full_name ?? "—"}, {formatDateTime(purchase.created_at)}
            </dd>
          </div>
          {purchase.confirmed_at && (
            <div>
              <dt className="text-ink-muted">Confirmó</dt>
              <dd>
                {purchase.confirmed_by?.full_name ?? "—"}, {formatDateTime(purchase.confirmed_at)}
              </dd>
            </div>
          )}
          {purchase.notes && (
            <div className="sm:col-span-2">
              <dt className="text-ink-muted">Notas</dt>
              <dd>{purchase.notes}</dd>
            </div>
          )}
        </dl>
      </div>
      <VoidDialog
        purchase={purchase}
        open={voiding}
        onClose={() => setVoiding(false)}
        onVoided={(message) => {
          setVoiding(false);
          setNotice(message);
          void load();
        }}
      />
    </>
  );
}

function DetailPage() {
  const id = useSearchParams().get("id");
  return (
    <AppShell>
      <Link href="/compras/" className="mb-3 inline-flex min-h-11 items-center gap-2 text-primary">
        <ArrowLeft aria-hidden className="size-5" /> Compras
      </Link>
      {id ? <PurchaseDetail key={id} id={id} /> : <Alert variant="danger">Falta la compra.</Alert>}
    </AppShell>
  );
}

export default function PurchaseDetailPage() {
  return (
    <RequireAuth roles={["admin", "warehouse"]}>
      <Suspense fallback={null}>
        <DetailPage />
      </Suspense>
    </RequireAuth>
  );
}
