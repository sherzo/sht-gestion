"use client";

// Un conteo físico (RF-12, RN-19; FR-025, FR-025a, FR-026). El Almacén anota a ciegas: la
// pantalla (y el servidor) no le muestran el stock del sistema ni las diferencias. El
// Admin revisa las diferencias, lo devuelve para recontar o lo aplica.
import { formatDateTime, formatQuantity, parseDecimalInput } from "@sht/shared";
import { ArrowLeft, Check, CheckCheck, RotateCcw, XCircle } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";

import { AppShell } from "@/components/app-shell";
import { RequireAuth } from "@/components/require-auth";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { DecimalInput } from "@/components/ui/decimal-input";
import { Dialog } from "@/components/ui/dialog";
import { TextAreaField } from "@/components/ui/field";
import { ApiError, apiFetch } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/use-auth";
import { COUNT_STATUS_LABELS, isReviewable, scopeLabel } from "@/lib/stock-counts";
import type { ApplyResult, CountDetail, CountLine } from "@/lib/stock-counts";

function display(value: string | null | undefined, decimals: number): string {
  return value === null || value === undefined ? "—" : formatQuantity(value, decimals);
}

function LineEditor({ countId, line, editable, onSaved }: { countId: string; line: CountLine; editable: boolean; onSaved: (line: CountLine) => void }) {
  const decimals = line.product.unit.decimals;
  const [value, setValue] = useState(line.counted_quantity ? line.counted_quantity.replace(".", ",") : "");
  const [error, setError] = useState<string | undefined>();
  const [saving, setSaving] = useState(false);
  const parsed = parseDecimalInput(value, decimals);
  const dirty = parsed !== null && parsed !== line.counted_quantity;

  async function save(event: FormEvent) {
    event.preventDefault();
    if (parsed === null) return;
    setSaving(true);
    setError(undefined);
    try {
      onSaved(await apiFetch<CountLine>(`/stock-counts/${countId}/lines/${line.id}`, { method: "PUT", body: { counted_quantity: parsed } }));
    } catch (caught) {
      setError(caught instanceof ApiError ? (caught.fields.counted_quantity ?? caught.message) : "No se pudo guardar");
    } finally {
      setSaving(false);
    }
  }

  return (
    <li className="flex flex-col gap-2 rounded-xl border border-line bg-surface p-3 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        <p className="text-sm text-ink-muted">{line.product.sku}</p>
        <p className="font-medium">{line.product.name}</p>
        {line.counted_at && (
          <p className="text-sm text-ink-muted">
            Anotado {formatDateTime(line.counted_at)} · {line.counted_by?.full_name}
          </p>
        )}
      </div>
      {editable ? (
        <form onSubmit={save} className="flex items-end gap-2" noValidate>
          <div className="w-36">
            <DecimalInput label={`Contado (${line.product.unit.code})`} decimals={decimals} value={value} error={error} onChange={setValue} />
          </div>
          <Button type="submit" variant={dirty ? "primary" : "secondary"} loading={saving} disabled={!dirty} aria-label={`Guardar ${line.product.sku}`}>
            <Check aria-hidden className="size-4" />
          </Button>
        </form>
      ) : (
        <p className="tabular-nums">
          Contado: <strong>{display(line.counted_quantity, decimals)}</strong> {line.product.unit.code}
        </p>
      )}
    </li>
  );
}

