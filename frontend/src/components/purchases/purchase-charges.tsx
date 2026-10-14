"use client";

// Gastos de la compra (RF-14, RN-20/FR-029 a FR-032): envío, comisión, entrega al local…
// cada uno por porcentaje de la factura o por monto fijo en USD o Bs. Se eligen de la
// lista de gastos frecuentes o se escriben a mano. El monto en USD y el reparto entre
// los productos los calcula el servidor al guardar.
import { formatUsd } from "@sht/shared";
import { ChevronDown, Plus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { DecimalInput } from "@/components/ui/decimal-input";
import { SelectField, TextField } from "@/components/ui/field";
import { apiFetch } from "@/lib/api/client";
import type { ChargeTemplate, Currency, PurchaseCharge } from "@/lib/purchases";

export type ChargeDraft = {
  key: string;
  description: string;
  charge_type: "percent" | "fixed";
  value: string;
  currency: Currency;
  charge_template_id: string | null;
};

type PurchaseChargesProps = {
  charges: ChargeDraft[];
  computed: PurchaseCharge[];
  fields: Record<string, string>;
  disabled?: boolean;
  onChange: (charges: ChargeDraft[]) => void;
};

export function emptyCharge(): ChargeDraft {
  return { key: crypto.randomUUID(), description: "", charge_type: "fixed", value: "", currency: "USD", charge_template_id: null };
}

export function PurchaseCharges({ charges, computed, fields, disabled, onChange }: PurchaseChargesProps) {
  const [open, setOpen] = useState(charges.length > 0);
  const [templates, setTemplates] = useState<ChargeTemplate[]>([]);
  const [templateId, setTemplateId] = useState("");

  useEffect(() => {
    if (charges.length > 0) setOpen(true);
  }, [charges.length]);

  useEffect(() => {
    if (open && !disabled) {
      apiFetch<ChargeTemplate[]>("/charge-templates")
        .then(setTemplates)
        .catch(() => setTemplates([]));
    }
  }, [open, disabled]);

  function update(index: number, change: Partial<ChargeDraft>) {
    onChange(charges.map((charge, i) => (i === index ? { ...charge, ...change } : charge)));
  }

  function addTemplate() {
    const template = templates.find((item) => item.id === templateId);
    if (!template) return;
    onChange([
      ...charges,
      {
        key: crypto.randomUUID(),
        description: template.name,
        charge_type: template.charge_type as ChargeDraft["charge_type"],
        value: template.default_value ? template.default_value.replace(".", ",").replace(/,00$/, "") : "",
        currency: (template.currency as Currency | null) ?? "USD",
        charge_template_id: template.id,
      },
    ]);
    setTemplateId("");
  }

  return (
    <section aria-labelledby="charges-title" className="rounded-xl border border-line bg-surface">
      <button
        type="button"
        aria-expanded={open}
        className="flex min-h-11 w-full items-center justify-between gap-2 px-3 py-2 text-left"
        onClick={() => setOpen(!open)}
      >
        <span id="charges-title" className="text-lg font-semibold">
          Gastos de la compra {charges.length > 0 && <span className="text-ink-muted">({charges.length})</span>}
        </span>
        <ChevronDown aria-hidden className={`size-5 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <div className="flex flex-col gap-3 border-t border-line p-3">
          <p className="text-sm text-ink-muted">
            Envío, comisión de compra, entrega al local… Se reparten entre los productos según su valor y forman su costo final.
          </p>
          {charges.map((charge, index) => {
            const server = computed[index];
            return (
              <div key={charge.key} className="grid gap-3 rounded-lg border border-line p-3 sm:grid-cols-[2fr_1fr_1fr_1fr_auto] sm:items-end">
                <TextField
                  label="Descripción"
                  maxLength={120}
                  value={charge.description}
                  disabled={disabled}
                  error={fields[`charges.${index}.description`] ?? fields[`charges.${index}`]}
                  onChange={(event) => update(index, { description: event.target.value })}
                />
                <SelectField
                  label="Tipo"
                  value={charge.charge_type}
                  disabled={disabled}
                  onChange={(event) => update(index, { charge_type: event.target.value as ChargeDraft["charge_type"] })}
                  options={[
                    { value: "fixed", label: "Monto fijo" },
                    { value: "percent", label: "% de la factura" },
                  ]}
                />
                <DecimalInput
                  label={charge.charge_type === "percent" ? "Porcentaje" : "Monto"}
                  decimals={2}
                  value={charge.value}
                  disabled={disabled}
                  error={fields[`charges.${index}.percent`] ?? fields[`charges.${index}.amount`]}
                  onChange={(text) => update(index, { value: text })}
                />
                {charge.charge_type === "fixed" ? (
                  <SelectField
                    label="Moneda"
                    value={charge.currency}
                    disabled={disabled}
                    onChange={(event) => update(index, { currency: event.target.value as Currency })}
                    options={[
                      { value: "USD", label: "USD" },
                      { value: "VES", label: "Bs" },
                    ]}
                  />
                ) : (
                  <div className="text-sm">
                    <span className="block text-ink-muted">En USD</span>
                    <span className="tabular-nums">{server ? `${formatUsd(server.amount_usd)} USD` : "—"}</span>
                  </div>
                )}
                {!disabled && (
                  <Button variant="secondary" aria-label={`Quitar ${charge.description || "gasto"}`} onClick={() => onChange(charges.filter((_, i) => i !== index))}>
                    <Trash2 aria-hidden className="size-4" />
                  </Button>
                )}
                {charge.charge_type === "fixed" && server && (
                  <p className="text-sm text-ink-muted sm:col-span-5">En USD: {formatUsd(server.amount_usd)}</p>
                )}
              </div>
            );
          })}
          {!disabled && (
            <div className="grid gap-3 sm:grid-cols-[1fr_auto_auto] sm:items-end">
              <SelectField
                label="Gasto frecuente"
                value={templateId}
                onChange={(event) => setTemplateId(event.target.value)}
                options={[{ value: "", label: templates.length ? "Elige uno…" : "No hay gastos frecuentes" }, ...templates.map((t) => ({ value: t.id, label: t.name }))]}
              />
              <Button variant="secondary" disabled={!templateId} onClick={addTemplate}>
                <Plus aria-hidden className="size-4" /> Agregar frecuente
              </Button>
              <Button variant="secondary" onClick={() => onChange([...charges, emptyCharge()])}>
                <Plus aria-hidden className="size-4" /> Agregar gasto
              </Button>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
