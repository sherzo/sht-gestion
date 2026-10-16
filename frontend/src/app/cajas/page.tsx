"use client";

// Consulta de cajas del Admin (RF-31; FR-024; research R9 y R13 de la etapa 1.4): filtros
// por fechas de apertura, equipo, quién abrió o cerró, estado y diferencias. Las cajas con
// diferencias se resaltan y cada fila lleva a su detalle con el cuadre.
import { formatDate, formatDateTime, todayInCaracas } from "@sht/shared";
import { ChevronLeft, ChevronRight } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { RequireAuth } from "@/components/require-auth";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import type { Column } from "@/components/ui/data-table";
import { SelectField, TextField } from "@/components/ui/field";
import { StatusChip } from "@/components/ui/status-chip";
import { ApiError, apiFetch } from "@/lib/api/client";
import type { Schemas } from "@/lib/api/client";
import type { CashSessionSummary } from "@/lib/cash";

type CashPage = Schemas["CashSessionPage"];
type DeviceOut = Schemas["DeviceOut"];
type UserSummary = Schemas["UserSummary"];

const PAGE_SIZE = 50;
const STATUS_OPTIONS = [
  { value: "", label: "Todas" },
  { value: "open", label: "Abiertas" },
  { value: "closed", label: "Cerradas" },
];
const DIFFERENCE_OPTIONS = [
  { value: "", label: "Todas" },
  { value: "true", label: "Con diferencias" },
  { value: "false", label: "Sin diferencias" },
];

const EMPTY = { from: "", to: "", device_id: "", opened_by: "", closed_by: "", status: "", with_differences: "" };

function CashSessionsContent() {
  const today = todayInCaracas();
  const [filters, setFilters] = useState({ ...EMPTY, from: today, to: today });
  const [page, setPage] = useState(1);
  const [data, setData] = useState<CashPage | null>(null);
  const [devices, setDevices] = useState<DeviceOut[]>([]);
  const [users, setUsers] = useState<UserSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<DeviceOut[]>("/devices").then(setDevices).catch(() => setDevices([]));
    apiFetch<UserSummary[]>("/users").then(setUsers).catch(() => setUsers([]));
  }, []);

  const load = useCallback(async () => {
    try {
      setData(await apiFetch<CashPage>("/cash-sessions", { query: { ...filters, page, page_size: PAGE_SIZE } }));
      setError(null);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No se pudieron cargar las cajas");
    }
  }, [filters, page]);

  useEffect(() => {
    void load();
  }, [load]);

  function update(name: keyof typeof filters, value: string) {
    setFilters((current) => ({ ...current, [name]: value }));
    setPage(1);
  }

  const userOptions = [{ value: "", label: "Cualquiera" }, ...users.map((user) => ({ value: user.id, label: user.full_name }))];
  const columns: Column<CashSessionSummary>[] = [
    {
      key: "device",
      header: "Equipo",
      render: (session) => (
        <Link href={`/cajas/detalle/?id=${session.id}`} className="font-semibold text-primary underline-offset-2 hover:underline">
          {session.device.name} ({session.device.series})
        </Link>
      ),
    },
    {
      key: "opened",
      header: "Apertura",
      render: (session) => (
        <>
          <span className="block tabular-nums">{formatDateTime(session.opened_at)}</span>
          <span className="block text-sm text-ink-muted">{session.opened_by.full_name}</span>
        </>
      ),
    },
    {
      key: "closed",
      header: "Cierre",
      render: (session) =>
        session.closed_at ? (
          <>
            <span className="block tabular-nums">{formatDateTime(session.closed_at)}</span>
            <span className="block text-sm text-ink-muted">{session.closed_by?.full_name}</span>
          </>
        ) : (
          "—"
        ),
    },
    {
      key: "status",
      header: "Estado",
      render: (session) => (
        <span className="flex flex-wrap gap-1">
          {session.status === "open" ? <StatusChip variant="pending" label="Abierta" /> : <StatusChip variant="confirmed" label="Cerrada" />}
          {session.has_differences && <StatusChip variant="needs_review" label="Con diferencias" />}
          {session.closed_outside_device && <StatusChip variant="inactive" label="Cerrada fuera del equipo" />}
          {session.opened_on_previous_day && <StatusChip variant="low_stock" label={`Abierta desde el ${formatDate(session.business_date)}`} />}
        </span>
      ),
    },
  ];

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <AppShell>
      <h1 className="mb-4 text-2xl font-bold">Cajas</h1>
      {error && (
        <div className="mb-4">
          <Alert variant="danger">{error}</Alert>
        </div>
      )}
      <div className="mb-4 grid gap-3 sm:grid-cols-4">
        <TextField label="Abiertas desde" type="date" value={filters.from} max={today} onChange={(event) => update("from", event.target.value)} />
        <TextField label="Hasta" type="date" value={filters.to} max={today} onChange={(event) => update("to", event.target.value)} />
        <SelectField
          label="Equipo"
          value={filters.device_id}
          options={[{ value: "", label: "Todos" }, ...devices.map((device) => ({ value: device.id, label: `${device.name} (${device.series})` }))]}
          onChange={(event) => update("device_id", event.target.value)}
        />
        <SelectField label="Estado" value={filters.status} options={STATUS_OPTIONS} onChange={(event) => update("status", event.target.value)} />
        <SelectField label="Abrió" value={filters.opened_by} options={userOptions} onChange={(event) => update("opened_by", event.target.value)} />
        <SelectField label="Cerró" value={filters.closed_by} options={userOptions} onChange={(event) => update("closed_by", event.target.value)} />
        <SelectField
          label="Diferencias"
          value={filters.with_differences}
          options={DIFFERENCE_OPTIONS}
          onChange={(event) => update("with_differences", event.target.value)}
        />
      </div>
      {data && (
        <>
          <DataTable caption="Cajas" columns={columns} rows={data.items} rowKey={(session) => session.id} emptyMessage="No hay cajas con estos filtros." />
          {data.total > data.page_size && (
            <nav aria-label="Paginación" className="mt-4 flex items-center justify-between gap-3">
              <Button variant="secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>
                <ChevronLeft aria-hidden className="size-4" /> Anterior
              </Button>
              <span className="text-sm text-ink-muted">
                Página {page} de {totalPages}
              </span>
              <Button variant="secondary" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>
                Siguiente <ChevronRight aria-hidden className="size-4" />
              </Button>
            </nav>
          )}
        </>
      )}
    </AppShell>
  );
}

export default function CashSessionsPage() {
  return (
    <RequireAuth roles={["admin"]}>
      <CashSessionsContent />
    </RequireAuth>
  );
}
