"use client";

// Pagos mixtos y vuelto (RF-23 a RF-25; RN-04, RN-06; FR-033 a FR-038): uno o varios pagos
// con los seis métodos, referencia obligatoria salvo en efectivo, saldo en USD y Bs después
// de cada pago y vuelto en uno o varios métodos. Si el vuelto es menor que el excedente
// (por ejemplo, sin sencillo), la diferencia queda como sobrepago de la venta.
import { formatUsd, formatVes, suggestedVes, uuidv7 } from "@sht/shared";
import type { SaleCalcResult } from "@sht/shared";
import { AlertCircle, Plus, Trash2 } from "lucide-react";

import { DecimalInput } from "@/components/ui/decimal-input";
import { SelectField, TextField } from "@/components/ui/field";
import { PAYMENT_METHODS, entryAmount, paymentMethod } from "@/lib/sales";
import type { MoneyEntry, PaymentMethodCode } from "@/lib/sales";

type Props = {
  payments: MoneyEntry[];
  change: MoneyEntry[];
  result: SaleCalcResult | null;
  /** Error del vuelto (por ejemplo, mayor que el excedente): se muestra junto al vuelto. */
  changeError?: string | null;
  rate: string;
  disabled?: boolean;
  onPayments: (entries: MoneyEntry[]) => void;
  onChange: (entries: MoneyEntry[]) => void;
};

const METHOD_OPTIONS = PAYMENT_METHODS.map((method) => ({ value: method.code, label: method.name }));

/** Monto en la moneda del método que cubre `usd` (Bs con la tasa de la venta, RN-06). */
function amountFor(method: PaymentMethodCode, usd: string, rate: string): string {
  const value = paymentMethod(method).currency === "VES" ? suggestedVes(usd, rate) : usd;
  return value.replace(".", ",");
}

function EntryRow({
  entry,
  label,
  disabled,
  onUpdate,
  onRemove,
}: {
  entry: MoneyEntry;
  label: string;
  disabled?: boolean;
  onUpdate: (entry: MoneyEntry) => void;
  onRemove: () => void;
}) {
  const method = paymentMethod(entry.method);
  const missingReference = method.requiresReference && !entry.reference.trim();
  return (
    <li className="grid gap-2 rounded-lg border border-line p-2 sm:grid-cols-[1fr_8rem_1fr_auto] sm:items-end">
      <SelectField label={label} value={entry.method} options={METHOD_OPTIONS} disabled={disabled} onChange={(event) => onUpdate({ ...entry, method: event.target.value as PaymentMethodCode })} />
      <DecimalInput
        label={`Monto (${method.currency === "VES" ? "Bs" : method.currency})`}
        decimals={2}
        value={entry.text}
        disabled={disabled}
        error={entry.text.trim() && entryAmount(entry) === null ? "Debe ser mayor que cero" : undefined}
        onChange={(text) => onUpdate({ ...entry, text })}
      />
      {method.requiresReference ? (
        <TextField
          label="Referencia"
          value={entry.reference}
          maxLength={60}
          disabled={disabled}
          error={missingReference ? "Este método exige referencia" : undefined}
          onChange={(event) => onUpdate({ ...entry, reference: event.target.value })}
        />
      ) : (
        <span aria-hidden />
      )}
      <button type="button" aria-label="Quitar" disabled={disabled} onClick={onRemove} className="inline-flex size-11 items-center justify-center rounded-lg text-ink-muted hover:bg-neutral-100 disabled:opacity-60">
        <Trash2 aria-hidden className="size-5" />
      </button>
    </li>
  );
}

