"use client";

// Estado de las salidas que pidió el Almacén (RN-19/FR-019b): pendientes, aprobadas,
// rechazadas con su motivo o retiradas. Una pendiente se puede retirar para registrar otra.
import { formatDateTime, formatQuantity } from "@sht/shared";
import { Undo2 } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { RequireAuth } from "@/components/require-auth";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import type { Column } from "@/components/ui/data-table";
import { SelectField } from "@/components/ui/field";
import { StatusChip } from "@/components/ui/status-chip";
import type { StatusChipVariant } from "@/components/ui/status-chip";
import { ApiError, apiFetch } from "@/lib/api/client";
import type { Schemas } from "@/lib/api/client";
import { ADJUSTMENT_REASON_LABELS } from "@/lib/products";

type AdjustmentRequest = Schemas["AdjustmentRequestOut"];
type RequestPage = Schemas["AdjustmentRequestPage"];

function MyRequestsContent() {
  const [status, setStatus] = useState("");
  const [requests, setRequests] = useState<AdjustmentRequest[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const page = await apiFetch<RequestPage>("/inventory/adjustment-requests", { query: { status, page_size: 100 } });
      setRequests(page.items);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No se pudieron cargar tus solicitudes");
    }
  }, [status]);

  useEffect(() => {
    void load();
  }, [load]);

  async function withdraw(request: AdjustmentRequest) {
    setBusy(request.id);
    setError(null);
    try {
      await apiFetch(`/inventory/adjustment-requests/${request.id}/withdraw`, { method: "POST" });
      await load();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No se pudo retirar la solicitud");
    } finally {
      setBusy(null);
    }
  }

  const columns: Column<AdjustmentRequest>[] = [
    {
      key: "product",
      header: "Producto",
      render: (request) => (
        <Link href={`/productos/ficha/?id=${request.product.id}`} className="text-primary underline-offset-2 hover:underline">
          <span className="block text-sm text-ink-muted">{request.product.sku}</span>
          {request.product.name}
        </Link>
      ),
    },
    {
      key: "quantity",
      header: "Salida",
      className: "tabular-nums",
      render: (request) => `${formatQuantity(request.quantity_delta, request.product.unit.decimals)} ${request.product.unit.code}`,
    },
    { key: "reason", header: "Motivo", render: (request) => ADJUSTMENT_REASON_LABELS[request.adjustment_reason] },
    { key: "date", header: "Fecha", render: (request) => formatDateTime(request.requested_at) },
    {
      key: "status",
      header: "Estado",
      render: (request) => (
        <span className="flex flex-col gap-1">
          <StatusChip variant={request.status as StatusChipVariant} />
          {request.rejection_reason && <span className="text-sm">Motivo: {request.rejection_reason}</span>}
          {request.decided_by && request.status !== "withdrawn" && (
            <span className="text-sm text-ink-muted">Por {request.decided_by.full_name}</span>
          )}
        </span>
      ),
    },
    {
      key: "actions",
      header: "Acciones",
      render: (request) =>
        request.status === "pending" ? (
          <Button variant="secondary" loading={busy === request.id} onClick={() => withdraw(request)}>
            <Undo2 aria-hidden className="size-4" /> Retirar
          </Button>
        ) : (
          <span className="text-ink-muted">—</span>
        ),
    },
  ];

  return (
    <AppShell>
      <h1 className="mb-4 text-2xl font-bold">Mis solicitudes</h1>
      <div className="mb-4 sm:max-w-xs">
        <SelectField
          label="Estado"
          value={status}
          onChange={(event) => setStatus(event.target.value)}
          options={[
            { value: "", label: "Todas" },
            { value: "pending", label: "Pendientes" },
            { value: "approved", label: "Aprobadas" },
            { value: "rejected", label: "Rechazadas" },
            { value: "withdrawn", label: "Retiradas" },
          ]}
        />
      </div>
      {error && (
        <div className="mb-4">
          <Alert variant="danger">{error}</Alert>
        </div>
      )}
      {requests && (
        <DataTable caption="Mis solicitudes" columns={columns} rows={requests} rowKey={(request) => request.id} emptyMessage="No tienes solicitudes con este estado." />
      )}
    </AppShell>
  );
}

export default function MyRequestsPage() {
  return (
    <RequireAuth roles={["warehouse"]}>
      <MyRequestsContent />
    </RequireAuth>
  );
}
