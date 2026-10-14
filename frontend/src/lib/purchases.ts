"use client";

// Tipos y utilidades de compras, proveedores, tasa y gastos (etapa 1.2). El servidor
// calcula todos los montos (research R4): la pantalla solo muestra lo que recibe y, al
// escribir, la cantidad × costo de cada línea como guía.
import { parseDecimalInput } from "@sht/shared";

import type { StatusChipVariant } from "@/components/ui/status-chip";
import type { Schemas } from "@/lib/api/client";

export type Purchase = Schemas["PurchaseOut"];
export type PurchaseConfirmedAdmin = Schemas["PurchaseConfirmedAdmin"];
export type PurchaseSummary = Schemas["PurchaseSummary"];
export type PurchasePage = Schemas["PurchasePage"];
export type PurchaseItem = Schemas["PurchaseItemOut"];
export type PurchaseCharge = Schemas["PurchaseChargeOut"];
export type Supplier = Schemas["SupplierOut"];
export type SupplierPage = Schemas["SupplierPage"];
export type ChargeTemplate = Schemas["ChargeTemplateOut"];
export type ApplicableRate = Schemas["ApplicableRateOut"];
export type VoidPreview = Schemas["VoidPreview"];
export type Currency = "USD" | "VES";

export const PURCHASE_STATUS: Record<string, { label: string; chip: StatusChipVariant }> = {
  draft: { label: "Borrador", chip: "draft" },
  confirmed: { label: "Confirmada", chip: "confirmed" },
  voided: { label: "Anulada", chip: "voided" },
};

export const CURRENCY_LABELS: Record<Currency, string> = { USD: "Dólares (USD)", VES: "Bolívares (Bs)" };

/** Decimales que admite el costo unitario según la moneda (ADR-0004). */
export function costDecimals(currency: Currency): number {
  return currency === "VES" ? 2 : 6;
}

/**
 * Cantidad × costo escritos por el usuario, solo como guía mientras escribe: el total
 * real lo calcula el servidor al guardar. Devuelve null si algún número no es válido.
 */
export function previewLineTotal(quantity: string, cost: string, quantityDecimals: number, currency: Currency): string | null {
  const q = parseDecimalInput(quantity, quantityDecimals);
  const c = parseDecimalInput(cost, costDecimals(currency));
  if (q === null || c === null) return null;
  // Producto exacto con enteros escalados, sin pasar por coma flotante.
  const scale = (text: string) => {
    const [integer, fraction = ""] = text.split(".");
    return { digits: BigInt(integer + fraction), places: fraction.length };
  };
  const a = scale(q);
  const b = scale(c);
  const places = a.places + b.places;
  const product = (a.digits * b.digits).toString().padStart(places + 1, "0");
  const integer = product.slice(0, product.length - places) || "0";
  const fraction = product.slice(product.length - places);
  // Redondeo a 2 decimales, mitad hacia arriba (ADR-0004).
  const cents = BigInt(integer + fraction.padEnd(2, "0").slice(0, 2)) + (fraction.length > 2 && Number(fraction[2]) >= 5 ? 1n : 0n);
  const text = cents.toString().padStart(3, "0");
  return `${text.slice(0, -2)}.${text.slice(-2)}`;
}
