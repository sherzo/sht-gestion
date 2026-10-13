"use client";

// Lista de productos (RF-01, RF-06): todos los roles la ven, cada uno con su esquema; el
// precio solo aparece para Admin y Vendedor (research R6).
import { formatUsd } from "@sht/shared";
import { ChevronLeft, ChevronRight, PackagePlus } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { ProductStatus } from "@/components/products/product-status";
import { RequireAuth } from "@/components/require-auth";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import type { Column } from "@/components/ui/data-table";
import { SelectField } from "@/components/ui/field";
import { ApiError, apiFetch } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/use-auth";
import { hasPrice, quantityWithUnit, useCatalogConfig } from "@/lib/products";
import type { Product, ProductPage } from "@/lib/products";

const PAGE_SIZE = 50;

function ProductsContent() {
  const { user } = useAuth();
  const { categories } = useCatalogConfig();
  const [filters, setFilters] = useState({ category_id: "", is_active: "true" });
  const [page, setPage] = useState(1);
  const [data, setData] = useState<ProductPage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const canEdit = user?.role === "admin" || user?.role === "warehouse";

  const latest = useRef(0);
  const load = useCallback(async () => {
    const request = ++latest.current;
    setError(null);
    try {
      const query = { ...filters, is_active: canEdit ? filters.is_active : undefined, page, page_size: PAGE_SIZE };
      const result = await apiFetch<ProductPage>("/products", { query });
      if (request === latest.current) setData(result);
    } catch (caught) {
      if (request === latest.current) setError(caught instanceof ApiError ? caught.message : "No se pudo cargar la lista");
    }
  }, [filters, page, canEdit]);

  useEffect(() => {
    void load();
  }, [load]);

  function update(name: keyof typeof filters, value: string) {
    setFilters((current) => ({ ...current, [name]: value }));
    setPage(1);
  }

  const columns: Column<Product>[] = [
    {
      key: "product",
      header: "Producto",
      render: (product) => (
        <Link href={`/productos/ficha/?id=${product.id}`} className="font-medium text-primary underline-offset-2 hover:underline">
          <span className="block text-sm text-ink-muted">{product.sku}</span>
          {product.name}
        </Link>
      ),
    },
    { key: "category", header: "Categoría", render: (product) => product.category.name },
    {
      key: "stock",
      header: "Stock",
      className: "tabular-nums",
      render: (product) => quantityWithUnit(product.stock, product.unit),
    },
    ...(user?.role === "warehouse"
      ? []
      : [
          {
            key: "price",
            header: "Precio (USD)",
            className: "tabular-nums",
            render: (product: Product) =>
              hasPrice(product) && product.sale_price_usd ? formatUsd(product.sale_price_usd) : <span className="text-ink-muted">Sin precio</span>,
          },
        ]),
    { key: "status", header: "Estado", render: (product) => <ProductStatus product={product} /> },
  ];

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <AppShell>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">Productos</h1>
        {canEdit && (
          <Link
            href="/productos/nuevo/"
            className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-primary px-4 font-semibold text-on-primary hover:bg-primary-hover"
          >
            <PackagePlus aria-hidden className="size-5" /> Nuevo producto
          </Link>
        )}
      </div>
      <div className="mb-4 grid gap-3 sm:max-w-xl sm:grid-cols-2">
        <SelectField
          label="Categoría"
          value={filters.category_id}
          onChange={(event) => update("category_id", event.target.value)}
          options={[{ value: "", label: "Todas" }, ...categories.map((category) => ({ value: category.id, label: category.name }))]}
        />
        {canEdit && (
          <SelectField
            label="Estado"
            value={filters.is_active}
            onChange={(event) => update("is_active", event.target.value)}
            options={[
              { value: "true", label: "Activos" },
              { value: "false", label: "Inactivos" },
              { value: "", label: "Todos" },
            ]}
          />
        )}
      </div>
      {error && (
        <div className="mb-4">
          <Alert variant="danger">{error}</Alert>
        </div>
      )}
      {data && (
        <>
          <p className="mb-2 text-sm text-ink-muted" aria-live="polite">
            {data.total} producto{data.total === 1 ? "" : "s"}
          </p>
          <DataTable caption="Productos" columns={columns} rows={data.items} rowKey={(product) => product.id} emptyMessage="No hay productos con estos filtros." />
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

export default function ProductsPage() {
  return (
    <RequireAuth>
      <ProductsContent />
    </RequireAuth>
  );
}
