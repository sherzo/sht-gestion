"use client";

// Anulación de una venta (RF-27; FR-041 a FR-043 de la 1.3), solo Admin: motivo obligatorio
// y resumen de lo que vuelve. La venta no se borra: queda anulada, el stock vuelve con
// reversos en el kardex y cada pago y vuelto se revierte en una caja. Si la caja de la venta
// sigue abierta, en ella; si ya está cerrada, en la caja abierta del equipo desde el que se
// anula, y el cierre anterior no cambia (PRD v0.11; FR-020 a FR-022 de la 1.4, research R8).
import { formatQuantity, formatUsd } from "@sht/shared";
import { useEffect, useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { TextAreaField } from "@/components/ui/field";
import { ApiError, apiFetch } from "@/lib/api/client";
import { formatMethodAmount, getCashSession, isCashMethod, reconcile, toCents } from "@/lib/cash";
import { getDevice } from "@/lib/device/device-store";
import type { DeviceRecord } from "@/lib/device/device-store";
import { deviceFetch } from "@/lib/device/use-device";
import type { ServerDevice } from "@/lib/device/use-device";
import { methodLabel } from "@/lib/sales";
import type { Sale } from "@/lib/sales";

type Props = { sale: Sale; open: boolean; onClose: () => void; onVoided: (sale: Sale) => void };

type Destination =
  | { kind: "loading" }
  | { kind: "own" }
  | { kind: "device"; device: DeviceRecord; name: string; shortages: string[] }
  | { kind: "blocked" };

/** Efectivo que sale de la caja que recibe la devolución, por método: pago menos vuelto. */
function cashOut(sale: Sale): Map<string, { amount: bigint; currency: string }> {
  const totals = new Map<string, { amount: bigint; currency: string }>();
  for (const payment of sale.payments) {
    if (!isCashMethod(payment.method)) continue;
    const sign = payment.kind === "sale_payment" ? 1n : payment.kind === "change" ? -1n : 0n;
    const current = totals.get(payment.method) ?? { amount: 0n, currency: payment.currency };
    totals.set(payment.method, { ...current, amount: current.amount + sign * toCents(payment.amount) });
  }
  return totals;
}

async function findDestination(sale: Sale): Promise<Destination> {
  const own = await getCashSession(sale.cash_session_id);
  if (own.status === "open") return { kind: "own" };
  const device = await getDevice();
  if (!device) return { kind: "blocked" };
  try {
    const server = await deviceFetch<ServerDevice>(device, "/devices/current");
    if (!server.open_cash_session) return { kind: "blocked" };
    const rows = reconcile(await getCashSession(server.open_cash_session.id, device));
    const shortages = [...cashOut(sale)].flatMap(([method, out]) => {
      const row = rows.find((item) => item.method === method);
      return row && out.amount > toCents(row.expected) ? [`${methodLabel(method)} (disponible ${formatMethodAmount(row.expected, out.currency)})`] : [];
    });
    return { kind: "device", device, name: server.name, shortages };
  } catch {
    return { kind: "blocked" };
  }
}

export function VoidSaleDialog({ sale, open, onClose, onVoided }: Props) {
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [destination, setDestination] = useState<Destination>({ kind: "loading" });
  const valid = reason.trim().length >= 5;

  useEffect(() => {
    if (!open) return;
    setDestination({ kind: "loading" });
    findDestination(sale)
      .then(setDestination)
      .catch(() => setDestination({ kind: "blocked" }));
  }, [open, sale]);

  async function submit() {
    setSaving(true);
    setError(null);
    try {
      const options = { method: "POST" as const, body: { reason: reason.trim() } };
      const path = `/sales/${sale.id}/void`;
      onVoided(destination.kind === "device" ? await deviceFetch<Sale>(destination.device, path, options) : await apiFetch<Sale>(path, options));
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
          Se devuelve: {received.map((payment) => `${methodLabel(payment.method)} ${formatUsd(payment.amount)}`).join(", ")}
          {given.length > 0 && `; vuelve el vuelto entregado: ${given.map((payment) => `${methodLabel(payment.method)} ${formatUsd(payment.amount)}`).join(", ")}`}.
        </p>
        {destination.kind === "loading" && <p className="text-ink-muted">Buscando la caja que recibe la devolución…</p>}
        {destination.kind === "own" && <p>La devolución se registra en la caja de la venta, que sigue abierta.</p>}
        {destination.kind === "device" && (
          <Alert variant="info">
            La caja de la venta ya está cerrada y su cierre no cambia: la devolución se registra en la caja abierta de este equipo ({destination.name}).
          </Alert>
        )}
        {destination.kind === "device" && destination.shortages.length > 0 && (
          <Alert variant="warning">
            Esa caja no tiene efectivo suficiente en {destination.shortages.join(", ")}. Se puede anular igual: el esperado quedará negativo.
          </Alert>
        )}
        {destination.kind === "blocked" && (
          <Alert variant="warning">
            La caja de esta venta ya está cerrada. Para anularla, hazlo desde un equipo de mostrador registrado con la caja abierta (ábrela en Caja si hace falta).
          </Alert>
        )}
        <TextAreaField
          label="Motivo"
          maxLength={500}
          value={reason}
          hint="Obligatorio, al menos 5 caracteres. Queda en la auditoría."
          onChange={(event) => setReason(event.target.value)}
        />
        {error && <Alert variant="danger">{error}</Alert>}
        <Button
          variant="danger"
          loading={saving}
          disabled={!valid || destination.kind === "loading" || destination.kind === "blocked"}
          onClick={() => void submit()}
        >
          Anular venta
        </Button>
      </div>
    </Dialog>
  );
}
