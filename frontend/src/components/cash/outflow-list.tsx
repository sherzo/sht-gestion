"use client";

// Egresos de una caja (RF-32, RF-33; FR-003): los anulados se ven tachados con su motivo y
// quién los anuló. El Admin anula uno con motivo mientras la caja sigue abierta.
import { formatDateTime } from "@sht/shared";
import { useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { TextAreaField } from "@/components/ui/field";
import { StatusChip } from "@/components/ui/status-chip";
import { ApiError } from "@/lib/api/client";
import { formatMethodAmount, voidOutflow } from "@/lib/cash";
import type { CashOutflow } from "@/lib/cash";
import { methodLabel } from "@/lib/sales";

type Props = {
  outflows: CashOutflow[];
  /** Admin con la caja abierta: puede anular. */
  canVoid: boolean;
  onChanged: () => void;
};

function VoidOutflowDialog({ outflow, onClose, onDone }: { outflow: CashOutflow; onClose: () => void; onDone: () => void }) {
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function submit() {
    setSaving(true);
    setError(null);
    try {
      await voidOutflow(outflow.id, reason.trim());
      onDone();
      onClose();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No se pudo anular el egreso");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open title="Anular egreso" onClose={onClose}>
      <div className="flex flex-col gap-3">
        <p>
          {methodLabel(outflow.method)} {formatMethodAmount(outflow.amount, outflow.currency)}: {outflow.reason}. El egreso no se borra: queda anulado y
          deja de restar del esperado.
        </p>
        <TextAreaField label="Motivo de la anulación" value={reason} maxLength={200} hint="Obligatorio, de 5 a 200 caracteres." onChange={(event) => setReason(event.target.value)} />
        {error && <Alert variant="danger">{error}</Alert>}
        <Button variant="danger" loading={saving} disabled={reason.trim().length < 5} onClick={() => void submit()}>
          Anular egreso
        </Button>
      </div>
    </Dialog>
  );
}

export function OutflowList({ outflows, canVoid, onChanged }: Props) {
  const [voiding, setVoiding] = useState<CashOutflow | null>(null);
  if (outflows.length === 0) return <p className="text-ink-muted">Sin egresos en esta caja.</p>;
  return (
    <>
      <ul className="flex flex-col gap-2">
        {outflows.map((outflow) => (
          <li key={outflow.id} className="flex flex-col gap-1 rounded-xl border border-line bg-surface p-3 sm:flex-row sm:items-center sm:justify-between">
            <div className={outflow.void ? "text-ink-muted" : ""}>
              <p className={outflow.void ? "line-through" : "font-medium"}>
                {methodLabel(outflow.method)} {formatMethodAmount(outflow.amount, outflow.currency)} · {outflow.reason}
              </p>
              <p className="text-sm text-ink-muted">
                {formatDateTime(outflow.occurred_at)} · {outflow.created_by.full_name}
                {outflow.reference && ` · Ref. ${outflow.reference}`}
              </p>
              {outflow.void && (
                <p className="text-sm">
                  Anulado por {outflow.void.voided_by.full_name} el {formatDateTime(outflow.void.voided_at)}: {outflow.void.reason}
                </p>
              )}
            </div>
            {outflow.void ? (
              <StatusChip variant="voided" label="Anulado" />
            ) : (
              canVoid && (
                <Button variant="secondary" onClick={() => setVoiding(outflow)}>
                  Anular
                </Button>
              )
            )}
          </li>
        ))}
      </ul>
      {voiding && <VoidOutflowDialog outflow={voiding} onClose={() => setVoiding(null)} onDone={onChanged} />}
    </>
  );
}
