"use client";

// Tipos y utilidades de productos e inventario compartidos por las pantallas de la etapa
// 1.1b. El servidor responde con un esquema por rol (research R6): el precio solo llega al
// Admin y al Vendedor, y el costo solo al Admin.
import { formatQuantity } from "@sht/shared";
import { useEffect, useState } from "react";

import type { StatusChipVariant } from "@/components/ui/status-chip";
import { apiFetch } from "@/lib/api/client";
import type { Schemas } from "@/lib/api/client";

export type ProductAdmin = Schemas["ProductAdmin"];
export type ProductSeller = Schemas["ProductSeller"];
export type Product = ProductAdmin | ProductSeller | Schemas["ProductWarehouse"];
export type ProductPage = Schemas["ProductPage"];
export type Category = Schemas["CategoryOut"];
export type Unit = Schemas["UnitOut"];
export type Attribute = Schemas["AttributeOut"];

export function hasPrice(product: Product): product is ProductAdmin | ProductSeller {
  return "sale_price_usd" in product;
}

export function hasCost(product: Product): product is ProductAdmin {
  return "avg_cost_usd" in product;
}

/** `35,50 m` o `12 u`. */
export function quantityWithUnit(value: string, unit: { code: string; decimals: number }): string {
  return `${formatQuantity(value, unit.decimals)} ${unit.code}`;
}

export function isNegative(value: string): boolean {
  return value.trim().startsWith("-");
}

/** Estados visibles de un producto, en orden de importancia. */
export function productChips(product: Product): StatusChipVariant[] {
  const chips: StatusChipVariant[] = [];
  if (isNegative(product.stock)) chips.push("negative_stock");
  else if (product.is_low_stock) chips.push("low_stock");
  if (!product.is_active) chips.push("inactive");
  if (product.is_published) chips.push("published");
  return chips;
}

/** Avisos que no bloquean el guardado (research R10 y R15). */
export const WARNING_MESSAGES: Record<string, string> = {
  duplicate_name: "Ya existe otro producto activo con el mismo nombre en esta categoría.",
  has_stock: "El producto quedó inactivo pero todavía tiene stock: sigue en el inventario y en los conteos.",
  stale_data: "Otra persona había cambiado este producto mientras lo editabas. Se guardaron tus cambios; revisa los datos actuales.",
};

export const ADJUSTMENT_REASONS = [
  { value: "correction", label: "Corrección" },
  { value: "damage", label: "Daño" },
  { value: "loss", label: "Pérdida" },
  { value: "physical_count", label: "Conteo físico" },
] as const;

export const ADJUSTMENT_REASON_LABELS: Record<string, string> = Object.fromEntries(
  ADJUSTMENT_REASONS.map((reason) => [reason.value, reason.label]),
);

export const MOVEMENT_TYPE_LABELS: Record<string, string> = {
  purchase: "Entrada por compra",
  sale: "Salida por venta",
  sale_void: "Reverso de venta anulada",
  purchase_void: "Reverso de compra anulada",
  adjustment: "Ajuste",
};

/** Categorías y unidades activas, cargadas una vez por pantalla. */
export function useCatalogConfig(includeInactive = false) {
  const [categories, setCategories] = useState<Category[]>([]);
  const [units, setUnits] = useState<Unit[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    const query = { include_inactive: includeInactive || undefined };
    Promise.all([apiFetch<Category[]>("/categories", { query }), apiFetch<Unit[]>("/units", { query })])
      .then(([loadedCategories, loadedUnits]) => {
        setCategories(loadedCategories);
        setUnits(loadedUnits);
      })
      .catch(() => setError("No se pudieron cargar las categorías"));
  }, [includeInactive, version]);

  return { categories, units, error, reload: () => setVersion((current) => current + 1) };
}