function ReviewTable({ count }: { count: CountDetail }) {
  if (!isReviewable(count)) return null;
  return (
    <div className="overflow-hidden rounded-xl border border-line bg-surface">
      <table className="w-full text-left">
        <caption className="sr-only">Diferencias del conteo</caption>
        <thead className="bg-neutral-100 text-sm text-ink-muted">
          <tr>
            <th scope="col" className="px-3 py-2 font-medium">
              Producto
            </th>
            <th scope="col" className="px-3 py-2 text-right font-medium">
              Sistema al anotar
            </th>
            <th scope="col" className="px-3 py-2 text-right font-medium">
              Contado
            </th>
            <th scope="col" className="px-3 py-2 text-right font-medium">
              Diferencia
            </th>
          </tr>
        </thead>
        <tbody>
          {count.lines.map((line) => {
            const decimals = line.product.unit.decimals;
            const difference = line.difference ?? null;
            const tone = !difference || Number(difference) === 0 ? "" : difference.startsWith("-") ? "text-danger" : "text-success";
            return (
              <tr key={line.id} className="border-t border-line align-top">
                <td className="px-3 py-2">
                  <span className="block text-sm text-ink-muted">{line.product.sku}</span>
                  {line.product.name}
                </td>
                <td className="px-3 py-2 text-right tabular-nums">{display(line.expected_quantity, decimals)}</td>
                <td className="px-3 py-2 text-right tabular-nums">{display(line.counted_quantity, decimals)}</td>
                <td className={`px-3 py-2 text-right font-semibold tabular-nums ${tone}`}>
                  {difference === null ? "Sin contar" : `${difference.startsWith("-") || Number(difference) === 0 ? "" : "+"}${display(difference, decimals)}`}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function CountDetailView({ id }: { id: string }) {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [count, setCount] = useState<CountDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [applying, setApplying] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [cancelReason, setCancelReason] = useState("");
  const [result, setResult] = useState<ApplyResult | null>(null);

  const load = useCallback(async () => {
    try {
      setCount(await apiFetch<CountDetail>(`/stock-counts/${id}`));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No se pudo cargar el conteo");
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  async function act(path: string, body: unknown, message: string) {
    setBusy(true);
    setError(null);
    try {
      setCount(await apiFetch<CountDetail>(`/stock-counts/${id}/${path}`, { method: "POST", body }));
      setNotice(message);
      return true;
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No se pudo completar la operación");
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function apply() {
    if (!count) return;
    setBusy(true);
    setError(null);
    try {
      const applied = await apiFetch<ApplyResult>(`/stock-counts/${id}/apply`, { method: "POST", body: { acknowledge_uncounted: true } });
      setResult(applied);
      setCount(applied.count);
      setNotice(`Conteo aplicado: se generaron ${applied.adjustments} ajuste(s) por conteo físico.`);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No se pudo aplicar el conteo");
    } finally {
      setBusy(false);
      setApplying(false);
    }
  }

  if (!count) return error ? <Alert variant="danger">{error}</Alert> : <p className="text-ink-muted">Cargando…</p>;

  const open = count.status === "open";
  const inReview = count.status === "ready_for_review";
  const uncounted = count.lines_total - count.lines_counted;
  const canCancel = open || (inReview && isAdmin);

  function replaceLine(line: CountLine) {
    setCount((current) =>
      current
        ? ({
            ...current,
            lines: current.lines.map((item) => (item.id === line.id ? line : item)),
            lines_counted: current.lines.filter((item) => (item.id === line.id ? line : item).counted_quantity !== null).length,
          } as CountDetail)
        : current,
    );
  }

  return (
    <>
      <div className="mb-4">
        <h1 className="text-2xl font-bold">Conteo: {scopeLabel(count.scope)}</h1>
        <p className="text-ink-muted">
          {COUNT_STATUS_LABELS[count.status]} · {count.lines_counted} de {count.lines_total} anotados · abierto el {formatDateTime(count.started_at)} por{" "}
          {count.started_by?.full_name}
        </p>
        {count.notes && <p className="mt-1">{count.notes}</p>}
        {count.cancel_reason && <p className="mt-1 text-danger">Cancelado: {count.cancel_reason}</p>}
      </div>
      <div className="mb-4 flex flex-col gap-2">
        {notice && <Alert variant="success">{notice}</Alert>}
        {error && <Alert variant="danger">{error}</Alert>}
        {result && result.negative_products.length > 0 && (
          <Alert variant="warning">
            Quedaron con stock negativo por salidas posteriores a la anotación: {result.negative_products.map((item) => item.sku).join(", ")}.
          </Alert>
        )}
        {!isAdmin && inReview && <Alert variant="info">El conteo está listo para revisión. El administrador lo aplicará o lo devolverá para recontar.</Alert>}
      </div>

      {isAdmin && (inReview || count.status === "applied") ? (
        <div className="flex flex-col gap-3">
          {isReviewable(count) && (
            <p>
              <strong>{count.lines_with_difference}</strong> producto(s) con diferencia
              {uncounted > 0 && (
                <>
                  {" "}
                  · <strong>{uncounted}</strong> sin contar
                </>
              )}
            </p>
          )}
          <ReviewTable count={count} />
        </div>
      ) : (
        <ul className="flex flex-col gap-2">
          {count.lines.map((line) => (
            <LineEditor key={line.id} countId={count.id} line={line} editable={open} onSaved={replaceLine} />
          ))}
        </ul>
      )}

      <div className="mt-6 flex flex-wrap gap-2">
        {open && (
          <Button onClick={() => act("ready", undefined, "El conteo quedó listo para revisión del administrador.")} loading={busy}>
            <CheckCheck aria-hidden className="size-4" /> Listo para revisión
          </Button>
        )}
        {isAdmin && (open || inReview) && (
          <Button variant="accent" onClick={() => setApplying(true)}>
            Aplicar conteo
          </Button>
        )}
        {isAdmin && inReview && (
          <Button variant="secondary" loading={busy} onClick={() => act("reopen", undefined, "El conteo volvió a abierto para recontar.")}>
            <RotateCcw aria-hidden className="size-4" /> Devolver para recontar
          </Button>
        )}
        {canCancel && (
          <Button variant="secondary" onClick={() => setCancelling(true)}>
            <XCircle aria-hidden className="size-4" /> Cancelar conteo
          </Button>
        )}
      </div>

      <Dialog open={applying} title="Aplicar conteo" onClose={() => setApplying(false)}>
        <p>
          Cada producto con diferencia recibirá un ajuste con motivo «conteo físico». Esta acción no se puede deshacer; un error se corrige
          con un ajuste nuevo.
        </p>
        {uncounted > 0 && <Alert variant="warning">Quedan {uncounted} producto(s) sin contar: no se ajustarán.</Alert>}
        {isReviewable(count) && count.status === "open" && <p className="text-sm text-ink-muted">El conteo todavía está abierto.</p>}
        <div className="flex flex-wrap gap-2">
          <Button variant="accent" loading={busy} onClick={apply}>
            Aplicar
          </Button>
          <Button variant="secondary" onClick={() => setApplying(false)}>
            Volver
          </Button>
        </div>
      </Dialog>
      <Dialog open={cancelling} title="Cancelar conteo" onClose={() => setCancelling(false)}>
        <form
          className="flex flex-col gap-4"
          noValidate
          onSubmit={async (event) => {
            event.preventDefault();
            if (await act("cancel", { reason: cancelReason }, "Conteo cancelado. No se generó ningún movimiento.")) {
              setCancelling(false);
              setCancelReason("");
            }
          }}
        >
          <p>No se generará ningún movimiento y los productos quedarán libres para otro conteo.</p>
          <TextAreaField label="Motivo" required maxLength={500} value={cancelReason} onChange={(event) => setCancelReason(event.target.value)} />
          <div className="flex flex-wrap gap-2">
            <Button type="submit" variant="danger" loading={busy} disabled={!cancelReason.trim()}>
              Cancelar conteo
            </Button>
            <Button variant="secondary" onClick={() => setCancelling(false)}>
              Volver
            </Button>
          </div>
        </form>
      </Dialog>
    </>
  );
}

function CountPage() {
  const id = useSearchParams().get("id");
  return (
    <AppShell>
      <Link href="/inventario/conteos/" className="mb-3 inline-flex min-h-11 items-center gap-2 text-primary">
        <ArrowLeft aria-hidden className="size-5" /> Conteos
      </Link>
      {id ? <CountDetailView key={id} id={id} /> : <Alert variant="danger">Falta el conteo.</Alert>}
    </AppShell>
  );
}

export default function StockCountPage() {
  return (
    <RequireAuth roles={["admin", "warehouse"]}>
      <Suspense fallback={null}>
        <CountPage />
      </Suspense>
    </RequireAuth>
  );
}
