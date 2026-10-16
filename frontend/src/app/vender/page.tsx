"use client";

// Pantalla de venta (RF-18, RF-20 a RF-28; FR-010 a FR-019, FR-030, FR-033 a FR-038): busca
// productos, arma las líneas por metro (m o cm) o unidad, muestra los totales en USD y Bs,
// cobra con uno o varios métodos y confirma. La venta entra a la cola de salida con su
// número de la serie del equipo, así que un corte de conexión no la pierde ni la duplica.
//
// Tasa (FR-014): cada venta toma la vigente al empezar; si cambia mientras se arma y aún
// no hay pagos, se pide actualizarla antes del primer pago; con pagos, la venta conserva
// la suya. Atajos en PC: F2 enfoca el buscador y F9 confirma.
import { formatDate, formatPercent, formatRate, formatUsd, todayInCaracas } from "@sht/shared";
import { Percent } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { RequireAuth } from "@/components/require-auth";
import { CustomerPicker } from "@/components/sales/customer-picker";
import { DiscountDialog } from "@/components/sales/discount-dialog";
import type { DiscountTarget } from "@/components/sales/discount-dialog";
import { PaymentsPanel } from "@/components/sales/payments-panel";
import { SaleLines } from "@/components/sales/sale-lines";
import { SaleProductSearch } from "@/components/sales/sale-product-search";
import { SaleTotals } from "@/components/sales/sale-totals";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { ApiError, apiFetch } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/use-auth";
import { useCounterDevice } from "@/lib/device/use-device";
import { calculate, confirmSale, moneyProblem, newDraft, newLine } from "@/lib/sales";
import type { ApplicableRate, LineDiscount, SaleDraft, SaleLine, SellableProduct } from "@/lib/sales";

const RATE_CHECK_MS = 5 * 60_000;

async function fetchRate(): Promise<ApplicableRate | null> {
  try {
    return await apiFetch<ApplicableRate>("/exchange-rates/applicable", { query: { date: todayInCaracas() } });
  } catch (caught) {
    if (caught instanceof ApiError && caught.status === 404) return null;
    throw caught;
  }
}

function sameRate(a: ApplicableRate, b: ApplicableRate): boolean {
  return a.rate === b.rate && a.business_date === b.business_date;
}

/** Una autorización vale solo para el monto que se autorizó: si cambia, se pide de nuevo. */
function withoutAuthorization(discount: LineDiscount | null): LineDiscount | null {
  return discount?.authorizationId ? { ...discount, authorizationId: null, requestedValue: undefined } : discount;
}

/** Cambio en una línea: si cambia su cantidad, su descuento y el del total pierden la autorización. */
function changeLine(draft: SaleDraft, line: SaleLine): SaleDraft {
  const previous = draft.lines.find((item) => item.id === line.id);
  const baseChanged = previous && (previous.text !== line.text || previous.enteredUnit !== line.enteredUnit);
  const updated = baseChanged ? { ...line, discount: withoutAuthorization(line.discount) } : line;
  return {
    ...draft,
    lines: draft.lines.map((item) => (item.id === line.id ? updated : item)),
    discount: baseChanged ? withoutAuthorization(draft.discount) : draft.discount,
  };
}

type Notice = { variant: "success" | "warning" | "danger" | "info"; text: string };

