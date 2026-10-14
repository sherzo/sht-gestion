"use client";

// Ficha de producto (FR-035): datos, fotos y, según el rol, precio, costo y kardex. La
// ruta es estática y recibe el producto en `?id=` (export estático, research R13).
import { formatUsd } from "@sht/shared";
import { ArrowLeft, Pencil, Power, SlidersHorizontal } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { KardexTable } from "@/components/products/kardex-table";
import { PhotoGallery } from "@/components/products/photo-gallery";
import { PriceCostPanel } from "@/components/products/price-cost-panel";
import { ProductForm } from "@/components/products/product-form";
import { ProductStatus } from "@/components/products/product-status";
import { RequireAuth } from "@/components/require-auth";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Tabs } from "@/components/ui/tabs";
import type { TabItem } from "@/components/ui/tabs";
import { ApiError, apiFetch } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/use-auth";
import { WARNING_MESSAGES, hasCost, hasPrice, quantityWithUnit, useCatalogConfig } from "@/lib/products";
import type { Category, Product } from "@/lib/products";

function attributeLabel(category: Category | undefined, key: string): string {
  return category?.attributes.find((attribute) => attribute.key === key)?.label ?? key;
}

function Warnings({ warnings }: { warnings: string[] }) {
  if (warnings.length === 0) return null;
  return (
    <div className="flex flex-col gap-2">
      {warnings.map((warning) => (
        <Alert key={warning} variant="warning">
          {WARNING_MESSAGES[warning] ?? warning}
        </Alert>
      ))}
    </div>
  );
}

function ProductData({ product, category }: { product: Product; category?: Category }) {
  const attributes = Object.entries(product.attributes);
  const rows: [string, string][] = [
    ["SKU", product.sku],
    ["Categoría", product.category.name],
    ["Unidad", `${product.unit.name} (${product.unit.code})`],
    ["Stock", quantityWithUnit(product.stock, product.unit)],
    ["Stock mínimo", quantityWithUnit(product.min_stock, product.unit)],
    // El precio solo llega a Admin y Vendedor (research R6).
    ...(hasPrice(product) ? [["Precio de venta", product.sale_price_usd ? `${formatUsd(product.sale_price_usd)} USD` : "Sin precio"] as [string, string]] : []),
    ...attributes.map(([key, value]): [string, string] => [attributeLabel(category, key), value]),
  ];
  return (
    <div className="flex flex-col gap-4">
      <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-2">
        {rows.map(([label, value]) => (
          <div key={label}>
            <dt className="text-sm text-ink-muted">{label}</dt>
            <dd className="font-medium tabular-nums">{value}</dd>
          </div>
        ))}
      </dl>
      {product.description && (
        <div>
          <h3 className="text-sm text-ink-muted">Descripción</h3>
          <p className="whitespace-pre-line">{product.description}</p>
        </div>
      )}
    </div>
  );
}

