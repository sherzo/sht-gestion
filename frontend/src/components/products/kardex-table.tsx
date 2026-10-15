"use client";

// Kardex de un producto (RF-08, RF-09/FR-017, FR-022): movimientos más recientes primero
// con su saldo, motivo y quién los hizo. Solo Admin y Almacén; el servidor no envía al
// Almacén los costos del movimiento.
import { formatDateTime, formatQuantity } from "@sht/shared";
import { ChevronLeft, ChevronRight } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import type { Column } from "@/components/ui/data-table";
import { SelectField, TextField } from "@/components/ui/field";
import { ApiError, apiFetch } from "@/lib/api/client";
import type { Schemas } from "@/lib/api/client";
import { ADJUSTMENT_REASON_LABELS, MOVEMENT_TYPE_LABELS } from "@/lib/products";
import type { Product } from "@/lib/products";

type Movement = Schemas["StockMovementAdmin"] | Schemas["StockMovementWarehouse"];
type MovementPage = Schemas["MovementPage"];

const PAGE_SIZE = 50;

export function KardexTable({ product }: { product: Product }) {
  const [filters, setFilters] = useState({ from: "", to: "", type: "" });
  const [page, setPage] = useState(1);
  const [data, setData] = useState<MovementPage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const decimals = product.unit.decimals;

  const latest = useRef(0);
  const load = useCallback(async () => {
    const request = ++latest.current;
    setError(null);
    try {
      const result = await apiFetch<MovementPage>(`/products/${product.id}/movements`, {
        query: { ...filters, page, page_size: PAGE_SIZE },
      });
      if (request === latest.current) setData(result);
    } catch (caught) {
      if (request === latest.current) setError(caught instanceof ApiError ? caught.message : "No se pudo cargar el kardex");
    }
  }, [product.id, filters, page]);

  useEffect(() => {
    void load();
  }, [load, product.stock]);

  function update(name: keyof typeof filters, value: string) {
    setFilters((current) => ({ ...current, [name]: value }));
    setPage(1);
  }

  const columns: Column<Movement>[] = [
    { key: "date", header: "Fecha", render: (item) => <span className="tabular-nums">{formatDateTime(item.occurred_at)}</span> },
    {
      key: "type",
      header: "Movimiento",
      render: (item) => (
        <>
          {MOVEMENT_TYPE_LABELS[item.type] ?? item.type}
          {item.adjustment_reason && <span className="block text-sm text-ink-muted">{ADJUSTMENT_REASON_LABELS[item.adjustment_reason]}</span>}
          {item.purchase && (
            <Link href={`/compras/detalle/?id=${item.purchase.id}`} className="block text-sm text-primary underline-offset-2 hover:underline">
              Compra {item.purchase.number}
            </Link>
          )}
          {/* Venta de la salida o del reverso (FR-048): el Almacén ve el número, pero no
              puede abrir la venta (solo el Admin recibe los costos del movimiento). */}
          {item.sale &&
            ("cost_before_usd" in item ? (
              <Link href={`/ventas/detalle/?id=${item.sale.id}`} className="block text-sm text-primary underline-offset-2 hover:underline">
                Venta {item.sale.number}
              </Link>
            ) : (
              <span className="block text-sm text-ink-muted">Venta {item.sale.number}</span>
            ))}
        </>
      ),
    },
    {
      key: "quantity",
      header: "Cantidad",
      className: "tabular-nums",
      render: (item) => {
        const negative = item.quantity_delta.startsWith("-");
        return (
          <span className={negative ? "text-danger" : "text-success"}>
            {negative ? "" : "+"}
            {formatQuantity(item.quantity_delta, decimals)}
          </span>
        );
      },
    },
    { key: "balance", header: "Saldo", className: "tabular-nums", render: (item) => formatQuantity(item.balance_after, decimals) },
    {
      key: "who",
      header: "Registró",
      render: (item) => (
        <>
          {item.created_by?.full_name ?? "Sistema"}
          {item.requested_by && <span className="block text-sm text-ink-muted">Solicitó: {item.requested_by.full_name}</span>}
        </>
      ),
    },
    { key: "note", header: "Nota", render: (item) => item.note ?? <span className="text-ink-muted">—</span> },
  ];

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <div className="flex flex-col gap-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <TextField label="Desde" type="date" value={filters.from} onChange={(event) => update("from", event.target.value)} />
        <TextField label="Hasta" type="date" value={filters.to} onChange={(event) => update("to", event.target.value)} />
        <SelectField
          label="Tipo"
          value={filters.type}
          onChange={(event) => update("type", event.target.value)}
          options={[{ value: "", label: "Todos" }, ...Object.entries(MOVEMENT_TYPE_LABELS).map(([value, label]) => ({ value, label }))]}
        />
      </div>
      {error && <Alert variant="danger">{error}</Alert>}
      {data && (
        <>
          <DataTable caption="Kardex" columns={columns} rows={data.items} rowKey={(item) => item.id} emptyMessage="No hay movimientos con estos filtros." />
          {data.total > data.page_size && (
            <nav aria-label="Paginación del kardex" className="flex items-center justify-between gap-3">
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
    </div>
  );
}
