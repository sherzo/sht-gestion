"use client";

// Anulación de una venta (RF-27; FR-041 a FR-043), solo Admin: motivo obligatorio y
// resumen de lo que vuelve. La venta no se borra: queda anulada, el stock vuelve con
// reversos en el kardex y cada pago y vuelto se revierte en la caja de la venta.
import { formatQuantity, formatUsd } from "@sht/shared";
import { useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { TextAreaField } from "@/components/ui/field";
import { ApiError, apiFetch } from "@/lib/api/client";
import { methodLabel } from "@/lib/sales";
import type { Sale } from "@/lib/sales";

type Props = { sale: Sale; open: boolean; onClose: () => void; onVoided: (sale: Sale) => void };

export function VoidSaleDialog({ sale, open, onClose, onVoided }: Props) {
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const valid = reason.trim().length >= 5;

  async function submit() {
    setSaving(true);
    setError(null);
    try {
      onVoided(await apiFetch<Sale>(`/sales/${sale.id}/void`, { method: "POST", body: { reason: reason.trim() } }));
      onClose();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No se pudo anular la venta");
    } finally {
      setSaving(false);
    }
  }

  const received = sale.payments.filter((payment) => payment.kind === "sale_payment");
  const given = sale.payments.filter((payment) => payment.kind === "change");

  return (
    <Dialog open={open} title={`Anular la venta ${sale.number}`} onClose={onClose}>
      <div className="flex flex-col gap-3">
        <p>Se anula la venta completa. Vuelve al inventario:</p>
        <ul className="list-disc pl-5">
          {sale.items.map((item) => (
            <li key={item.id}>
              {formatQuantity(item.quantity, item.product.unit_decimals)} {item.product.unit_code} de {item.product.name}
            </li>
          ))}
        </ul>
        <p>
          Se devuelve en la caja: {received.map((payment) => `${methodLabel(payment.method)} ${formatUsd(payment.amount)}`).join(", ")}
          {given.length > 0 && `; vuelve el vuelto entregado: ${given.map((payment) => `${methodLabel(payment.method)} ${formatUsd(payment.amount)}`).join(", ")}`}.
        </p>
        <TextAreaField
          label="Motivo"
          maxLength={500}
          value={reason}
          hint="Obligatorio, al menos 5 caracteres. Queda en la auditoría."
          onChange={(event) => setReason(event.target.value)}
        />
        {error && <Alert variant="danger">{error}</Alert>}
        <Button variant="danger" loading={saving} disabled={!valid} onClick={() => void submit()}>
          Anular venta
        </Button>
      </div>
    </Dialog>
  );
}
