"use client";

// Conteos físicos (RF-12/FR-024): lista con estado y avance, y apertura de un conteo de
// todo el inventario, de categorías o de productos elegidos.
import { formatDateTime } from "@sht/shared";
import { ClipboardPlus, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";

import { AppShell } from "@/components/app-shell";
import { ProductPicker } from "@/components/products/product-picker";
import { RequireAuth } from "@/components/require-auth";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import type { Column } from "@/components/ui/data-table";
import { Dialog } from "@/components/ui/dialog";
import { SelectField, TextAreaField } from "@/components/ui/field";
import { ApiError, apiFetch } from "@/lib/api/client";
import { useCatalogConfig } from "@/lib/products";
import type { Product } from "@/lib/products";
import { COUNT_STATUS_LABELS, scopeLabel } from "@/lib/stock-counts";
import type { CountDetail, CountSummary } from "@/lib/stock-counts";

type ScopeType = "all" | "categories" | "products";

function NewCountDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const router = useRouter();
  const { categories } = useCatalogConfig();
  const [type, setType] = useState<ScopeType>("categories");
  const [categoryIds, setCategoryIds] = useState<string[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open) {
      setType("categories");
      setCategoryIds([]);
      setProducts([]);
      setNotes("");
      setError(null);
    }
  }, [open]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const ids = type === "categories" ? categoryIds : type === "products" ? products.map((product) => product.id) : [];
    if (type !== "all" && ids.length === 0) {
      setError(type === "categories" ? "Elige al menos una categoría" : "Agrega al menos un producto");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const count = await apiFetch<CountDetail>("/stock-counts", {
        method: "POST",
        body: { scope: { type, ids }, notes: notes.trim() || undefined },
      });
      router.push(`/inventario/conteo/?id=${count.id}`);
    } catch (caught) {
      if (caught instanceof ApiError && caught.code === "product_in_open_count") {
        const skus = (caught.extra.skus as string[] | undefined) ?? [];
        setError(`Estos productos ya están en otro conteo abierto: ${skus.join(", ")}`);
      } else {
        setError(caught instanceof ApiError ? caught.message : "No se pudo abrir el conteo");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} title="Nuevo conteo" onClose={onClose}>
      <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
        {error && <Alert variant="danger">{error}</Alert>}
        <SelectField
          label="Qué se cuenta"
          value={type}
          onChange={(event) => setType(event.target.value as ScopeType)}
          options={[
            { value: "categories", label: "Una o varias categorías" },
            { value: "products", label: "Productos elegidos" },
            { value: "all", label: "Todo el inventario" },
          ]}
          hint="Con todo o por categorías entran los productos activos y los inactivos que todavía tienen stock."
        />
        {type === "categories" && (
          <fieldset className="flex flex-col gap-1">
            <legend className="mb-1 text-sm font-medium">Categorías</legend>
            {categories.map((category) => (
              <label key={category.id} className="flex min-h-11 items-center gap-3">
                <input
                  type="checkbox"
                  className="size-5"
                  checked={categoryIds.includes(category.id)}
                  onChange={(event) =>
                    setCategoryIds((current) =>
                      event.target.checked ? [...current, category.id] : current.filter((id) => id !== category.id),
                    )
                  }
                />
                {category.name}
              </label>
            ))}
          </fieldset>
        )}
        {type === "products" && (
          <div className="flex flex-col gap-2">
            <ProductPicker
              includeInactive
              label="Agregar producto"
              onSelect={(product) => setProducts((current) => (current.some((item) => item.id === product.id) ? current : [...current, product]))}
            />
            {products.length > 0 && (
              <ul className="flex flex-wrap gap-2">
                {products.map((product) => (
                  <li key={product.id} className="inline-flex items-center gap-1 rounded-lg border border-line px-2 py-1 text-sm">
                    {product.sku}
                    <button
                      type="button"
                      aria-label={`Quitar ${product.sku}`}
                      className="inline-flex size-8 items-center justify-center rounded hover:bg-neutral-100"
                      onClick={() => setProducts((current) => current.filter((item) => item.id !== product.id))}
                    >
                      <X aria-hidden className="size-4" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
        <TextAreaField label="Notas (opcional)" maxLength={500} value={notes} onChange={(event) => setNotes(event.target.value)} />
        <Button type="submit" loading={submitting}>
          Abrir conteo
        </Button>
      </form>
    </Dialog>
  );
}

function CountsContent() {
  const [status, setStatus] = useState("");
  const [counts, setCounts] = useState<CountSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
    try {
      setCounts(await apiFetch<CountSummary[]>("/stock-counts", { query: { status } }));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No se pudieron cargar los conteos");
    }
  }, [status]);

  useEffect(() => {
    void load();
  }, [load]);

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
    { key: "status", header: "Estado", render: (count) => COUNT_STATUS_LABELS[count.status] ?? count.status },
    { key: "progress", header: "Avance", className: "tabular-nums", render: (count) => `${count.lines_counted} de ${count.lines_total}` },
    {
      key: "started",
      header: "Abierto",
      render: (count) => (
        <>
          {formatDateTime(count.started_at)}
          <span className="block text-sm text-ink-muted">{count.started_by?.full_name}</span>
        </>
      ),
    },
  ];

  return (
    <AppShell>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">Conteos físicos</h1>
        <Button onClick={() => setCreating(true)}>
          <ClipboardPlus aria-hidden className="size-5" /> Nuevo conteo
        </Button>
      </div>
      <div className="mb-4 sm:max-w-xs">
        <SelectField
          label="Estado"
          value={status}
          onChange={(event) => setStatus(event.target.value)}
          options={[{ value: "", label: "Todos" }, ...Object.entries(COUNT_STATUS_LABELS).map(([value, label]) => ({ value, label }))]}
        />
      </div>
      {error && (
        <div className="mb-4">
          <Alert variant="danger">{error}</Alert>
        </div>
      )}
      {counts && <DataTable caption="Conteos" columns={columns} rows={counts} rowKey={(count) => count.id} emptyMessage="No hay conteos con este estado." />}
      <NewCountDialog open={creating} onClose={() => setCreating(false)} />
    </AppShell>
  );
}

export default function CountsPage() {
  return (
    <RequireAuth roles={["admin", "warehouse"]}>
      <CountsContent />
    </RequireAuth>
  );
}
