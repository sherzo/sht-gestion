"use client";

// Anular una compra confirmada (RN-14/FR-017 a FR-019), solo el Admin: muestra por
// producto el stock y el costo que quedarán, destaca los que quedan en cero o negativo o
// conservan su costo (y generarán una alerta), y exige el motivo.
import { formatCost, formatQuantity } from "@sht/shared";
import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { TextAreaField } from "@/components/ui/field";
import { ApiError, apiFetch } from "@/lib/api/client";
import type { Purchase, VoidPreview } from "@/lib/purchases";

type VoidDialogProps = {
  purchase: Purchase;
  open: boolean;
  onClose: () => void;
  onVoided: (message: string) => void;
};

export function VoidDialog({ purchase, open, onClose, onVoided }: VoidDialogProps) {
  const [preview, setPreview] = useState<VoidPreview | null>(null);
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setReason("");
    setError(null);
    setFields({});
    setPreview(null);
    apiFetch<VoidPreview>(`/purchases/${purchase.id}/void-preview`)
      .then(setPreview)
      .catch((caught) => setError(caught instanceof ApiError ? caught.message : "No se pudo calcular la anulación"));
  }, [open, purchase.id]);

  const decimals = new Map(purchase.items.map((item) => [item.product.id, item.product.unit.decimals]));

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const result = await apiFetch<{ alerts_created: number }>(`/purchases/${purchase.id}/void`, {
        method: "POST",
        body: { reason },
      });
      onVoided(
        result.alerts_created
          ? `Compra ${purchase.number} anulada. Se conservó el costo de ${result.alerts_created} producto(s) y quedó una alerta en Pendientes.`
          : `Compra ${purchase.number} anulada.`,
      );
    } catch (caught) {
      if (caught instanceof ApiError) {
        setError(caught.message);
        setFields(caught.fields);
      } else {
        setError("Ocurrió un error inesperado");
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} title={`Anular la compra ${purchase.number ?? ""}`} onClose={onClose}>
      <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
        <p>
          El stock de cada producto baja por lo que entró con esta compra y su costo vuelve al de antes. La compra queda anulada y no se puede
          deshacer.
        </p>
        {error && <Alert variant="danger">{error}</Alert>}
        {preview && (
          <ul className="flex flex-col divide-y divide-line rounded-xl border border-line">
            {preview.items.map((line) => {
              const unitDecimals = decimals.get(line.product_id) ?? 2;
              const risky = line.keeps_cost || !/[1-9]/.test(line.stock_after) || line.stock_after.startsWith("-");
              return (
                <li key={line.product_id} className={`p-3 text-sm ${risky ? "bg-warning-soft" : ""}`}>
                  <span className="block font-medium">{line.sku}</span>
                  <span className="block tabular-nums">
                    Stock: {formatQuantity(line.stock_before, unitDecimals)} → {formatQuantity(line.stock_after, unitDecimals)}
                  </span>
                  <span className="block tabular-nums">
                    Costo: {line.cost_before_usd ? formatCost(line.cost_before_usd) : "—"} →{" "}
                    {line.cost_after_usd ? formatCost(line.cost_after_usd) : "—"} USD
                  </span>
                  {line.keeps_cost && <span className="block font-medium text-warning">Se conserva el costo vigente y se crea una alerta.</span>}
                </li>
              );
            })}
          </ul>
        )}
        <TextAreaField
          label="Motivo de la anulación"
          hint="Entre 5 y 500 caracteres. Queda en la auditoría."
          maxLength={500}
          rows={3}
          value={reason}
          error={fields.reason}
          onChange={(event) => setReason(event.target.value)}
        />
        <Button type="submit" variant="danger" loading={saving} disabled={reason.trim().length < 5 || !preview}>
          Anular compra
        </Button>
      </form>
    </Dialog>
  );
}
