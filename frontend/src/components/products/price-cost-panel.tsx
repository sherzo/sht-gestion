"use client";

// Precio de venta, costo inicial y publicación (RF-01, RF-07, RN-09; FR-009, FR-011 a
// FR-013). Solo el Admin: el servidor rechaza a los demás roles y no les envía el costo.
import { formatCost, formatDateTime, formatUsd, parseDecimalInput } from "@sht/shared";
import { Globe, GlobeLock } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { DecimalInput } from "@/components/ui/decimal-input";
import { ApiError, apiFetch } from "@/lib/api/client";
import type { Schemas } from "@/lib/api/client";
import type { ProductAdmin } from "@/lib/products";

type Price = Schemas["PriceOut"];

type PanelProps = { product: ProductAdmin; onChanged: (product: ProductAdmin) => void };

function useAction() {
  const [error, setError] = useState<string | null>(null);
  const [fieldError, setFieldError] = useState<string | undefined>();
  const [busy, setBusy] = useState(false);

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    setFieldError(undefined);
    try {
      await action();
    } catch (caught) {
      if (caught instanceof ApiError) {
        setError(caught.message);
        setFieldError(Object.values(caught.fields)[0]);
      } else {
        setError("Ocurrió un error inesperado");
      }
    } finally {
      setBusy(false);
    }
  }
  return { error, fieldError, busy, run };
}

function PriceSection({ product, onChanged }: PanelProps) {
  const [value, setValue] = useState("");
  const [history, setHistory] = useState<Price[]>([]);
  const { error, fieldError, busy, run } = useAction();

  const loadHistory = useCallback(async () => {
    setHistory(await apiFetch<Price[]>(`/products/${product.id}/prices`));
  }, [product.id]);

  useEffect(() => {
    void loadHistory().catch(() => setHistory([]));
  }, [loadHistory]);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    const price = parseDecimalInput(value, 2);
    if (!price) return;
    void run(async () => {
      onChanged(await apiFetch<ProductAdmin>(`/products/${product.id}/price`, { method: "PUT", body: { sale_price_usd: price } }));
      setValue("");
      await loadHistory();
    });
  }

  return (
    <section aria-labelledby="precio" className="flex flex-col gap-3">
      <h3 id="precio" className="text-lg font-semibold">
        Precio de venta
      </h3>
      <p className="text-2xl font-bold tabular-nums">
        {product.sale_price_usd ? `${formatUsd(product.sale_price_usd)} USD` : <span className="text-ink-muted">Sin precio</span>}
      </p>
      <p className="text-sm text-ink-muted">En USD con IVA incluido. El precio en Bs se calcula con la tasa BCV del día al vender.</p>
      {error && <Alert variant="danger">{error}</Alert>}
      <form onSubmit={onSubmit} className="flex flex-wrap items-end gap-2" noValidate>
        <div className="min-w-48 flex-1">
          <DecimalInput label="Nuevo precio (USD)" decimals={2} value={value} error={fieldError} onChange={setValue} />
        </div>
        <Button type="submit" loading={busy} disabled={!parseDecimalInput(value, 2)}>
          Guardar precio
        </Button>
      </form>
      {history.length > 0 && (
        <div>
          <h4 className="mb-1 text-sm font-medium text-ink-muted">Historial</h4>
          <ul className="flex flex-col divide-y divide-line rounded-xl border border-line">
            {history.map((item) => (
              <li key={item.id} className="flex flex-wrap justify-between gap-2 px-3 py-2">
                <span className="font-medium tabular-nums">{formatUsd(item.price_usd)} USD</span>
                <span className="text-sm text-ink-muted">
                  {formatDateTime(item.valid_from)} · {item.set_by?.full_name ?? "—"}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

function CostSection({ product, onChanged }: PanelProps) {
  const [value, setValue] = useState("");
  const { error, fieldError, busy, run } = useAction();

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    const cost = parseDecimalInput(value, 6);
    if (cost === null) return;
    void run(async () => {
      onChanged(await apiFetch<ProductAdmin>(`/products/${product.id}/initial-cost`, { method: "PUT", body: { avg_cost_usd: cost } }));
      setValue("");
    });
  }

  return (
    <section aria-labelledby="costo" className="flex flex-col gap-3">
      <h3 id="costo" className="text-lg font-semibold">
        Costo
      </h3>
      <p className="text-2xl font-bold tabular-nums">
        {product.avg_cost_usd !== null ? `${formatCost(product.avg_cost_usd)} USD` : <span className="text-ink-muted">Sin costo</span>}
      </p>
      {product.cost_locked ? (
        <Alert variant="info">El producto ya tiene compras confirmadas: su costo lo actualizan las compras con el promedio ponderado.</Alert>
      ) : (
        <>
          <p className="text-sm text-ink-muted">
            Costo inicial, mientras el producto no tenga compras. Desde la primera compra lo calcula el sistema.
          </p>
          {error && <Alert variant="danger">{error}</Alert>}
          <form onSubmit={onSubmit} className="flex flex-wrap items-end gap-2" noValidate>
            <div className="min-w-48 flex-1">
              <DecimalInput label="Costo inicial (USD)" decimals={6} value={value} error={fieldError} onChange={setValue} />
            </div>
            <Button type="submit" variant="secondary" loading={busy} disabled={parseDecimalInput(value, 6) === null}>
              Guardar costo
            </Button>
          </form>
        </>
      )}
    </section>
  );
}

function PublicationSection({ product, onChanged }: PanelProps) {
  const { error, busy, run } = useAction();
  const reason = !product.is_active ? "Un producto inactivo no se publica." : !product.sale_price_usd ? "Fija un precio de venta para poder publicarlo." : null;

  function toggle() {
    void run(async () => {
      onChanged(
        await apiFetch<ProductAdmin>(`/products/${product.id}/publication`, { method: "PUT", body: { is_published: !product.is_published } }),
      );
    });
  }

  return (
    <section aria-labelledby="catalogo" className="flex flex-col gap-3">
      <h3 id="catalogo" className="text-lg font-semibold">
        Catálogo online
      </h3>
      <p>{product.is_published ? "El producto está publicado en el catálogo." : "El producto no está publicado."}</p>
      {error && <Alert variant="danger">{error}</Alert>}
      {!product.is_published && reason && <p className="text-sm text-ink-muted">{reason}</p>}
      <Button variant={product.is_published ? "secondary" : "primary"} loading={busy} disabled={!product.is_published && reason !== null} onClick={toggle} className="self-start">
        {product.is_published ? <GlobeLock aria-hidden className="size-4" /> : <Globe aria-hidden className="size-4" />}
        {product.is_published ? "Retirar del catálogo" : "Publicar en el catálogo"}
      </Button>
    </section>
  );
}

export function PriceCostPanel({ product, onChanged }: PanelProps) {
  return (
    <div className="grid gap-8 lg:grid-cols-2">
      <PriceSection product={product} onChanged={onChanged} />
      <div className="flex flex-col gap-8">
        <CostSection product={product} onChanged={onChanged} />
        <PublicationSection product={product} onChanged={onChanged} />
      </div>
    </div>
  );
}
