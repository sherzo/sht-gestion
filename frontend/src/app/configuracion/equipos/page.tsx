"use client";

// Equipos de mostrador (FR-001 a FR-004; RN-11), solo Admin: lista con serie, quién lo
// registró y su caja abierta, y revocación. Un equipo se registra desde su propio
// navegador, en Caja. Una serie revocada no se vuelve a usar.
import { formatDateTime } from "@sht/shared";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { RequireAuth } from "@/components/require-auth";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import type { Column } from "@/components/ui/data-table";
import { Dialog } from "@/components/ui/dialog";
import { StatusChip } from "@/components/ui/status-chip";
import { ApiError, apiFetch } from "@/lib/api/client";
import type { Schemas } from "@/lib/api/client";

type Device = Schemas["DeviceOut"];

function DevicesContent() {
  const [devices, setDevices] = useState<Device[] | null>(null);
  const [revoking, setRevoking] = useState<Device | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      setDevices(await apiFetch<Device[]>("/devices"));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No se pudieron cargar los equipos");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function revoke() {
    if (!revoking) return;
    setSaving(true);
    setError(null);
    try {
      await apiFetch(`/devices/${revoking.id}/revoke`, { method: "POST" });
      setNotice(`Equipo ${revoking.name} (serie ${revoking.series}) revocado.`);
      setRevoking(null);
      void load();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No se pudo revocar el equipo");
    } finally {
      setSaving(false);
    }
  }

  const columns: Column<Device>[] = [
    { key: "series", header: "Serie", className: "font-semibold", render: (device) => device.series },
    { key: "name", header: "Equipo", render: (device) => device.name },
    {
      key: "registered",
      header: "Registrado",
      render: (device) => (
        <>
          {device.registered_by.full_name}
          <span className="block text-sm text-ink-muted">{formatDateTime(device.registered_at)}</span>
        </>
      ),
    },
    {
      key: "cash",
      header: "Caja",
      render: (device) =>
        device.open_cash_session ? (
          <>
            Abierta por {device.open_cash_session.opened_by.full_name}
            <span className="block text-sm text-ink-muted">{formatDateTime(device.open_cash_session.opened_at)}</span>
          </>
        ) : (
          "Cerrada"
        ),
    },
    {
      key: "status",
      header: "Estado",
      render: (device) =>
        device.revoked_at ? <StatusChip variant="revoked" /> : <StatusChip variant="active" />,
    },
    {
      key: "actions",
      header: "",
      render: (device) =>
        !device.revoked_at && (
          <Button variant="secondary" onClick={() => setRevoking(device)}>
            Revocar
          </Button>
        ),
    },
  ];

  return (
    <AppShell>
      <h1 className="text-2xl font-bold">Equipos de mostrador</h1>
      <p className="mb-4">
        Cada equipo se registra desde su propio navegador, en{" "}
        <Link href="/caja/" className="text-primary underline-offset-2 hover:underline">
          Caja
        </Link>
        .{" "}
        <Link href="/configuracion/categorias/" className="text-primary underline-offset-2 hover:underline">
          Volver a configuración
        </Link>
      </p>
      <div className="mb-4 flex flex-col gap-2">
        {notice && <Alert variant="success">{notice}</Alert>}
        {error && <Alert variant="danger">{error}</Alert>}
      </div>
      {devices && <DataTable caption="Equipos registrados" columns={columns} rows={devices} rowKey={(device) => device.id} emptyMessage="Todavía no hay equipos registrados." />}
      <Dialog open={revoking !== null} title="Revocar equipo" onClose={() => setRevoking(null)}>
        <div className="flex flex-col gap-4">
          <p>
            El equipo <strong>{revoking?.name}</strong> (serie {revoking?.series}) no podrá abrir caja ni vender. Las ventas que hizo antes de revocarlo y
            aún no envió se aceptarán. Para volver a usarlo hay que registrarlo de nuevo y recibirá otra serie.
          </p>
          <Button variant="danger" loading={saving} onClick={() => void revoke()}>
            Revocar equipo
          </Button>
        </div>
      </Dialog>
    </AppShell>
  );
}

export default function DevicesPage() {
  return (
    <RequireAuth roles={["admin"]}>
      <DevicesContent />
    </RequireAuth>
  );
}
