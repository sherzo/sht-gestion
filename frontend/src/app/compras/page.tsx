"use client";

// Compras (RF-14/FR-020), Admin y Almacén: lista con filtros por proveedor, fechas,
// estado, producto y número o factura, de la más reciente a la más antigua.
import { formatDate, formatUsd } from "@sht/shared";
import { ChevronLeft, ChevronRight, Plus, X } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { ProductPicker } from "@/components/products/product-picker";
import { RequireAuth } from "@/components/require-auth";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import type { Column } from "@/components/ui/data-table";
import { SelectField, TextField } from "@/components/ui/field";
import { StatusChip } from "@/components/ui/status-chip";
import { ApiError, apiFetch } from "@/lib/api/client";
import { PURCHASE_STATUS } from "@/lib/purchases";
import type { PurchasePage, PurchaseSummary, Supplier, SupplierPage } from "@/lib/purchases";

const PAGE_SIZE = 50;
const EMPTY = { supplier_id: "", from: "", to: "", status: "", q: "" };

function PurchasesContent() {
  const [filters, setFilters] = useState(EMPTY);
  const [product, setProduct] = useState<{ id: string; name: string } | null>(null);
  const [page, setPage] = useState(1);
  const [data, setData] = useState<PurchasePage | null>(null);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<SupplierPage>("/suppliers", { query: { page_size: 100 } })
      .then((result) => setSuppliers(result.items))
      .catch(() => setSuppliers([]));
  }, []);

  const load = useCallback(async () => {
    setError(null);
    try {
      const query = Object.fromEntries(Object.entries(filters).filter(([, value]) => value));
      setData(
        await apiFetch<PurchasePage>("/purchases", {
          query: { ...query, product_id: product?.id, page, page_size: PAGE_SIZE },
        }),
      );
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No se pudieron cargar las compras");
    }
  }, [filters, product, page]);

  useEffect(() => {
    void load();
  }, [load]);

  function update(name: keyof typeof EMPTY, value: string) {
    setFilters((current) => ({ ...current, [name]: value }));
    setPage(1);
  }

  const columns: Column<PurchaseSummary>[] = [
    {
      key: "number",
      header: "Compra",
      render: (row) => (
        <Link
          href={row.status === "draft" ? `/compras/editar/?id=${row.id}` : `/compras/detalle/?id=${row.id}`}
          className="font-semibold text-primary underline-offset-2 hover:underline"
        >
          {row.number ?? "Borrador"}
        </Link>
      ),
    },
    { key: "date", header: "Fecha", render: (row) => <span className="tabular-nums">{formatDate(row.purchase_date)}</span> },
    {
      key: "supplier",
      header: "Proveedor",
      render: (row) => (
        <>
          {row.supplier.name}
          {row.supplier_invoice_number && <span className="block text-sm text-ink-muted">Factura {row.supplier_invoice_number}</span>}
        </>
      ),
    },
    { key: "currency", header: "Moneda", render: (row) => (row.currency === "VES" ? "Bs" : "USD") },
    { key: "total", header: "Total (USD)", className: "tabular-nums", render: (row) => formatUsd(row.total_usd) },
    { key: "status", header: "Estado", render: (row) => <StatusChip variant={PURCHASE_STATUS[row.status]?.chip ?? "draft"} /> },
  ];

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <AppShell>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">Compras</h1>
        <Link
          href="/compras/editar/"
          className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-primary px-4 font-semibold text-on-primary hover:bg-primary-hover"
        >
          <Plus aria-hidden className="size-5" /> Nueva compra
        </Link>
      </div>
      <section aria-label="Filtros" className="mb-4 grid gap-3 rounded-xl border border-line bg-surface p-3 sm:grid-cols-2 lg:grid-cols-3">
        <SelectField
          label="Proveedor"
          value={filters.supplier_id}
          onChange={(event) => update("supplier_id", event.target.value)}
          options={[{ value: "", label: "Todos" }, ...suppliers.map((s) => ({ value: s.id, label: s.name }))]}
        />
        <TextField label="Desde" type="date" value={filters.from} onChange={(event) => update("from", event.target.value)} />
        <TextField label="Hasta" type="date" value={filters.to} onChange={(event) => update("to", event.target.value)} />
        <SelectField
          label="Estado"
          value={filters.status}
          onChange={(event) => update("status", event.target.value)}
          options={[
            { value: "", label: "Todos" },
            { value: "draft", label: "Borradores" },
            { value: "confirmed", label: "Confirmadas" },
            { value: "voided", label: "Anuladas" },
          ]}
        />
        <TextField
          label="Número o factura"
          type="search"
          value={filters.q}
          onChange={(event) => update("q", event.target.value)}
          placeholder="C-000012 o PI-118"
        />
        <div>
          {product ? (
            <div className="flex flex-col gap-1">
              <span className="text-sm font-medium">Producto</span>
              <span className="flex items-center gap-2">
                <span className="min-w-0 flex-1 truncate">{product.name}</span>
                <Button variant="secondary" aria-label="Quitar filtro de producto" onClick={() => setProduct(null)}>
                  <X aria-hidden className="size-4" />
                </Button>
              </span>
            </div>
          ) : (
            <ProductPicker label="Producto" includeInactive onSelect={(picked) => setProduct({ id: picked.id, name: picked.name })} />
          )}
        </div>
      </section>
      {error && <Alert variant="danger">{error}</Alert>}
      {data && (
        <>
          <DataTable
            caption="Compras"
            columns={columns}
            rows={data.items}
            rowKey={(row) => row.id}
            emptyMessage="No hay compras que coincidan con los filtros."
          />
          {data.total > data.page_size && (
            <nav aria-label="Paginación" className="mt-4 flex items-center justify-between gap-3">
              <Button variant="secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>
                <ChevronLeft aria-hidden className="size-4" /> Anterior
              </Button>
              <span className="text-sm text-ink-muted">
                Página {page} de {totalPages}
              </span>
              <Button variant="secondary" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>
                Siguiente <ChevronRight aria-hidden className="size-4" />
              </Button>
            </nav>
          )}
        </>
      )}
    </AppShell>
  );
}

export default function PurchasesPage() {
  return (
    <RequireAuth roles={["admin", "warehouse"]}>
      <PurchasesContent />
    </RequireAuth>
  );
}
