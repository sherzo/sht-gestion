"use client";

// Caja del equipo (FR-001 a FR-008; RF-18, RF-29, RF-30, RN-16): el Admin registra el equipo
// de mostrador en este navegador y el Vendedor abre la caja con su fondo inicial. Si no hay
// tasa BCV de hoy se avisa con la fecha de la última; sin ninguna tasa no se puede abrir.
// Egresos, cierre y cuadre llegan en la etapa 1.4.
import { formatDate, formatDateTime, formatRate, parseDecimalInput, todayInCaracas, uuidv7 } from "@sht/shared";
import { ShoppingBag } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { AppShell } from "@/components/app-shell";
import { RequireAuth } from "@/components/require-auth";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { DecimalInput } from "@/components/ui/decimal-input";
import { TextField } from "@/components/ui/field";
import { ApiError, apiFetch } from "@/lib/api/client";
import type { Schemas } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/use-auth";
import { clearDevice, saveDevice } from "@/lib/device/device-store";
import { useCounterDevice } from "@/lib/device/use-device";
import { enqueue, waitFor } from "@/lib/outbox/outbox";

type Registered = Schemas["DeviceRegistered"];
type ApplicableRate = Schemas["ApplicableRateOut"];

function RegisterDevice({ onDone }: { onDone: () => void }) {
  const [name, setName] = useState("Mostrador principal");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const device = await apiFetch<Registered>("/devices", { method: "POST", body: { name } });
      await saveDevice({ id: device.id, name: device.name, series: device.series, token: device.token, nextSequence: 1 });
      onDone();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No se pudo registrar el equipo");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="flex max-w-md flex-col gap-3 rounded-xl border border-line bg-surface p-4" noValidate>
      <p>
        Registra este navegador como equipo de mostrador. Recibirá una serie para numerar sus ventas (por ejemplo, <strong>A-000001</strong>).
      </p>
      {error && <Alert variant="danger">{error}</Alert>}
      <TextField label="Nombre del equipo" value={name} maxLength={60} onChange={(event) => setName(event.target.value)} />
      <Button type="submit" loading={saving} disabled={!name.trim()}>
        Registrar este equipo
      </Button>
    </form>
  );
}

function OpenCashSession({ onDone }: { onDone: () => void }) {
  const [rate, setRate] = useState<ApplicableRate | null | undefined>(undefined);
  const [floatVes, setFloatVes] = useState("");
  const [floatUsd, setFloatUsd] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const today = todayInCaracas();

  useEffect(() => {
    apiFetch<ApplicableRate>("/exchange-rates/applicable", { query: { date: today } })
      .then(setRate)
      .catch((caught) => setRate(caught instanceof ApiError && caught.status === 404 ? null : undefined));
  }, [today]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const ves = floatVes.trim() ? parseDecimalInput(floatVes, 2) : "0";
    const usd = floatUsd.trim() ? parseDecimalInput(floatUsd, 2) : "0";
    if (ves === null || usd === null) return;
    setSaving(true);
    setError(null);
    const id = await enqueue("cash_session.open", { id: uuidv7(), opening_float_ves: ves, opening_float_usd: usd });
    const result = await waitFor(id);
    setSaving(false);
    if (result?.status === "rejected") setError(result.error?.message ?? "No se pudo abrir la caja");
    else if (result === null) setError("La apertura quedó pendiente de envío: se enviará al volver la conexión.");
    else onDone();
  }

  return (
    <form onSubmit={submit} className="flex max-w-md flex-col gap-3 rounded-xl border border-line bg-surface p-4" noValidate>
      <h2 className="text-lg font-semibold">Abrir caja</h2>
      {rate === null && <Alert variant="danger">No hay ninguna tasa BCV cargada: el administrador debe cargarla antes de abrir la caja.</Alert>}
      {rate && rate.business_date !== today && (
        <Alert variant="warning">
          No hay tasa BCV de hoy; se usará la del {formatDate(rate.business_date)} ({formatRate(rate.rate)} Bs por USD).
        </Alert>
      )}
      {rate && rate.business_date === today && <p className="text-ink-muted">Tasa BCV de hoy: {formatRate(rate.rate)} Bs por USD.</p>}
      {error && <Alert variant="danger">{error}</Alert>}
      <DecimalInput label="Fondo inicial en efectivo Bs" decimals={2} value={floatVes} placeholder="0,00" onChange={setFloatVes} />
      <DecimalInput label="Fondo inicial en efectivo USD" decimals={2} value={floatUsd} placeholder="0,00" onChange={setFloatUsd} />
      <Button type="submit" loading={saving} disabled={!rate}>
        Abrir caja
      </Button>
    </form>
  );
}

function CashContent() {
  const { user } = useAuth();
  const device = useCounterDevice();
  const isAdmin = user?.role === "admin";

  return (
    <AppShell>
      <h1 className="mb-4 text-2xl font-bold">Caja</h1>
      {device.status === "loading" && <p className="text-ink-muted">Cargando…</p>}
      {device.status === "unregistered" &&
        (isAdmin ? (
          <RegisterDevice onDone={() => void device.reload()} />
        ) : (
          <Alert variant="warning">Este equipo no está registrado para vender; pídeselo al administrador.</Alert>
        ))}
      {device.status === "revoked" && (
        <div className="flex max-w-md flex-col gap-3">
          <Alert variant="danger">Este equipo ({device.local.name}, serie {device.local.series}) fue revocado y ya no puede vender.</Alert>
          {isAdmin && (
            <Button
              variant="secondary"
              onClick={async () => {
                await clearDevice();
                await device.reload();
              }}
            >
              Borrar este equipo y registrarlo de nuevo
            </Button>
          )}
        </div>
      )}
      {device.status === "offline" && <Alert variant="warning">{device.message}</Alert>}
      {device.status === "ready" && (
        <div className="flex flex-col gap-4">
          <p>
            Equipo <strong>{device.server.name}</strong>, serie <strong>{device.server.series}</strong>.
          </p>
          {device.server.open_cash_session ? (
            <div className="flex max-w-md flex-col gap-3 rounded-xl border border-line bg-surface p-4">
              <p>
                Caja abierta por <strong>{device.server.open_cash_session.opened_by.full_name}</strong> desde el{" "}
                {formatDateTime(device.server.open_cash_session.opened_at)}.
              </p>
              <p className="text-sm text-ink-muted">El cierre y el cuadre de caja llegan en la próxima etapa.</p>
              <Link
                href="/vender/"
                className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-accent px-4 font-semibold text-on-accent hover:bg-accent-hover"
              >
                <ShoppingBag aria-hidden className="size-5" /> Ir a vender
              </Link>
            </div>
          ) : (
            <OpenCashSession onDone={() => void device.reload()} />
          )}
        </div>
      )}
    </AppShell>
  );
}

export default function CashPage() {
  return (
    <RequireAuth roles={["admin", "seller"]}>
      <CashContent />
    </RequireAuth>
  );
}
