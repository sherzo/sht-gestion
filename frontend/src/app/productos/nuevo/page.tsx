"use client";

// Alta de producto (RF-01/FR-001): Admin y Almacén. El SKU lo asigna el servidor (RF-02).
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { ProductForm } from "@/components/products/product-form";
import { RequireAuth } from "@/components/require-auth";
import { Alert } from "@/components/ui/alert";
import { useCatalogConfig } from "@/lib/products";

function NewProductContent() {
  const router = useRouter();
  const { categories, units, error } = useCatalogConfig();

  return (
    <AppShell>
      <Link href="/productos/" className="mb-3 inline-flex min-h-11 items-center gap-2 text-primary">
        <ArrowLeft aria-hidden className="size-5" /> Productos
      </Link>
      <h1 className="mb-4 text-2xl font-bold">Nuevo producto</h1>
      {error && <Alert variant="danger">{error}</Alert>}
      {categories.length > 0 && units.length > 0 && (
        <div className="max-w-3xl rounded-xl border border-line bg-surface p-4 sm:p-6">
          <ProductForm
            categories={categories}
            units={units}
            onSaved={(product) => {
              const warnings = product.warnings.length ? `&avisos=${product.warnings.join(",")}` : "";
              router.push(`/productos/ficha/?id=${product.id}&nuevo=1${warnings}`);
            }}
            onCancel={() => router.push("/productos/")}
          />
        </div>
      )}
    </AppShell>
  );
}

export default function NewProductPage() {
  return (
    <RequireAuth roles={["admin", "warehouse"]}>
      <NewProductContent />
    </RequireAuth>
  );
}
