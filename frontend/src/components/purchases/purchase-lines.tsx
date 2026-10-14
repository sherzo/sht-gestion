"use client";

// Líneas de una compra (RF-14/FR-004, FR-006, FR-031): producto, cantidad según su unidad
// y costo unitario en la moneda de la compra. Al escribir se muestra cantidad × costo como
// guía; el gasto asignado y el costo final llegan del servidor al guardar (research R4).
import { formatCost, formatQuantity, formatUsd, formatVes } from "@sht/shared";
import { Trash2 } from "lucide-react";

import { ProductPicker } from "@/components/products/product-picker";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { DecimalInput } from "@/components/ui/decimal-input";
import type { Product } from "@/lib/products";
import { costDecimals, previewLineTotal } from "@/lib/purchases";
import type { Currency, PurchaseItem } from "@/lib/purchases";

export type LineDraft = {
  key: string;
  product: { id: string; sku: string; name: string; unit: { code: string; decimals: number } };
  quantity: string;
  cost: string;
};

type PurchaseLinesProps = {
  lines: LineDraft[];
  currency: Currency;
  /** Líneas calculadas por el servidor en el último guardado, por producto. */
  computed: Map<string, PurchaseItem>;
  fields: Record<string, string>;
  disabled?: boolean;
  onChange: (lines: LineDraft[]) => void;
};

function money(value: string, currency: Currency): string {
  return currency === "VES" ? formatVes(value) : `${formatUsd(value)} USD`;
}

export function PurchaseLines({ lines, currency, computed, fields, disabled, onChange }: PurchaseLinesProps) {
  function add(product: Product) {
    if (lines.some((line) => line.product.id === product.id)) return;
    onChange([
      ...lines,
      {
        key: crypto.randomUUID(),
        product: { id: product.id, sku: product.sku, name: product.name, unit: product.unit },
        quantity: "",
        cost: "",
      },
    ]);
  }

  function update(index: number, change: Partial<LineDraft>) {
    onChange(lines.map((line, i) => (i === index ? { ...line, ...change } : line)));
  }

  return (
    <section aria-labelledby="lines-title" className="flex flex-col gap-3">
      <h2 id="lines-title" className="text-lg font-semibold">
        Productos
      </h2>
      {lines.length === 0 && <p className="text-ink-muted">Agrega los productos de la factura.</p>}
      <ol className="flex flex-col gap-3">
        {lines.map((line, index) => {
          const server = computed.get(line.product.id);
          const preview = previewLineTotal(line.quantity, line.cost, line.product.unit.decimals, currency);
          return (
            <li key={line.key} className="rounded-xl border border-line bg-surface p-3">
              <div className="mb-2 flex items-start justify-between gap-2">
                <span className="min-w-0">
                  <span className="block text-sm text-ink-muted">
                    {index + 1}. {line.product.sku}
                  </span>
                  <span className="block font-medium">{line.product.name}</span>
                </span>
                {!disabled && (
                  <Button variant="secondary" aria-label={`Quitar ${line.product.name}`} onClick={() => onChange(lines.filter((_, i) => i !== index))}>
                    <Trash2 aria-hidden className="size-4" />
                  </Button>
                )}
              </div>
              {fields[`items.${index}.product_id`] && <Alert variant="danger">{fields[`items.${index}.product_id`]}</Alert>}
              <div className="grid gap-3 sm:grid-cols-3">
                <DecimalInput
                  label={`Cantidad (${line.product.unit.code})`}
                  decimals={line.product.unit.decimals}
                  value={line.quantity}
                  disabled={disabled}
                  error={fields[`items.${index}.quantity`]}
                  onChange={(text) => update(index, { quantity: text })}
                />
                <DecimalInput
                  label={currency === "VES" ? "Costo unitario (Bs)" : "Costo unitario (USD)"}
                  decimals={costDecimals(currency)}
                  value={line.cost}
                  disabled={disabled}
                  error={fields[`items.${index}.unit_cost`]}
                  onChange={(text) => update(index, { cost: text })}
                />
                <div className="flex flex-col justify-end text-sm">
                  <span className="text-ink-muted">Total de la línea</span>
                  <span className="font-semibold tabular-nums">{preview ? money(preview, currency) : "—"}</span>
                </div>
              </div>
              {server && (
                <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-sm sm:grid-cols-4">
                  {currency === "VES" && (
                    <div>
                      <dt className="text-ink-muted">Costo en USD</dt>
                      <dd className="tabular-nums">{formatCost(server.unit_cost_usd)}</dd>
                    </div>
                  )}
                  <div>
                    <dt className="text-ink-muted">Cantidad guardada</dt>
                    <dd className="tabular-nums">{formatQuantity(server.quantity, line.product.unit.decimals)}</dd>
                  </div>
                  <div>
                    <dt className="text-ink-muted">Gasto asignado</dt>
                    <dd className="tabular-nums">{formatUsd(server.allocated_charges_usd)} USD</dd>
                  </div>
                  <div>
                    <dt className="text-ink-muted">Costo final por unidad</dt>
                    <dd className="font-semibold tabular-nums">{formatCost(server.landed_unit_cost_usd)} USD</dd>
                  </div>
                </dl>
              )}
            </li>
          );
        })}
      </ol>
      {!disabled && <ProductPicker label="Agregar producto" onSelect={add} />}
    </section>
  );
}