function SellContent() {
  const { user } = useAuth();
  const device = useCounterDevice();
  const [draft, setDraft] = useState<SaleDraft | null>(null);
  const [rateMissing, setRateMissing] = useState(false);
  const [newerRate, setNewerRate] = useState<ApplicableRate | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [saving, setSaving] = useState(false);
  const [discountTarget, setDiscountTarget] = useState<(DiscountTarget & { lineId: string | null }) | null>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const isAdmin = user?.role === "admin";

  const startSale = useCallback(async () => {
    try {
      const rate = await fetchRate();
      setRateMissing(rate === null);
      setDraft(rate ? newDraft(rate) : null);
      setNewerRate(null);
    } catch (caught) {
      setNotice({ variant: "danger", text: caught instanceof ApiError ? caught.message : "No se pudo consultar la tasa" });
    }
  }, []);

  useEffect(() => {
    void startSale();
  }, [startSale]);

  // La tasa se vuelve a consultar cada 5 minutos mientras hay una venta abierta (FR-014).
  // El temporizador depende solo de la tasa de la venta, no de cada cambio en sus líneas.
  const saleRate = draft?.rate ?? null;
  useEffect(() => {
    if (!saleRate) return;
    const timer = setInterval(() => {
      fetchRate()
        .then((rate) => setNewerRate(rate && !sameRate(rate, saleRate) ? rate : null))
        .catch(() => undefined);
    }, RATE_CHECK_MS);
    return () => clearInterval(timer);
  }, [saleRate]);

  const calc = useMemo(() => (draft ? calculate(draft) : null), [draft]);
  const results = useMemo(() => new Map((calc?.result?.lines ?? []).map((line) => [line.id, line])), [calc]);
  const rateLocked = Boolean(newerRate && draft && draft.payments.length === 0);
  const unauthorized =
    !isAdmin && draft && [draft.discount, ...draft.lines.map((line) => line.discount)].some((discount) => discount && !discount.authorizationId);
  const problem =
    !draft || draft.lines.length === 0
      ? "Agrega al menos un producto"
      : (calc?.error ??
        (unauthorized ? "Pide la autorización del administrador para los descuentos" : null) ??
        moneyProblem(draft.payments) ??
        moneyProblem(draft.change) ??
        (calc?.result && Number(calc.result.balance_usd) > 0 ? "Los pagos no cubren el total" : null));
  const canConfirm = !problem && !rateLocked && !saving && device.status === "ready";

  const confirm = useCallback(async () => {
    if (!draft || device.status !== "ready" || !device.server.open_cash_session || !user || !canConfirm) return;
    setSaving(true);
    setNotice(null);
    try {
      const outcome = await confirmSale(draft, { device: device.local, cashSessionId: device.server.open_cash_session.id, sellerId: user.id });
      if (outcome.status === "sent") {
        const warnings = outcome.sale.warnings?.includes("negative_stock") ? " Algún producto quedó con stock negativo: se avisó al administrador." : "";
        const review = outcome.sale.needs_review ? " La venta quedó marcada para revisión del administrador." : "";
        setNotice({ variant: warnings || review ? "warning" : "success", text: `Venta ${outcome.sale.number} registrada por ${formatUsd(outcome.sale.total_usd)} USD.${warnings}${review}` });
        await startSale();
      } else if (outcome.status === "pending") {
        setNotice({ variant: "warning", text: `Venta ${outcome.number} guardada en este equipo: se enviará al volver la conexión.` });
        await startSale();
      } else {
        setNotice({ variant: "danger", text: outcome.message });
      }
    } finally {
      setSaving(false);
      searchRef.current?.focus();
    }
  }, [draft, device, user, canConfirm, startSale]);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "F2") {
        event.preventDefault();
        searchRef.current?.focus();
      } else if (event.key === "F9") {
        event.preventDefault();
        void confirm();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [confirm]);

  function update(change: (current: SaleDraft) => SaleDraft) {
    setDraft((current) => (current ? change(current) : current));
  }

  if (device.status === "loading") return <AppShell>Cargando…</AppShell>;
  if (device.status !== "ready" || !device.server.open_cash_session) {
    return (
      <AppShell>
        <h1 className="mb-4 text-2xl font-bold">Vender</h1>
        <Alert variant="warning">
          {device.status === "ready" ? "La caja de este equipo no está abierta." : device.status === "offline" ? device.message : "Este equipo no está listo para vender."}{" "}
          <Link href="/caja/" className="font-semibold underline">
            Ir a Caja
          </Link>
        </Alert>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="text-2xl font-bold">Vender</h1>
        <p className="text-sm text-ink-muted">
          Equipo {device.server.name} · serie {device.server.series}
        </p>
      </div>
      <div className="mb-4 flex flex-col gap-2">
        {device.server.open_cash_session.opened_on_previous_day && (
          <Alert variant="warning">
            La caja está abierta desde el {formatDate(device.server.open_cash_session.business_date)}.{" "}
            <Link href="/caja/" className="font-semibold underline">
              Ciérrala en Caja
            </Link>{" "}
            cuando termines de contar.
          </Alert>
        )}
        {rateMissing && <Alert variant="danger">No hay ninguna tasa BCV cargada: el administrador debe cargarla antes de vender.</Alert>}
        {newerRate && draft && (
          <Alert variant={rateLocked ? "warning" : "info"}>
            Hay una tasa nueva: {formatRate(newerRate.rate)} del {formatDate(newerRate.business_date)}.{" "}
            {rateLocked ? (
              <Button
                variant="secondary"
                onClick={() => {
                  update((current) => ({ ...current, rate: newerRate }));
                  setNewerRate(null);
                }}
              >
                Actualizar tasa
              </Button>
            ) : (
              "Esta venta ya tiene pagos y conserva su tasa; la nueva aplica desde la próxima."
            )}
          </Alert>
        )}
        {notice && <Alert variant={notice.variant}>{notice.text}</Alert>}
      </div>
      {draft && (
        <div className="grid gap-4 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
          <div className="flex flex-col gap-4">
            <SaleProductSearch
              inputRef={searchRef}
              rate={draft.rate.rate}
              onSelect={(product: SellableProduct) =>
                update((current) => ({ ...current, lines: [...current.lines, newLine(product)], discount: withoutAuthorization(current.discount) }))
              }
            />
            <SaleLines
              draft={draft}
              results={results}
              onChange={(line) => update((current) => changeLine(current, line))}
              onRemove={(id) =>
                update((current) => ({ ...current, lines: current.lines.filter((item) => item.id !== id), discount: withoutAuthorization(current.discount) }))
              }
              onDiscount={(line) =>
                setDiscountTarget({
                  lineId: line.id,
                  title: `Descuento: ${line.product.name}`,
                  saleId: draft.saleId,
                  saleItemId: line.id,
                  productId: line.product.id,
                  base: results.get(line.id)?.line_subtotal_usd ?? "0.00",
                  current: line.discount,
                })
              }
            />
            <CustomerPicker value={draft.customer} onChange={(customer) => update((current) => ({ ...current, customer }))} />
          </div>
          <div className="flex flex-col gap-4">
            <SaleTotals result={calc?.result ?? null} rate={draft.rate} />
            {draft.lines.length > 0 && (
              <button
                type="button"
                className="inline-flex min-h-11 items-center gap-1 self-start rounded-lg px-3 font-medium text-primary hover:bg-neutral-100"
                onClick={() =>
                  setDiscountTarget({
                    lineId: null,
                    title: "Descuento sobre el total",
                    saleId: draft.saleId,
                    saleItemId: null,
                    productId: null,
                    base: calc?.result?.subtotal_usd ?? "0.00",
                    current: draft.discount,
                  })
                }
              >
                <Percent aria-hidden className="size-4" />
                {draft.discount
                  ? `Descuento sobre el total: ${draft.discount.type === "percent" ? formatPercent(draft.discount.value) : `${formatUsd(draft.discount.value)} USD`}${draft.discount.authorizationId || isAdmin ? "" : " (sin autorizar)"}`
                  : "Descuento sobre el total"}
              </button>
            )}
            <PaymentsPanel
              payments={draft.payments}
              change={draft.change}
              result={calc?.result ?? null}
              rate={draft.rate.rate}
              disabled={rateLocked}
              onPayments={(payments) => update((current) => ({ ...current, payments }))}
              onChange={(change) => update((current) => ({ ...current, change }))}
            />
            {problem && draft.lines.length > 0 && <p className="text-sm text-ink-muted">{problem}</p>}
            <Button variant="accent" className="min-h-14 text-lg" loading={saving} disabled={!canConfirm} onClick={() => void confirm()}>
              Confirmar venta (F9)
            </Button>
          </div>
        </div>
      )}
      <DiscountDialog
        target={discountTarget}
        isAdmin={isAdmin}
        device={device.local}
        onClose={() => setDiscountTarget(null)}
        onApply={(discount) => {
          const target = discountTarget;
          if (!target) return;
          update((current) =>
            target.lineId
              ? {
                  ...current,
                  lines: current.lines.map((line) => (line.id === target.lineId ? { ...line, discount } : line)),
                  discount: withoutAuthorization(current.discount),
                }
              : { ...current, discount },
          );
        }}
      />
    </AppShell>
  );
}

export default function SellPage() {
  return (
    <RequireAuth roles={["admin", "seller"]}>
      <SellContent />
    </RequireAuth>
  );
}
