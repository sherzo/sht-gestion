"use client";

// Consulta de ventas (FR-045, FR-046; matriz de permisos): el Admin filtra por fechas,
// número, vendedor, equipo y estado; el Vendedor ve solo sus ventas de hoy. El servidor
// impone la restricción, la pantalla solo la refleja.
import { formatDateTime, formatUsd, formatVes, todayInCaracas } from "@sht/shared";
import { ChevronLeft, ChevronRight } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { RequireAuth } from "@/components/require-auth";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import type { Column } from "@/components/ui/data-table";
import { SelectField, TextField } from "@/components/ui/field";
import { StatusChip } from "@/components/ui/status-chip";
import { ApiError, apiFetch } from "@/lib/api/client";
import type { Schemas } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/use-auth";

type Summary = Schemas["SaleSummary"];
type SalePage = Schemas["SalePage"];

const PAGE_SIZE = 50;
const STATUS_OPTIONS = [
  { value: "", label: "Todos" },
  { value: "registered", label: "Registradas" },
  { value: "voided", label: "Anuladas" },
  { value: "needs_review", label: "Para revisar" },
];

function SalesContent() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const today = todayInCaracas();
  const [filters, setFilters] = useState({ from: today, to: today, q: "", status: "" });
  const [page, setPage] = useState(1);
  const [data, setData] = useState<SalePage | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const query = isAdmin ? { ...filters, page, page_size: PAGE_SIZE } : { q: filters.q, page, page_size: PAGE_SIZE };
      setData(await apiFetch<SalePage>("/sales", { query }));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No se pudieron cargar las ventas");
    }
  }, [filters, page, isAdmin]);

  useEffect(() => {
    void load();
  }, [load]);

  function update(name: keyof typeof filters, value: string) {
    setFilters((current) => ({ ...current, [name]: value }));
    setPage(1);
  }

  const columns: Column<Summary>[] = [
    {
      key: "number",
      header: "Venta",
      render: (sale) => (
        <Link href={`/ventas/detalle/?id=${sale.id}`} className="font-semibold text-primary underline-offset-2 hover:underline">
          {sale.number}
        </Link>
      ),
    },
    { key: "when", header: "Fecha", render: (sale) => <span className="tabular-nums">{formatDateTime(sale.occurred_at)}</span> },
    { key: "seller", header: "Vendedor", render: (sale) => sale.seller.full_name },
    { key: "customer", header: "Cliente", render: (sale) => sale.customer_name ?? "—" },
    {
      key: "total",
      header: "Total",
      className: "tabular-nums text-right",
      render: (sale) => (
        <>
          <span className="block font-semibold">{formatUsd(sale.total_usd)} USD</span>
          <span className="block text-sm text-ink-muted">{formatVes(sale.total_ves)}</span>
        </>
      ),
    },
    {
      key: "status",
      header: "Estado",
      render: (sale) => (
        <span className="flex flex-wrap gap-1">
          {sale.status === "voided" && <StatusChip variant="voided" />}
          {sale.needs_review && <StatusChip variant="needs_review" />}
        </span>
      ),
    },
  ];

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <AppShell>
      <h1 className="mb-4 text-2xl font-bold">{isAdmin ? "Ventas" : "Mis ventas de hoy"}</h1>
      {error && (
        <div className="mb-4">
          <Alert variant="danger">{error}</Alert>
        </div>
      )}
      <div className={`mb-4 grid gap-3 ${isAdmin ? "sm:grid-cols-4" : "sm:grid-cols-2"}`}>
        {isAdmin && (
          <>
            <TextField label="Desde" type="date" value={filters.from} max={today} onChange={(event) => update("from", event.target.value)} />
            <TextField label="Hasta" type="date" value={filters.to} max={today} onChange={(event) => update("to", event.target.value)} />
          </>
        )}
        <TextField label="Número" type="search" placeholder="A-000123" value={filters.q} onChange={(event) => update("q", event.target.value)} />
        {isAdmin && <SelectField label="Estado" value={filters.status} options={STATUS_OPTIONS} onChange={(event) => update("status", event.target.value)} />}
      </div>
      {data && (
        <>
          <DataTable caption="Ventas" columns={columns} rows={data.items} rowKey={(sale) => sale.id} emptyMessage="No hay ventas con estos filtros." />
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

export default function SalesPage() {
  return (
    <RequireAuth roles={["admin", "seller"]}>
      <SalesContent />
    </RequireAuth>
  );
}