export function PaymentsPanel({ payments, change, result, changeError = null, rate, disabled, onPayments, onChange }: Props) {
  const balance = result?.balance_usd ?? "0.00";
  const excess = result?.excess_usd ?? "0.00";
  const pending = Number(balance) > 0;

  function addPayment(method: PaymentMethodCode) {
    onPayments([...payments, { id: uuidv7(), method, text: pending ? amountFor(method, balance, rate) : "", reference: "" }]);
  }

  function addChange(method: PaymentMethodCode) {
    const given = change.reduce((total, entry) => total + Number(entryAmount(entry) ?? 0), 0);
    const left = Math.max(Number(excess) - given, 0).toFixed(2);
    onChange([...change, { id: uuidv7(), method, text: amountFor(method, left, rate), reference: "" }]);
  }

  return (
    <section aria-labelledby="pagos" className="flex flex-col gap-3 rounded-xl border border-line bg-surface p-4">
      <h2 id="pagos" className="text-lg font-semibold">
        Pagos
      </h2>
      {payments.length > 0 && (
        <ul className="flex flex-col gap-2">
          {payments.map((entry, index) => (
            <EntryRow
              key={entry.id}
              entry={entry}
              label={`Pago ${index + 1}`}
              disabled={disabled}
              onUpdate={(updated) => onPayments(payments.map((item) => (item.id === entry.id ? updated : item)))}
              onRemove={() => onPayments(payments.filter((item) => item.id !== entry.id))}
            />
          ))}
        </ul>
      )}
      <div className="tabular-nums">
        {pending ? (
          <p className="text-lg font-semibold text-danger">
            Falta: {formatUsd(balance)} USD · {formatVes(result?.balance_ves ?? "0")}
          </p>
        ) : (
          result && Number(result.total_usd) > 0 && <p className="text-lg font-semibold text-success">Pagado</p>
        )}
      </div>
      <div className="flex flex-wrap gap-2" aria-label="Agregar pago">
        {PAYMENT_METHODS.map((method) => (
          <button
            key={method.code}
            type="button"
            disabled={disabled}
            onClick={() => addPayment(method.code)}
            className="inline-flex min-h-11 items-center gap-1 rounded-lg border border-line px-3 text-sm font-medium hover:bg-neutral-100 disabled:opacity-60"
          >
            <Plus aria-hidden className="size-4" /> {method.name}
          </button>
        ))}
      </div>

      {Number(excess) > 0 && (
        <div className="flex flex-col gap-2 border-t border-line pt-3">
          <h3 className="font-semibold">
            Vuelto: {formatUsd(excess)} USD · {formatVes(suggestedVes(excess, rate))}
          </h3>
          {change.length > 0 && (
            <ul className="flex flex-col gap-2">
              {change.map((entry, index) => (
                <EntryRow
                  key={entry.id}
                  entry={entry}
                  label={`Vuelto ${index + 1}`}
                  disabled={disabled}
                  onUpdate={(updated) => onChange(change.map((item) => (item.id === entry.id ? updated : item)))}
                  onRemove={() => onChange(change.filter((item) => item.id !== entry.id))}
                />
              ))}
            </ul>
          )}
          <div className="flex flex-wrap gap-2" aria-label="Entregar vuelto">
            {PAYMENT_METHODS.filter((method) => ["cash_usd", "cash_ves", "mobile_payment"].includes(method.code)).map((method) => (
              <button
                key={method.code}
                type="button"
                disabled={disabled}
                onClick={() => addChange(method.code)}
                className="inline-flex min-h-11 items-center gap-1 rounded-lg border border-line px-3 text-sm font-medium hover:bg-neutral-100 disabled:opacity-60"
              >
                <Plus aria-hidden className="size-4" /> Vuelto en {method.name}
              </button>
            ))}
          </div>
          {changeError && (
            <p role="alert" className="flex items-start gap-2 rounded-lg bg-danger-soft p-3 font-semibold text-danger">
              <AlertCircle aria-hidden className="mt-0.5 size-5 shrink-0" />
              <span>
                {changeError}. Como máximo: {formatUsd(excess)} USD o {formatVes(suggestedVes(excess, rate))}. Corrige el monto o quita el vuelto.
              </span>
            </p>
          )}
          {!changeError && result && Number(result.overpaid_usd) > 0 && change.length > 0 && (
            <p className="text-sm text-ink-muted">Sobrepago: {formatUsd(result.overpaid_usd)} USD (el cliente deja la diferencia).</p>
          )}
        </div>
      )}
    </section>
  );
}
