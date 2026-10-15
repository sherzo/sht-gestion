"use client";

// Líneas de la venta (FR-011, FR-012, FR-030; RF-21, RN-10, RN-13): cantidad en metros o
// centímetros para productos por metro y entera para unidades, con el error en la misma
// línea; precio del producto (el vendedor no lo cambia); descuento por ítem y advertencia
// si la cantidad supera el stock, sin bloquear la venta.
import { formatPercent, formatQuantity, formatUsd } from "@sht/shared";
import type { LineResult } from "@sht/shared";
import { AlertTriangle, Percent, Trash2 } from "lucide-react";

import { TextField } from "@/components/ui/field";
import { isMeter, lineQuantity, quantityOf } from "@/lib/sales";
import type { SaleDraft, SaleLine } from "@/lib/sales";

type Props = {
  draft: SaleDraft;
  results: Map<string, LineResult>;
  onChange: (line: SaleLine) => void;
  onRemove: (id: string) => void;
  onDiscount?: (line: SaleLine) => void;
};

function StockWarning({ draft, line }: { draft: SaleDraft; line: SaleLine }) {
  const wanted = quantityOf(draft, line.product.id);
  const stock = Number(line.product.stock);
  if (wanted <= stock) return null;
  return (
    <p className="flex items-center gap-1 text-sm text-warning">
      <AlertTriangle aria-hidden className="size-4" />
      Stock disponible: {formatQuantity(line.product.stock, line.product.unit.decimals)} {line.product.unit.code}; la venta quedará con stock negativo.
    </p>
  );
}

export function SaleLines({ draft, results, onChange, onRemove, onDiscount }: Props) {
  if (draft.lines.length === 0) {
    return <p className="rounded-xl border border-dashed border-line p-6 text-center text-ink-muted">Busca un producto para empezar la venta.</p>;
  }
  return (
    <ul className="flex flex-col divide-y divide-line rounded-xl border border-line bg-surface">
      {draft.lines.map((line) => {
        const quantity = lineQuantity(line);
        const result = results.get(line.id);
        return (
          <li key={line.id} className="flex flex-col gap-2 p-3">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="text-sm text-ink-muted">{line.product.sku}</p>
                <p className="font-medium">{line.product.name}</p>
                <p className="text-sm tabular-nums text-ink-muted">
                  {formatUsd(line.product.sale_price_usd ?? "0")} USD por {line.product.unit.code}
                </p>
              </div>
              <button
                type="button"
                aria-label={`Quitar ${line.product.name}`}
                onClick={() => onRemove(line.id)}
                className="inline-flex size-11 shrink-0 items-center justify-center rounded-lg text-ink-muted hover:bg-neutral-100"
              >
                <Trash2 aria-hidden className="size-5" />
              </button>
            </div>
            <div className="flex flex-wrap items-end gap-2">
              <div className="w-32">
                <TextField
                  label="Cantidad"
                  inputMode="decimal"
                  autoComplete="off"
                  value={line.text}
                  error={quantity.error ?? undefined}
                  onChange={(event) => onChange({ ...line, text: event.target.value })}
                />
              </div>
              {isMeter(line.product) ? (
                <div className="flex rounded-lg border border-line" role="group" aria-label="Unidad de la cantidad">
                  {(["m", "cm"] as const).map((unit) => (
                    <button
                      key={unit}
                      type="button"
                      aria-pressed={line.enteredUnit === unit}
                      onClick={() => onChange({ ...line, enteredUnit: unit })}
                      className={`min-h-11 min-w-11 px-3 font-medium first:rounded-l-lg last:rounded-r-lg ${line.enteredUnit === unit ? "bg-primary text-on-primary" : "hover:bg-neutral-100"}`}
                    >
                      {unit}
                    </button>
                  ))}
                </div>
              ) : (
                <span className="min-h-11 content-center text-ink-muted">{line.product.unit.code}</span>
              )}
              {onDiscount && (
                <button type="button" onClick={() => onDiscount(line)} className="inline-flex min-h-11 items-center gap-1 rounded-lg px-3 font-medium text-primary hover:bg-neutral-100">
                  <Percent aria-hidden className="size-4" />
                  {line.discount ? "Cambiar descuento" : "Descuento"}
                </button>
              )}
              <div className="ml-auto text-right tabular-nums">
                {isMeter(line.product) && line.enteredUnit === "cm" && quantity.quantity && (
                  <p className="text-sm text-ink-muted">= {formatQuantity(quantity.quantity, 2)} m</p>
                )}
                {result && (
                  <>
                    {result.item_discount_usd !== "0.00" && (
                      <p className="text-sm text-ink-muted line-through">{formatUsd(result.line_subtotal_usd)}</p>
                    )}
                    <p className="font-semibold">{formatUsd(result.line_total_usd)} USD</p>
                  </>
                )}
              </div>
            </div>
            {line.discount && (
              <p className="text-sm text-success">
                Descuento {line.discount.type === "percent" ? formatPercent(line.discount.value) : `${formatUsd(line.discount.value)} USD`}
                {line.discount.requestedValue && ` (aprobado en lugar de ${line.discount.type === "percent" ? formatPercent(line.discount.requestedValue) : formatUsd(line.discount.requestedValue)})`}
                {line.discount.authorizationId ? " autorizado" : ""}
              </p>
            )}
            <StockWarning draft={draft} line={line} />
          </li>
        );
      })}
    </ul>
  );
}
