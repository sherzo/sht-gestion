"use client";

// Compra en borrador (RF-14 a RF-16, RN-20/FR-004 a FR-015, FR-029 a FR-031): proveedor,
// fecha, moneda, productos y gastos. "Guardar y calcular" envía el borrador entero y
// muestra lo que calculó el servidor (reparto de gastos y costo final, research R4).
// "Confirmar" sube el stock y fija el costo; desde ahí la compra no cambia (RN-14).
import { formatDate, formatRate, parseDecimalInput, todayInCaracas } from "@sht/shared";
import { ArrowLeft, CheckCircle2, Save, Trash2 } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { PurchaseCharges } from "@/components/purchases/purchase-charges";
import type { ChargeDraft } from "@/components/purchases/purchase-charges";
import { PurchaseLines } from "@/components/purchases/purchase-lines";
import type { LineDraft } from "@/components/purchases/purchase-lines";
import { PurchaseTotals } from "@/components/purchases/purchase-totals";
import { RequireAuth } from "@/components/require-auth";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { SelectField, TextAreaField, TextField } from "@/components/ui/field";
import { ApiError, apiFetch } from "@/lib/api/client";
import { CURRENCY_LABELS, costDecimals } from "@/lib/purchases";
import type { ApplicableRate, Currency, Purchase, PurchaseItem, Supplier, SupplierPage } from "@/lib/purchases";

type Header = {
  supplier_id: string;
  purchase_date: string;
  currency: Currency;
  supplier_invoice_number: string;
  notes: string;
};

type Warning = { code: string; message: string };

/** `"3.000000"` → `"3"`, `"30.50"` → `"30,5"`: para volver a editar un valor guardado. */
function toInput(value: string | null | undefined): string {
  if (!value) return "";
  const [integer, fraction = ""] = value.split(".");
  const trimmed = fraction.replace(/0+$/, "");
  return trimmed ? `${integer},${trimmed}` : integer;
}

function fromPurchase(purchase: Purchase): { header: Header; lines: LineDraft[]; charges: ChargeDraft[] } {
  return {
    header: {
      supplier_id: purchase.supplier.id,
      purchase_date: purchase.purchase_date,
      currency: purchase.currency as Currency,
      supplier_invoice_number: purchase.supplier_invoice_number ?? "",
      notes: purchase.notes ?? "",
    },
    lines: purchase.items.map((item) => ({
      key: item.id,
      product: item.product,
      quantity: toInput(item.quantity),
      cost: toInput(purchase.currency === "VES" ? item.unit_cost_ves : item.unit_cost_usd),
    })),
    charges: purchase.charges.map((charge) => ({
      key: charge.id,
      description: charge.description,
      charge_type: charge.charge_type as ChargeDraft["charge_type"],
      value: toInput(charge.charge_type === "percent" ? charge.percent : charge.amount),
      currency: (charge.currency as Currency | null) ?? "USD",
      charge_template_id: charge.charge_template_id ?? null,
    })),
  };
}

