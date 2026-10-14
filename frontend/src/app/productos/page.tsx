"use client";

// Lista y búsqueda de productos (RF-01, RF-06/FR-032, FR-033): todos los roles la ven,
// cada uno con su esquema; el precio solo aparece para Admin y Vendedor (research R6).
import { formatUsd } from "@sht/shared";
import { ChevronLeft, ChevronRight, PackagePlus } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { EMPTY_FILTERS, ProductSearch, searchParams } from "@/components/products/product-search";
import type { SearchFilters } from "@/components/products/product-search";
import { ProductStatus } from "@/components/products/product-status";
import { RequireAuth } from "@/components/require-auth";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import type { Column } from "@/components/ui/data-table";
import { ApiError, apiFetch } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/use-auth";
import { hasPrice, quantityWithUnit, useCatalogConfig } from "@/lib/products";
import type { Product, ProductPage } from "@/lib/products";

const PAGE_SIZE = 50;

function ProductsContent() {
  const { user } = useAuth();
  const { categories } = useCatalogConfig();
  const [filters, setFilters] = useState<SearchFilters>(EMPTY_FILTERS);
  const [page, setPage] = useState(1);
  const [data, setData] = useState<ProductPage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const canEdit = user?.role === "admin" || user?.role === "warehouse";

  const latest = useRef(0);
  const load = useCallback(async () => {
    const request = ++latest.current;
    setError(null);
    try {
      const query = searchParams({ ...filters, is_active: canEdit ? filters.is_active : "" }, { page, page_size: PAGE_SIZE });
      const result = await apiFetch<ProductPage>("/products", { query });
      if (request === latest.current) setData(result);
    } catch (caught) {
      if (request === latest.current) setError(caught instanceof ApiError ? caught.message : "No se pudo cargar la lista");
    }
  }, [filters, page, canEdit]);

  useEffect(() => {
    void load();
  }, [load]);

  const changeFilters = useCallback((next: SearchFilters) => {
    setFilters(next);
    setPage(1);
  }, []);

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
      <div className="mb-4">
        <ProductSearch categories={categories} value={filters} onChange={changeFilters} showStatus={canEdit} />
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
          {data.items.length === 0 ? (
            <div className="flex flex-col items-center gap-3 rounded-xl border border-line bg-surface p-6 text-center">
              <p className="text-ink-muted">No se encontraron productos con esta búsqueda.</p>
              {canEdit && (
                <Link href="/productos/nuevo/" className="font-semibold text-primary underline-offset-2 hover:underline">
                  Crear producto
                </Link>
              )}
            </div>
          ) : (
            <DataTable caption="Productos" columns={columns} rows={data.items} rowKey={(product) => product.id} emptyMessage="" />
          )}
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
