"use client";

// Productos con stock bajo (RF-11/FR-023): activos con stock menor o igual al mínimo,
// agrupados por categoría, para decidir qué comprar.
import Link from "next/link";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { ProductStatus } from "@/components/products/product-status";
import { RequireAuth } from "@/components/require-auth";
import { Alert } from "@/components/ui/alert";
import { DataTable } from "@/components/ui/data-table";
import type { Column } from "@/components/ui/data-table";
import { ApiError, apiFetch } from "@/lib/api/client";
import { quantityWithUnit } from "@/lib/products";
import type { Product } from "@/lib/products";

function LowStockContent() {
  const [products, setProducts] = useState<Product[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<Product[]>("/inventory/low-stock")
      .then(setProducts)
      .catch((caught) => setError(caught instanceof ApiError ? caught.message : "No se pudo cargar la lista"));
  }, []);

  const groups = new Map<string, Product[]>();
  for (const product of products ?? []) {
    groups.set(product.category.name, [...(groups.get(product.category.name) ?? []), product]);
  }

  const columns: Column<Product>[] = [
    {
      key: "product",
      header: "Producto",
      render: (product) => (
        <Link href={`/productos/ficha/?id=${product.id}`} className="text-primary underline-offset-2 hover:underline">
          <span className="block text-sm text-ink-muted">{product.sku}</span>
          {product.name}
        </Link>
      ),
    },
    { key: "stock", header: "Stock", className: "tabular-nums", render: (product) => quantityWithUnit(product.stock, product.unit) },
    { key: "min", header: "Mínimo", className: "tabular-nums", render: (product) => quantityWithUnit(product.min_stock, product.unit) },
    { key: "status", header: "Estado", render: (product) => <ProductStatus product={product} /> },
  ];

  return (
    <AppShell>
      <h1 className="mb-1 text-2xl font-bold">Stock bajo</h1>
      <p className="mb-4 text-ink-muted">Productos activos con stock igual o menor a su mínimo.</p>
      {error && <Alert variant="danger">{error}</Alert>}
      {products && products.length === 0 && (
        <p className="rounded-xl border border-line bg-surface p-6 text-center text-ink-muted">Ningún producto tiene stock bajo.</p>
      )}
      <div className="flex flex-col gap-6">
        {[...groups.entries()].map(([category, items]) => (
          <section key={category} aria-label={category} className="flex flex-col gap-2">
            <h2 className="text-lg font-semibold">
              {category} <span className="text-ink-muted">({items.length})</span>
            </h2>
            <DataTable caption={`Stock bajo en ${category}`} columns={columns} rows={items} rowKey={(product) => product.id} emptyMessage="" />
          </section>
        ))}
      </div>
    </AppShell>
  );
}

export default function LowStockPage() {
  return (
    <RequireAuth roles={["admin", "warehouse"]}>
      <LowStockContent />
    </RequireAuth>
  );
}