function PurchaseEditor({ id }: { id: string | null }) {
  const router = useRouter();
  const [purchase, setPurchase] = useState<Purchase | null>(null);
  const [header, setHeader] = useState<Header>({
    supplier_id: "",
    purchase_date: todayInCaracas(),
    currency: "USD",
    supplier_invoice_number: "",
    notes: "",
  });
  const [lines, setLines] = useState<LineDraft[]>([]);
  const [charges, setCharges] = useState<ChargeDraft[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [rate, setRate] = useState<ApplicableRate | null | undefined>(undefined);
  const [dirty, setDirty] = useState(false);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [warnings, setWarnings] = useState<Warning[]>([]);
  const [notice, setNotice] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [askConfirm, setAskConfirm] = useState(false);
  const [askDiscard, setAskDiscard] = useState(false);
  const [pendingCurrency, setPendingCurrency] = useState<Currency | null>(null);

  const load = useCallback(
    (data: Purchase) => {
      if (data.status !== "draft") {
        router.replace(`/compras/detalle/?id=${data.id}`);
        return;
      }
      const state = fromPurchase(data);
      setPurchase(data);
      setHeader(state.header);
      setLines(state.lines);
      setCharges(state.charges);
      setDirty(false);
    },
    [router],
  );

  useEffect(() => {
    apiFetch<SupplierPage>("/suppliers", { query: { is_active: true, page_size: 100 } })
      .then((page) => setSuppliers(page.items))
      .catch(() => setSuppliers([]));
    if (id) {
      apiFetch<Purchase>(`/purchases/${id}`)
        .then(load)
        .catch((caught) => setError(caught instanceof ApiError ? caught.message : "No se pudo cargar la compra"));
    }
  }, [id, load]);

  const needsRate = header.currency === "VES" || charges.some((charge) => charge.charge_type === "fixed" && charge.currency === "VES");
  useEffect(() => {
    if (!needsRate || !header.purchase_date) {
      setRate(undefined);
      return;
    }
    apiFetch<ApplicableRate>("/exchange-rates/applicable", { query: { date: header.purchase_date } })
      .then(setRate)
      .catch(() => setRate(null));
  }, [needsRate, header.purchase_date]);

  const computed = useMemo(() => new Map<string, PurchaseItem>((purchase?.items ?? []).map((item) => [item.product.id, item])), [purchase]);
  const supplierOptions = useMemo(() => {
    const list = [...suppliers];
    if (purchase && !list.some((supplier) => supplier.id === purchase.supplier.id)) {
      list.push({ ...purchase.supplier, phone: null, notes: null, is_active: false, updated_at: "" });
    }
    return list;
  }, [suppliers, purchase]);

  function edit<T>(setter: (value: T) => void) {
    return (value: T) => {
      setter(value);
      setDirty(true);
      setNotice(null);
    };
  }

  function buildBody() {
    const errors: Record<string, string> = {};
    const items = lines.map((line, index) => {
      const quantity = parseDecimalInput(line.quantity, line.product.unit.decimals);
      const cost = parseDecimalInput(line.cost, costDecimals(header.currency));
      if (quantity === null) errors[`items.${index}.quantity`] = "Escribe la cantidad";
      if (cost === null) errors[`items.${index}.unit_cost`] = "Escribe el costo unitario";
      return { product_id: line.product.id, quantity: quantity ?? "", unit_cost: cost ?? "" };
    });
    const chargeBody = charges.map((charge, index) => {
      const value = parseDecimalInput(charge.value, 2);
      if (value === null) errors[`charges.${index}`] = "Escribe el valor del gasto";
      return charge.charge_type === "percent"
        ? { description: charge.description, charge_type: "percent", percent: value ?? "", charge_template_id: charge.charge_template_id }
        : { description: charge.description, charge_type: "fixed", amount: value ?? "", currency: charge.currency, charge_template_id: charge.charge_template_id };
    });
    if (!header.supplier_id) errors.supplier_id = "Elige el proveedor";
    if (lines.length === 0) errors.items = "Agrega al menos un producto";
    return {
      errors,
      body: {
        supplier_id: header.supplier_id,
        purchase_date: header.purchase_date,
        currency: header.currency,
        supplier_invoice_number: header.supplier_invoice_number || null,
        notes: header.notes || null,
        items,
        charges: chargeBody,
        ...(purchase ? { updated_at: purchase.updated_at } : {}),
      },
    };
  }

  async function save(): Promise<Purchase | null> {
    const { errors, body } = buildBody();
    setFields(errors);
    setError(null);
    if (Object.keys(errors).length > 0) {
      setError("Revisa los datos marcados");
      return null;
    }
    setSaving(true);
    try {
      const saved = purchase
        ? await apiFetch<Purchase & { warnings: Warning[] }>(`/purchases/${purchase.id}`, { method: "PUT", body })
        : await apiFetch<Purchase & { warnings: Warning[] }>("/purchases", { method: "POST", body });
      setWarnings(saved.warnings ?? []);
      load(saved);
      setNotice("Borrador guardado y calculado.");
      if (!purchase) router.replace(`/compras/editar/?id=${saved.id}`);
      return saved;
    } catch (caught) {
      if (caught instanceof ApiError) {
        setError(caught.message);
        setFields(caught.fields);
      } else {
        setError("Ocurrió un error inesperado");
      }
      return null;
    } finally {
      setSaving(false);
    }
  }

  async function confirm() {
    if (!purchase) return;
    setConfirming(true);
    setError(null);
    try {
      await apiFetch(`/purchases/${purchase.id}/confirm`, { method: "POST", body: { updated_at: purchase.updated_at } });
      router.push(`/compras/detalle/?id=${purchase.id}&confirmada=1`);
    } catch (caught) {
      setAskConfirm(false);
      if (caught instanceof ApiError && caught.code === "stale_data" && caught.extra.purchase) {
        load(caught.extra.purchase as Purchase);
        setError("Otra persona cambió esta compra mientras la revisabas. Se cargó la versión actual: revísala y vuelve a confirmar.");
      } else {
        setError(caught instanceof ApiError ? caught.message : "No se pudo confirmar la compra");
      }
    } finally {
      setConfirming(false);
    }
  }

  async function discard() {
    if (!purchase) {
      router.push("/compras/");
      return;
    }
    try {
      await apiFetch(`/purchases/${purchase.id}`, { method: "DELETE" });
      router.push("/compras/");
    } catch (caught) {
      setAskDiscard(false);
      setError(caught instanceof ApiError ? caught.message : "No se pudo descartar el borrador");
    }
  }

  function changeCurrency(next: Currency) {
    if (next === header.currency) return;
    if (lines.some((line) => line.cost.trim())) {
      setPendingCurrency(next);
      return;
    }
    edit(setHeader)({ ...header, currency: next });
  }

  return (
    <>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">{purchase ? "Compra en borrador" : "Nueva compra"}</h1>
      </div>
      <div className="mb-4 flex flex-col gap-2">
        {notice && <Alert variant="success">{notice}</Alert>}
        {error && <Alert variant="danger">{error}</Alert>}
        {fields.items && <Alert variant="danger">{fields.items}</Alert>}
        {warnings.map((warning) => (
          <Alert key={warning.code} variant="warning">
            {warning.message}
          </Alert>
        ))}
      </div>
      <div className="flex flex-col gap-4">
        <section className="grid gap-3 rounded-xl border border-line bg-surface p-3 sm:grid-cols-2">
          <SelectField
            label="Proveedor"
            value={header.supplier_id}
            error={fields.supplier_id}
            onChange={(event) => edit(setHeader)({ ...header, supplier_id: event.target.value })}
            options={[
              { value: "", label: supplierOptions.length ? "Elige el proveedor…" : "No hay proveedores activos" },
              ...supplierOptions.map((s) => ({ value: s.id, label: s.is_active ? s.name : `${s.name} (inactivo)` })),
            ]}
          />
          <TextField
            label="Fecha de la factura"
            type="date"
            max={todayInCaracas()}
            value={header.purchase_date}
            error={fields.purchase_date}
            onChange={(event) => edit(setHeader)({ ...header, purchase_date: event.target.value })}
          />
          <SelectField
            label="Moneda de la factura"
            value={header.currency}
            onChange={(event) => changeCurrency(event.target.value as Currency)}
            options={[
              { value: "USD", label: CURRENCY_LABELS.USD },
              { value: "VES", label: CURRENCY_LABELS.VES },
            ]}
          />
          <TextField
            label="N.º de factura del proveedor (opcional)"
            maxLength={50}
            value={header.supplier_invoice_number}
            error={fields.supplier_invoice_number}
            onChange={(event) => edit(setHeader)({ ...header, supplier_invoice_number: event.target.value })}
          />
          {needsRate && (
            <div className="sm:col-span-2">
              {rate === null && <Alert variant="danger">No hay tasa BCV cargada para esta fecha ni días anteriores. El Admin debe cargarla en Tasa BCV.</Alert>}
              {rate && (
                <Alert variant={rate.business_date === header.purchase_date ? "info" : "warning"}>
                  Tasa BCV: {formatRate(rate.rate)} Bs/USD
                  {rate.business_date === header.purchase_date ? "" : `, del ${formatDate(rate.business_date)} (no hay tasa del día de la factura)`}.
                </Alert>
              )}
            </div>
          )}
          <TextAreaField
            className="sm:col-span-2"
            label="Notas (opcional)"
            maxLength={1000}
            rows={2}
            value={header.notes}
            onChange={(event) => edit(setHeader)({ ...header, notes: event.target.value })}
          />
        </section>
        <PurchaseLines lines={lines} currency={header.currency} computed={dirty ? new Map() : computed} fields={fields} onChange={edit(setLines)} />
        <PurchaseCharges charges={charges} computed={dirty ? [] : (purchase?.charges ?? [])} fields={fields} onChange={edit(setCharges)} />
        {purchase && !dirty && <PurchaseTotals purchase={purchase} />}
        {dirty && purchase && <p className="text-sm text-ink-muted">Hay cambios sin guardar: guarda para ver el reparto de gastos y el costo final.</p>}
        <div className="flex flex-wrap gap-3">
          <Button onClick={() => void save()} loading={saving}>
            <Save aria-hidden className="size-5" /> Guardar y calcular
          </Button>
          <Button variant="accent" disabled={!purchase || dirty} onClick={() => setAskConfirm(true)}>
            <CheckCircle2 aria-hidden className="size-5" /> Confirmar compra
          </Button>
          <Button variant="secondary" onClick={() => setAskDiscard(true)}>
            <Trash2 aria-hidden className="size-5" /> Descartar
          </Button>
        </div>
      </div>

      <Dialog open={askConfirm} title="Confirmar la compra" onClose={() => setAskConfirm(false)}>
        <div className="flex flex-col gap-4">
          <p>
            El stock de los productos sube y su costo se recalcula con el costo final. Después de confirmar, la compra <strong>no se puede cambiar</strong>: si
            tiene un error, solo el Admin puede anularla.
          </p>
          <Button variant="accent" loading={confirming} onClick={() => void confirm()}>
            Confirmar compra
          </Button>
        </div>
      </Dialog>
      <Dialog open={askDiscard} title="Descartar el borrador" onClose={() => setAskDiscard(false)}>
        <div className="flex flex-col gap-4">
          <p>Se borra este borrador. No cambia el stock ni el costo de ningún producto.</p>
          <Button variant="danger" onClick={() => void discard()}>
            Descartar borrador
          </Button>
        </div>
      </Dialog>
      <Dialog open={pendingCurrency !== null} title="Cambiar la moneda" onClose={() => setPendingCurrency(null)}>
        <div className="flex flex-col gap-4">
          <p>Los costos unitarios escritos se borran para que los escribas de nuevo en {pendingCurrency ? CURRENCY_LABELS[pendingCurrency] : ""}.</p>
          <Button
            onClick={() => {
              if (pendingCurrency) {
                edit(setHeader)({ ...header, currency: pendingCurrency });
                setLines(lines.map((line) => ({ ...line, cost: "" })));
              }
              setPendingCurrency(null);
            }}
          >
            Cambiar la moneda
          </Button>
        </div>
      </Dialog>
    </>
  );
}

function EditorPage() {
  const id = useSearchParams().get("id");
  return (
    <AppShell>
      <Link href="/compras/" className="mb-3 inline-flex min-h-11 items-center gap-2 text-primary">
        <ArrowLeft aria-hidden className="size-5" /> Compras
      </Link>
      <PurchaseEditor id={id} />
    </AppShell>
  );
}

export default function PurchaseEditorPage() {
  return (
    <RequireAuth roles={["admin", "warehouse"]}>
      <Suspense fallback={null}>
        <EditorPage />
      </Suspense>
    </RequireAuth>
  );
}
