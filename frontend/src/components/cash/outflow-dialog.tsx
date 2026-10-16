"use client";

// Registro de un egreso de caja (RF-32, PRD v0.12; FR-001, FR-002): método, monto en su
// moneda, motivo y, si no es efectivo, la referencia. En efectivo muestra el disponible y
// no deja superarlo; los demás métodos no tienen tope. Sin autorización del Admin.
import { parseDecimalInput } from "@sht/shared";
import { useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { DecimalInput } from "@/components/ui/decimal-input";
import { Dialog } from "@/components/ui/dialog";
import { SelectField, TextAreaField, TextField } from "@/components/ui/field";
import { enqueueOutflow, formatMethodAmount, isCashMethod, toCents } from "@/lib/cash";
import { paymentMethod, PAYMENT_METHODS } from "@/lib/sales";

type Props = {
  open: boolean;
  sessionId: string;
  /** Esperado actual por método, para el tope del efectivo. */
  expected: Record<string, string>;
  onClose: () => void;
  onDone: () => void;
};

const REASON_MAX = 200;

export function OutflowDialog({ open, sessionId, expected, onClose, onDone }: Props) {
  const [method, setMethod] = useState("cash_usd");
  const [amountText, setAmountText] = useState("");
  const [reason, setReason] = useState("");
  const [reference, setReference] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const info = paymentMethod(method);
  const cash = isCashMethod(method);
  const amount = amountText.trim() ? parseDecimalInput(amountText, 2) : null;
  const available = expected[method] ?? "0.00";
  const overLimit = cash && amount !== null && toCents(amount) > toCents(available);
  const valid =
    amount !== null &&
    toCents(amount) > 0n &&
    !overLimit &&
    reason.trim().length >= 5 &&
    (!info.requiresReference || reference.trim().length > 0);

  function reset() {
    setAmountText("");
    setReason("");
    setReference("");
    setError(null);
  }

  async function submit() {
    if (!valid || amount === null) return;
    setSaving(true);
    setError(null);
    const outcome = await enqueueOutflow(sessionId, method, amount, reason.trim(), info.requiresReference ? reference.trim() : null);
    setSaving(false);
    if (!outcome.ok) {
      setError(outcome.message);
      return;
    }
    reset();
    onDone();
    onClose();
  }

  return (
    <Dialog open={open} title="Registrar egreso" onClose={onClose}>
      <div className="flex flex-col gap-3">
        <p className="text-ink-muted">Dinero que sale de la caja sin ser vuelto: agua, limpieza, un delivery, un retiro.</p>
        <SelectField
          label="Sale de"
          value={method}
          options={PAYMENT_METHODS.map((item) => ({ value: item.code, label: item.name }))}
          onChange={(event) => setMethod(event.target.value)}
        />
        <DecimalInput
          label={`Monto en ${info.currency === "VES" ? "Bs" : info.currency}`}
          decimals={2}
          value={amountText}
          placeholder="0,00"
          hint={cash ? `Disponible: ${formatMethodAmount(available, info.currency)}` : "Sin tope: la cuenta puede tener dinero de otros días."}
          error={overLimit ? `Supera el disponible (${formatMethodAmount(available, info.currency)})` : undefined}
          onChange={setAmountText}
        />
        {info.requiresReference && (
          <TextField label="Referencia" value={reference} maxLength={60} hint="Obligatoria en este método." onChange={(event) => setReference(event.target.value)} />
        )}
        <TextAreaField
          label="Motivo"
          value={reason}
          maxLength={REASON_MAX}
          hint={`Obligatorio, de 5 a ${REASON_MAX} caracteres (${reason.length}/${REASON_MAX}).`}
          onChange={(event) => setReason(event.target.value)}
        />
        {error && <Alert variant="danger">{error}</Alert>}
        <Button loading={saving} disabled={!valid} onClick={() => void submit()}>
          Registrar egreso
        </Button>
      </div>
    </Dialog>
  );
}
