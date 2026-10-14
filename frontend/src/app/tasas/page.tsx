"use client";

// Tasa BCV (RF-17, RN-15/FR-025 a FR-027), solo Admin: carga la tasa del día, la corrige
// con auditoría si se equivocó y consulta el histórico. Las compras confirmadas conservan
// la tasa con la que se registraron (RN-05).
import { formatDate, formatDateTime, formatRate, parseDecimalInput, todayInCaracas } from "@sht/shared";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";

import { AppShell } from "@/components/app-shell";
import { RequireAuth } from "@/components/require-auth";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import type { Column } from "@/components/ui/data-table";
import { DecimalInput } from "@/components/ui/decimal-input";
import { Dialog } from "@/components/ui/dialog";
import { TextField } from "@/components/ui/field";
import { ApiError, apiFetch } from "@/lib/api/client";
import type { Schemas } from "@/lib/api/client";

type Rate = Schemas["ExchangeRateOut"];
type RatePage = Schemas["ExchangeRatePage"];

const PAGE_SIZE = 30;

function RatesContent() {
  const [data, setData] = useState<RatePage | null>(null);
  const [page, setPage] = useState(1);
  const [date, setDate] = useState(todayInCaracas());
  const [value, setValue] = useState("");
  const [existing, setExisting] = useState<Rate | null>(null);
  const [confirmCorrection, setConfirmCorrection] = useState(false);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      setData(await apiFetch<RatePage>("/exchange-rates", { query: { page, page_size: PAGE_SIZE } }));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No se pudo cargar el histórico");
    }
  }, [page]);

  useEffect(() => {
    void load();
  }, [load]);

  // Si la fecha ya tiene tasa, el formulario pasa a corregirla (FR-026).
  useEffect(() => {
    setExisting(data?.items.find((rate) => rate.business_date === date) ?? null);
  }, [data, date]);

  async function submit(event?: FormEvent) {
    event?.preventDefault();
    setError(null);
    setFields({});
    const rate = parseDecimalInput(value, 8);
    if (rate === null) {
      setFields({ rate: "Escribe la tasa, por ejemplo 36,50" });
      return;
    }
    if (existing && !confirmCorrection) {
      setConfirmCorrection(true);
      return;
    }
    setSaving(true);
    try {
      if (existing) {
        await apiFetch(`/exchange-rates/${date}`, { method: "PUT", body: { rate } });
        setNotice(`Tasa del ${formatDate(date)} corregida a ${formatRate(rate)}.`);
      } else {
        await apiFetch("/exchange-rates", { method: "POST", body: { business_date: date, rate } });
        setNotice(`Tasa del ${formatDate(date)} cargada: ${formatRate(rate)}.`);
      }
      setValue("");
      setConfirmCorrection(false);
      void load();
    } catch (caught) {
      setConfirmCorrection(false);
      if (caught instanceof ApiError) {
        setError(caught.message);
        setFields(caught.fields);
      } else {
        setError("Ocurrió un error inesperado");
      }
    } finally {
      setSaving(false);
    }
  }

  const columns: Column<Rate>[] = [
    { key: "date", header: "Fecha", render: (rate) => <span className="tabular-nums">{formatDate(rate.business_date)}</span> },
    { key: "rate", header: "Tasa (Bs/USD)", className: "tabular-nums font-semibold", render: (rate) => formatRate(rate.rate) },
    {
      key: "who",
      header: "Cargó",
      render: (rate) => (
        <>
          {rate.created_by?.full_name ?? "—"}
          {rate.updated_at && (
            <span className="block text-sm text-ink-muted">
              Corregida por {rate.updated_by?.full_name ?? "—"}, {formatDateTime(rate.updated_at)}
            </span>
          )}
        </>
      ),
    },
  ];

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;
  const today = todayInCaracas();
  const hasToday = data?.items.some((rate) => rate.business_date === today);

  return (
    <AppShell>
      <h1 className="mb-4 text-2xl font-bold">Tasa BCV</h1>
      <div className="mb-4 flex flex-col gap-2">
        {data && !hasToday && page === 1 && <Alert variant="warning">Todavía no se cargó la tasa de hoy.</Alert>}
        {notice && <Alert variant="success">{notice}</Alert>}
        {error && <Alert variant="danger">{error}</Alert>}
      </div>
      <form onSubmit={submit} className="mb-6 grid gap-3 rounded-xl border border-line bg-surface p-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end" noValidate>
        <TextField label="Fecha" type="date" max={today} value={date} error={fields.business_date} onChange={(event) => setDate(event.target.value)} />
        <DecimalInput
          label="Tasa (Bs por USD)"
          decimals={8}
          value={value}
          error={fields.rate}
          hint={existing ? `Ya cargada: ${formatRate(existing.rate)}. Se corregirá.` : undefined}
          onChange={setValue}
        />
        <Button type="submit" loading={saving}>
          {existing ? "Corregir tasa" : "Cargar tasa"}
        </Button>
      </form>
      {data && (
        <>
          <DataTable caption="Histórico de tasas" columns={columns} rows={data.items} rowKey={(rate) => rate.id} emptyMessage="Todavía no hay tasas cargadas." />
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
      <Dialog open={confirmCorrection} title="Corregir la tasa" onClose={() => setConfirmCorrection(false)}>
        <div className="flex flex-col gap-4">
          <p>
            La tasa del {formatDate(date)} pasa de {existing ? formatRate(existing.rate) : "—"} a {formatRate(parseDecimalInput(value, 8) ?? "0")}. La corrección queda
            en la auditoría. Las compras ya confirmadas conservan su tasa; los borradores de esa fecha toman la nueva.
          </p>
          <Button loading={saving} onClick={() => void submit()}>
            Corregir tasa
          </Button>
        </div>
      </Dialog>
    </AppShell>
  );
}

export default function RatesPage() {
  return (
    <RequireAuth roles={["admin"]}>
      <RatesContent />
    </RequireAuth>
  );
}
