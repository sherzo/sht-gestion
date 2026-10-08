"use client";

// Consulta de la auditoría para el admin (RF-46/FR-025): filtros por usuario, tipo de
// acción y fechas (días de Caracas), más recientes primero.
import { AUDIT_ACTION_GROUPS, ROLE_LABELS, auditActionLabel, formatDateTime, formatTime } from "@sht/shared";
import type { Role } from "@sht/shared";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { RequireAuth } from "@/components/require-auth";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import type { Column } from "@/components/ui/data-table";
import { SelectField, TextField } from "@/components/ui/field";
import { ApiError, apiFetch } from "@/lib/api/client";
import type { Schemas } from "@/lib/api/client";

type Entry = Schemas["AuditEntry"];
type Page = Schemas["AuditPage"];
type Json = Record<string, unknown> | null | undefined;

const PAGE_SIZE = 50;

function roleLabel(value: unknown): string {
  return typeof value === "string" && value in ROLE_LABELS ? ROLE_LABELS[value as Role] : String(value);
}

/** Resumen legible de lo que cambió, sin mostrar JSON crudo. */
function summarize(entry: Entry): string {
  const before = entry.before as Json;
  const after = entry.after as Json;
  const details = entry.details as Json;
  switch (entry.action) {
    case "setup.admin_created":
    case "user.created":
      return `${after?.username ?? ""} · ${roleLabel(after?.role)}`;
    case "user.updated":
      return `Nombre: ${before?.full_name ?? ""} → ${after?.full_name ?? ""}`;
    case "user.role_changed":
      return `${roleLabel(before?.role)} → ${roleLabel(after?.role)}`;
    case "user.password_reset":
      return details?.source === "cli" ? "Por comando de soporte" : "Por un administrador";
    case "auth.login_failed":
      return `Usuario probado: ${details?.username ?? ""}`;
    case "auth.login_locked":
    case "auth.pin_locked":
      return typeof details?.locked_until === "string" ? `Bloqueado hasta las ${formatTime(details.locked_until)}` : "Bloqueado";
    case "auth.pin_set":
      return details?.first_time ? "Primera vez" : "Cambio";
    case "auth.pin_failed":
    case "auth.pin_verified":
      return details?.admin_username ? `Admin: ${details.admin_username}` : "";
    case "setup.failed":
      return "Código incorrecto";
    default:
      return entry.reason ?? "";
  }
}

function AuditContent() {
  const [users, setUsers] = useState<Schemas["UserSummary"][]>([]);
  const [filters, setFilters] = useState({ user_id: "", action: "", date_from: "", date_to: "" });
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    apiFetch<Schemas["UserSummary"][]>("/users")
      .then(setUsers)
      .catch(() => setUsers([]));
  }, []);

  // Solo se muestra la respuesta de la última consulta: una anterior más lenta se descarta.
  const latest = useRef(0);
  const load = useCallback(async () => {
    const request = ++latest.current;
    setLoading(true);
    setError(null);
    try {
      const result = await apiFetch<Page>("/audit-log", { query: { ...filters, page, page_size: PAGE_SIZE } });
      if (request === latest.current) setData(result);
    } catch (caught) {
      if (request === latest.current) {
        setError(caught instanceof ApiError ? caught.message : "No se pudo cargar la auditoría");
      }
    } finally {
      if (request === latest.current) setLoading(false);
    }
  }, [filters, page]);

  useEffect(() => {
    void load();
  }, [load]);

  function update(name: keyof typeof filters, value: string) {
    setFilters((current) => ({ ...current, [name]: value }));
    setPage(1);
  }

  const columns: Column<Entry>[] = [
    { key: "date", header: "Fecha", render: (entry) => <span className="tabular-nums">{formatDateTime(entry.occurred_at)}</span> },
    { key: "user", header: "Usuario", render: (entry) => entry.user?.full_name ?? <span className="text-ink-muted">Sistema o anónimo</span> },
    { key: "action", header: "Acción", render: (entry) => auditActionLabel(entry.action) },
    { key: "detail", header: "Detalle", render: (entry) => summarize(entry) || <span className="text-ink-muted">—</span> },
  ];

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;
  const actionOptions = [
    { value: "", label: "Todas" },
    ...AUDIT_ACTION_GROUPS.flatMap((group) => [
      { value: Object.keys(group.actions).join(","), label: `${group.label} (todas)` },
      ...Object.entries(group.actions).map(([value, label]) => ({ value, label: `  ${label}` })),
    ]),
  ];

  return (
    <AppShell>
      <h1 className="mb-4 text-2xl font-bold">Auditoría</h1>
      <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <SelectField
          label="Usuario"
          options={[{ value: "", label: "Todos" }, ...users.map((user) => ({ value: user.id, label: user.full_name }))]}
          value={filters.user_id}
          onChange={(e) => update("user_id", e.target.value)}
        />
        <SelectField label="Acción" options={actionOptions} value={filters.action} onChange={(e) => update("action", e.target.value)} />
        <TextField label="Desde" type="date" value={filters.date_from} onChange={(e) => update("date_from", e.target.value)} />
        <TextField label="Hasta" type="date" value={filters.date_to} onChange={(e) => update("date_to", e.target.value)} />
      </div>
      {error && (
        <div className="mb-4">
          <Alert variant="danger">{error}</Alert>
        </div>
      )}
      {data && (
        <>
          <p className="mb-2 text-sm text-ink-muted" aria-live="polite">
            {loading ? "Cargando…" : `${data.total} registro${data.total === 1 ? "" : "s"}`}
          </p>
          <DataTable caption="Registros de auditoría" columns={columns} rows={data.items} rowKey={(entry) => entry.id} emptyMessage="No hay registros con estos filtros." />
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

export default function AuditPage() {
  return (
    <RequireAuth roles={["admin"]}>
      <AuditContent />
    </RequireAuth>
  );
}