function ProductDetail({ id }: { id: string }) {
  const { user } = useAuth();
  const searchParams = useSearchParams();
  const { categories, units } = useCatalogConfig();
  const [product, setProduct] = useState<Product | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [warnings, setWarnings] = useState<string[]>(() => searchParams.get("avisos")?.split(",").filter(Boolean) ?? []);
  const [notice, setNotice] = useState<string | null>(() => (searchParams.get("nuevo") ? "Producto creado." : null));
  const [tab, setTab] = useState("data");
  const [editing, setEditing] = useState(false);
  const [toggling, setToggling] = useState(false);
  const [busy, setBusy] = useState(false);
  const canEdit = user?.role === "admin" || user?.role === "warehouse";

  const load = useCallback(async () => {
    try {
      setProduct(await apiFetch<Product>(`/products/${id}`));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No se pudo cargar el producto");
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  function saved(next: Product, message: string) {
    setProduct(next);
    setWarnings(next.warnings);
    setNotice(message);
    setEditing(false);
  }

  async function toggleActive() {
    if (!product) return;
    setBusy(true);
    try {
      const next = await apiFetch<Product>(`/products/${product.id}`, {
        method: "PATCH",
        body: { is_active: !product.is_active, updated_at: product.updated_at },
      });
      saved(next, next.is_active ? "Producto reactivado." : "Producto desactivado.");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No se pudo cambiar el estado");
    } finally {
      setBusy(false);
      setToggling(false);
    }
  }

  if (error && !product) {
    return <Alert variant="danger">{error}</Alert>;
  }
  if (!product) {
    return <p className="text-ink-muted">Cargando…</p>;
  }

  const category = categories.find((item) => item.id === product.category.id);
  const tabs: TabItem[] = [
    { id: "data", label: "Datos" },
    { id: "photos", label: `Fotos (${product.photos.length})` },
    ...(hasCost(product) ? [{ id: "price", label: "Precio y costo" }] : []),
    // El Vendedor solo ve el stock actual, no el kardex (FR-022).
    ...(canEdit ? [{ id: "kardex", label: "Kardex" }] : []),
  ];

  return (
    <>
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm text-ink-muted">{product.sku}</p>
          <h1 className="text-2xl font-bold">{product.name}</h1>
          <div className="mt-2">
            <ProductStatus product={product} />
          </div>
        </div>
        {canEdit && !editing && (
          <div className="flex flex-wrap gap-2">
            <Link
              href={`/inventario/ajuste/?producto=${product.id}`}
              className="inline-flex min-h-11 items-center gap-2 rounded-lg border border-line bg-surface px-4 font-semibold text-ink hover:bg-neutral-100"
            >
              <SlidersHorizontal aria-hidden className="size-4" /> Ajustar stock
            </Link>
            <Button variant="secondary" onClick={() => { setTab("data"); setEditing(true); }}>
              <Pencil aria-hidden className="size-4" /> Editar
            </Button>
            <Button variant="secondary" onClick={() => setToggling(true)}>
              <Power aria-hidden className="size-4" /> {product.is_active ? "Desactivar" : "Reactivar"}
            </Button>
          </div>
        )}
      </div>
      <div className="mb-4 flex flex-col gap-2">
        {notice && <Alert variant="success">{notice}</Alert>}
        {error && <Alert variant="danger">{error}</Alert>}
        <Warnings warnings={warnings} />
      </div>
      <Tabs tabs={tabs} active={tab} onChange={setTab} label="Secciones del producto">
        <div className="rounded-xl border border-line bg-surface p-4 sm:p-6">
          {tab === "data" &&
            (editing && categories.length > 0 ? (
              <ProductForm
                categories={categories}
                units={units}
                product={product}
                onSaved={(next) => saved(next, "Cambios guardados.")}
                onCancel={() => setEditing(false)}
              />
            ) : (
              <ProductData product={product} category={category} />
            ))}
          {tab === "photos" && <PhotoGallery product={product} editable={canEdit} onChanged={setProduct} />}
          {tab === "kardex" && canEdit && <KardexTable product={product} />}
          {tab === "price" && hasCost(product) && <PriceCostPanel product={product} onChanged={setProduct} />}
        </div>
      </Tabs>
      <Dialog open={toggling} title={product.is_active ? "Desactivar producto" : "Reactivar producto"} onClose={() => setToggling(false)}>
        <p>
          {product.is_active
            ? "El producto dejará de aparecer para vender y en el catálogo. Conserva su SKU e historial y se puede reactivar."
            : "El producto volverá a aparecer para vender."}
        </p>
        <div className="flex flex-wrap gap-2">
          <Button variant={product.is_active ? "danger" : "primary"} loading={busy} onClick={toggleActive}>
            {product.is_active ? "Desactivar" : "Reactivar"}
          </Button>
          <Button variant="secondary" onClick={() => setToggling(false)}>
            Cancelar
          </Button>
        </div>
      </Dialog>
    </>
  );
}

function DetailPage() {
  const id = useSearchParams().get("id");
  return (
    <AppShell>
      <Link href="/productos/" className="mb-3 inline-flex min-h-11 items-center gap-2 text-primary">
        <ArrowLeft aria-hidden className="size-5" /> Productos
      </Link>
      {id ? <ProductDetail key={id} id={id} /> : <Alert variant="danger">Falta el producto.</Alert>}
    </AppShell>
  );
}

export default function ProductDetailPage() {
  return (
    <RequireAuth>
      <Suspense fallback={null}>
        <DetailPage />
      </Suspense>
    </RequireAuth>
  );
}
