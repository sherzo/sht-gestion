"use client";

// Pendientes del Admin (RN-19/FR-019b): salidas del Almacén por aprobar. Aprobar genera el
// movimiento con el stock de ese momento; rechazar exige un motivo que el Almacén verá.
import { formatDateTime, formatQuantity } from "@sht/shared";
import { Check, X } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";

import { AppShell } from "@/components/app-shell";
import { RequireAuth } from "@/components/require-auth";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import type { Column } from "@/components/ui/data-table";
import { Dialog } from "@/components/ui/dialog";
import { TextAreaField } from "@/components/ui/field";
import { ApiError, apiFetch } from "@/lib/api/client";
import type { Schemas } from "@/lib/api/client";
import { ADJUSTMENT_REASON_LABELS } from "@/lib/products";

type AdjustmentRequest = Schemas["AdjustmentRequestOut"];
type RequestPage = Schemas["AdjustmentRequestPage"];

function quantity(request: AdjustmentRequest, value: string): string {
  return `${formatQuantity(value, request.product.unit.decimals)} ${request.product.unit.code}`;
}

function AdjustmentRequests() {
  const [requests, setRequests] = useState<AdjustmentRequest[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [approving, setApproving] = useState<AdjustmentRequest | null>(null);
  const [rejecting, setRejecting] = useState<AdjustmentRequest | null>(null);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const page = await apiFetch<RequestPage>("/inventory/adjustment-requests", { query: { status: "pending", page_size: 100 } });
      setRequests(page.items);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No se pudieron cargar los pendientes");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function decide(request: AdjustmentRequest, action: "approve" | "reject", body?: unknown) {
    setBusy(true);
    setError(null);
    try {
      await apiFetch(`/inventory/adjustment-requests/${request.id}/${action}`, { method: "POST", body });
      setNotice(action === "approve" ? `Salida de ${request.product.sku} aprobada.` : `Salida de ${request.product.sku} rechazada.`);
      setApproving(null);
      setRejecting(null);
      setReason("");
      await load();
    } catch (caught) {
      if (caught instanceof ApiError && caught.code === "negative_stock") {
        setError(
          `No se puede aprobar: el stock de ${request.product.sku} ya no alcanza. Recházala con un motivo para que el Almacén registre la cantidad correcta.`,
        );
      } else {
        setError(caught instanceof ApiError ? caught.message : "No se pudo completar la operación");
      }
      setApproving(null);
    } finally {
      setBusy(false);
    }
  }

  function onReject(event: FormEvent) {
    event.preventDefault();
    if (rejecting && reason.trim()) void decide(rejecting, "reject", { reason });
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
      render: (request) => (
        <>
          <span className="text-danger">{quantity(request, request.quantity_delta)}</span>
          <span className="block text-sm text-ink-muted">Stock actual: {quantity(request, request.product.stock)}</span>
        </>
      ),
    },
    {
      key: "reason",
      header: "Motivo",
      render: (request) => (
        <>
          {ADJUSTMENT_REASON_LABELS[request.adjustment_reason]}
          {request.note && <span className="block text-sm text-ink-muted">{request.note}</span>}
        </>
      ),
    },
    {
      key: "who",
      header: "Solicitó",
      render: (request) => (
        <>
          {request.requested_by.full_name}
          <span className="block text-sm text-ink-muted">{formatDateTime(request.requested_at)}</span>
        </>
      ),
    },
    {
      key: "actions",
      header: "Decisión",
      render: (request) => (
        <span className="flex flex-wrap gap-2">
          <Button onClick={() => setApproving(request)}>
            <Check aria-hidden className="size-4" /> Aprobar
          </Button>
          <Button variant="secondary" onClick={() => setRejecting(request)}>
            <X aria-hidden className="size-4" /> Rechazar
          </Button>
        </span>
      ),
    },
  ];

  return (
    <section aria-labelledby="pendientes-ajustes" className="flex flex-col gap-3">
      <h2 id="pendientes-ajustes" className="text-xl font-semibold">
        Salidas de inventario por aprobar
      </h2>
      {notice && <Alert variant="success">{notice}</Alert>}
      {error && <Alert variant="danger">{error}</Alert>}
      {requests && (
        <DataTable caption="Salidas por aprobar" columns={columns} rows={requests} rowKey={(request) => request.id} emptyMessage="No hay salidas pendientes." />
      )}
      <Dialog open={approving !== null} title="Aprobar salida" onClose={() => setApproving(null)}>
        {approving && (
          <>
            <p>
              Se descontarán <strong>{quantity(approving, approving.quantity_delta.replace("-", ""))}</strong> de{" "}
              {approving.product.name} (stock actual: {quantity(approving, approving.product.stock)}).
            </p>
            <div className="flex flex-wrap gap-2">
              <Button loading={busy} onClick={() => decide(approving, "approve")}>
                Aprobar
              </Button>
              <Button variant="secondary" onClick={() => setApproving(null)}>
                Cancelar
              </Button>
            </div>
          </>
        )}
      </Dialog>
      <Dialog open={rejecting !== null} title="Rechazar salida" onClose={() => setRejecting(null)}>
        <form onSubmit={onReject} className="flex flex-col gap-4" noValidate>
          <TextAreaField
            label="Motivo del rechazo"
            required
            maxLength={500}
            hint="El Almacén verá este motivo en sus solicitudes."
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
          <div className="flex flex-wrap gap-2">
            <Button type="submit" variant="danger" loading={busy} disabled={!reason.trim()}>
              Rechazar
            </Button>
            <Button variant="secondary" onClick={() => setRejecting(null)}>
              Cancelar
            </Button>
          </div>
        </form>
      </Dialog>
    </section>
  );
}

function PendingContent() {
  return (
    <AppShell>
      <h1 className="mb-4 text-2xl font-bold">Pendientes</h1>
      <div className="flex flex-col gap-8">
        <AdjustmentRequests />
      </div>
    </AppShell>
  );
}

export default function PendingPage() {
  return (
    <RequireAuth roles={["admin"]}>
      <PendingContent />
    </RequireAuth>
  );
}
