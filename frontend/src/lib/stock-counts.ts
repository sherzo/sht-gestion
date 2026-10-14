// Tipos y textos de los conteos físicos (RF-12, RN-19).
import type { Schemas } from "@/lib/api/client";

export type CountSummary = Schemas["StockCountSummary"];
export type CountAdmin = Schemas["StockCountAdmin"];
export type CountDetail = CountAdmin | Schemas["StockCountWarehouse"];
export type CountLine = Schemas["StockCountLineOut"] | Schemas["StockCountLineBlind"];
export type ApplyResult = Schemas["ApplyResult"];

export const COUNT_STATUS_LABELS: Record<string, string> = {
  open: "Abierto",
  ready_for_review: "Listo para revisión",
  applied: "Aplicado",
  cancelled: "Cancelado",
};

export function isReviewable(count: CountDetail): count is CountAdmin {
  return "lines_with_difference" in count;
}

export function scopeLabel(scope: Record<string, unknown>): string {
  const ids = Array.isArray(scope.ids) ? scope.ids.length : 0;
  if (scope.type === "categories") return `${ids} categoría${ids === 1 ? "" : "s"}`;
  if (scope.type === "products") return `${ids} producto${ids === 1 ? "" : "s"} elegido${ids === 1 ? "" : "s"}`;
  return "Todo el inventario";
}
