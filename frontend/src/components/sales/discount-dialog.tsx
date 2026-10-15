"use client";

// Descuento por ítem o sobre el total (RF-22, RN-07; FR-020 a FR-027): en monto USD o en
// porcentaje. El Admin lo aplica directamente; el Vendedor necesita al Admin, que escribe
// su PIN en este equipo o aprueba una solicitud desde su sesión (puede aprobar un valor
// menor). La autorización queda atada a la línea, el valor y el monto base: si cambian,
// hay que pedirla de nuevo.
import { discountAmount, formatPercent, formatUsd, MoneyError, parseDecimalInput } from "@sht/shared";
import { useEffect, useRef, useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { DecimalInput } from "@/components/ui/decimal-input";
import { Dialog } from "@/components/ui/dialog";
import { TextField } from "@/components/ui/field";
import { ApiError, apiFetch } from "@/lib/api/client";
import type { Schemas } from "@/lib/api/client";
import type { DeviceRecord } from "@/lib/device/device-store";
import { deviceFetch } from "@/lib/device/use-device";
import type { LineDiscount } from "@/lib/sales";

type Authorization = Schemas["DiscountAuthorizationOut"];

export type DiscountTarget = {
  title: string;
  saleId: string;
  saleItemId: string | null;
  productId: string | null;
  /** Monto al que se aplica: subtotal de la línea o neto de la venta. */
  base: string;
  current: LineDiscount | null;
};

type Props = {
  target: DiscountTarget | null;
  isAdmin: boolean;
  device: DeviceRecord;
  onApply: (discount: LineDiscount | null) => void;
  onClose: () => void;
};

const POLL_MS = 3000;

export function DiscountDialog({ target, isAdmin, device, onApply, onClose }: Props) {
  const [type, setType] = useState<"amount" | "percent">("percent");
  const [text, setText] = useState("");
  const [mode, setMode] = useState<"edit" | "pin" | "waiting">("edit");
  const [adminUsername, setAdminUsername] = useState("");
  const [pin, setPin] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [requestId, setRequestId] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!target) return;
    setType(target.current?.type ?? "percent");
    setText(target.current ? target.current.value.replace(".", ",") : "");
    setMode("edit");
    setError(null);
    setPin("");
    setRequestId(null);
  }, [target]);

  useEffect(() => () => {
    if (timer.current) clearInterval(timer.current);
  }, []);

  if (!target) return <Dialog open={false} title="" onClose={onClose}>{null}</Dialog>;

  const value = parseDecimalInput(text, 2);
  let preview: string | null = null;
  let previewError: string | null = null;
  if (value !== null) {
    try {
      preview = discountAmount({ type, value }, target.base);
    } catch (caught) {
      previewError = caught instanceof MoneyError ? caught.message : "El descuento no es válido";
    }
  }
  const ready = value !== null && preview !== null;

  function apply(authorization: Authorization | null) {
    if (!value) return;
    if (authorization && authorization.discount_value !== authorization.requested_value) {
      onApply({ type, value: authorization.discount_value, authorizationId: authorization.id, requestedValue: authorization.requested_value });
    } else {
      onApply({ type, value, authorizationId: authorization?.id ?? null });
    }
    onClose();
  }

  async function send(method: "pin" | "request") {
    if (!value || !target) return;
    setSaving(true);
    setError(null);
    try {
      const authorization = await deviceFetch<Authorization>(device, "/discount-authorizations", {
        method: "POST",
        body: {
          method,
          admin_username: method === "pin" ? adminUsername : null,
          pin: method === "pin" ? pin : null,
          sale_id: target.saleId,
          sale_item_id: target.saleItemId,
          product_id: target.productId,
          discount_type: type,
          discount_value: value,
          base_usd: target.base,
        },
      });
      if (authorization.status === "approved") {
        apply(authorization);
        return;
      }
      setRequestId(authorization.id);
      setMode("waiting");
      // El Vendedor ve la respuesta sin recargar: se consulta cada 3 s (FR-025, R8).
      timer.current = setInterval(async () => {
        try {
          const current = await apiFetch<Authorization>(`/discount-authorizations/${authorization.id}`);
          if (current.status === "approved") {
            if (timer.current) clearInterval(timer.current);
            apply(current);
          } else if (current.status === "rejected") {
            if (timer.current) clearInterval(timer.current);
            setMode("edit");
            setError(`El administrador rechazó el descuento${current.rejection_reason ? `: ${current.rejection_reason}` : "."}`);
          }
        } catch {
          // Sin conexión momentánea: se vuelve a intentar en la próxima consulta.
        }
      }, POLL_MS);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No se pudo pedir la autorización");
    } finally {
      setSaving(false);
      setPin("");
    }
  }

  return (
    <Dialog open title={target.title} onClose={onClose} dismissible={mode !== "waiting"}>
      <div className="flex flex-col gap-3">
        <p className="text-sm text-ink-muted">Se aplica sobre {formatUsd(target.base)} USD.</p>
        {mode !== "waiting" && (
          <>
            <div className="flex rounded-lg border border-line" role="group" aria-label="Tipo de descuento">
              {(["percent", "amount"] as const).map((option) => (
                <button
                  key={option}
                  type="button"
                  aria-pressed={type === option}
                  onClick={() => setType(option)}
                  className={`min-h-11 flex-1 font-medium first:rounded-l-lg last:rounded-r-lg ${type === option ? "bg-primary text-on-primary" : "hover:bg-neutral-100"}`}
                >
                  {option === "percent" ? "Porcentaje" : "Monto USD"}
                </button>
              ))}
            </div>
            <DecimalInput label={type === "percent" ? "Porcentaje" : "Monto en USD"} decimals={2} value={text} error={previewError ?? undefined} onChange={setText} />
            {preview && (
              <p className="tabular-nums">
                Descuento: {formatUsd(preview)} USD{type === "percent" && value ? ` (${formatPercent(value)})` : ""}
              </p>
            )}
          </>
        )}
        {error && <Alert variant="danger">{error}</Alert>}
        {mode === "edit" && (
          <div className="flex flex-wrap gap-2">
            {isAdmin ? (
              <Button disabled={!ready} onClick={() => apply(null)}>
                Aplicar descuento
              </Button>
            ) : (
              <>
                <Button disabled={!ready} onClick={() => setMode("pin")}>
                  Autorizar con PIN
                </Button>
                <Button variant="secondary" disabled={!ready} loading={saving} onClick={() => void send("request")}>
                  Pedir aprobación al administrador
                </Button>
              </>
            )}
            {target.current && (
              <Button
                variant="secondary"
                onClick={() => {
                  onApply(null);
                  onClose();
                }}
              >
                Quitar descuento
              </Button>
            )}
          </div>
        )}
        {mode === "pin" && (
          <form
            className="flex flex-col gap-3"
            onSubmit={(event) => {
              event.preventDefault();
              void send("pin");
            }}
          >
            <TextField label="Usuario del administrador" autoComplete="off" value={adminUsername} onChange={(event) => setAdminUsername(event.target.value)} />
            <TextField label="PIN" type="password" inputMode="numeric" autoComplete="off" value={pin} onChange={(event) => setPin(event.target.value)} />
            <div className="flex gap-2">
              <Button type="submit" loading={saving} disabled={!adminUsername.trim() || !pin}>
                Autorizar
              </Button>
              <Button variant="secondary" onClick={() => setMode("edit")}>
                Volver
              </Button>
            </div>
          </form>
        )}
        {mode === "waiting" && (
          <div className="flex flex-col gap-3">
            <Alert variant="info">Esperando la respuesta del administrador… Puede aprobarla desde Pendientes.</Alert>
            <Button
              variant="secondary"
              onClick={() => {
                if (timer.current) clearInterval(timer.current);
                setMode("edit");
                setRequestId(null);
              }}
            >
              Dejar de esperar
            </Button>
            {requestId && <p className="text-xs text-ink-muted">Solicitud {requestId.slice(-6)}</p>}
          </div>
        )}
      </div>
    </Dialog>
  );
}
