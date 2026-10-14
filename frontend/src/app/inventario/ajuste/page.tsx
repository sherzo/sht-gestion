"use client";

// Ajuste de inventario con motivo (RF-10/FR-019, RN-19): Admin y Almacén. Las salidas del
// Almacén quedan pendientes de aprobación del Admin y no cambian el stock hasta entonces.
import { formatQuantity, parseDecimalInput } from "@sht/shared";
import { ArrowDownCircle, ArrowUpCircle, X } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import type { FormEvent } from "react";

import { AppShell } from "@/components/app-shell";
import { ProductPicker } from "@/components/products/product-picker";
import { RequireAuth } from "@/components/require-auth";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { DecimalInput } from "@/components/ui/decimal-input";
import { SelectField, TextAreaField } from "@/components/ui/field";
import { ApiError, apiFetch } from "@/lib/api/client";
import type { Schemas } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/use-auth";
import { ADJUSTMENT_REASONS, quantityWithUnit } from "@/lib/products";
import type { Product } from "@/lib/products";

type Result = Schemas["AdjustmentResultOut"];
type Direction = "in" | "out";

function AdjustmentContent() {
  const { user } = useAuth();
  const productId = useSearchParams().get("producto");
  const [product, setProduct] = useState<Product | null>(null);
  const [direction, setDirection] = useState<Direction>("out");
  const [quantity, setQuantity] = useState("");
  const [reason, setReason] = useState("");
  const [note, setNote] = useState("");
  const [fields, setFields] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const isWarehouse = user?.role === "warehouse";

  useEffect(() => {
    if (!productId) return;
    apiFetch<Product>(`/products/${productId}`)
      .then(setProduct)
      .catch(() => setError("No se pudo cargar el producto"));
  }, [productId]);

  function reset() {
    setQuantity("");
    setReason("");
    setNote("");
    setFields({});
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!product) return;
    setError(null);
    setSuccess(null);
    const amount = parseDecimalInput(quantity, product.unit.decimals);
    const errors: Record<string, string> = {};
    if (amount === null || Number(amount) === 0 || amount.startsWith("-")) errors.quantity_delta = "Escribe una cantidad mayor que cero";
    if (!reason) errors.reason = "Elige el motivo";
    if (Object.keys(errors).length) {
      setFields(errors);
      return;
    }
    setSubmitting(true);
    try {
      const result = await apiFetch<Result>("/inventory/adjustments", {
        method: "POST",
        body: {
          product_id: product.id,
          quantity_delta: direction === "out" ? `-${amount}` : amount,
          reason,
          note: note.trim() || undefined,
        },
      });
      if (result.status === "pending") {
        setSuccess("Tu salida quedó pendiente de aprobación del administrador. El stock no cambia hasta que la apruebe.");
      } else if (result.movement) {
        setSuccess(`Ajuste registrado. Stock nuevo: ${formatQuantity(result.movement.balance_after, product.unit.decimals)} ${product.unit.code}.`);
        setProduct(await apiFetch<Product>(`/products/${product.id}`));
      }
      reset();
    } catch (caught) {
      if (caught instanceof ApiError) {
        setError(caught.message);
        setFields(caught.fields);
      } else {
        setError("Ocurrió un error inesperado");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AppShell>
      <h1 className="mb-4 text-2xl font-bold">Ajuste de inventario</h1>
      <div className="flex max-w-2xl flex-col gap-4">
        {success && <Alert variant="success">{success}</Alert>}
        {error && <Alert variant="danger">{error}</Alert>}
        {!product ? (
          <ProductPicker includeInactive onSelect={(selected) => setProduct(selected)} />
        ) : (
          <form onSubmit={onSubmit} className="flex flex-col gap-4 rounded-xl border border-line bg-surface p-4 sm:p-6" noValidate>
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm text-ink-muted">{product.sku}</p>
                <p className="font-semibold">
                  <Link href={`/productos/ficha/?id=${product.id}`} className="text-primary underline-offset-2 hover:underline">
                    {product.name}
                  </Link>
                </p>
                <p className="tabular-nums">Stock actual: {quantityWithUnit(product.stock, product.unit)}</p>
              </div>
              <Button variant="secondary" aria-label="Elegir otro producto" onClick={() => { setProduct(null); setSuccess(null); }}>
                <X aria-hidden className="size-4" /> Cambiar
              </Button>
            </div>
            <fieldset className="flex flex-col gap-2">
              <legend className="mb-1 text-sm font-medium">Tipo de ajuste</legend>
              <div className="grid gap-2 sm:grid-cols-2">
                {(
                  [
                    ["in", "Entrada (suma)", ArrowUpCircle],
                    ["out", "Salida (resta)", ArrowDownCircle],
                  ] as const
                ).map(([value, label, Icon]) => (
                  <label
                    key={value}
                    className={`flex min-h-11 cursor-pointer items-center gap-2 rounded-lg border px-3 ${
                      direction === value ? "border-accent bg-accent/10" : "border-line"
                    }`}
                  >
                    <input type="radio" name="direction" value={value} checked={direction === value} onChange={() => setDirection(value)} className="size-4" />
                    <Icon aria-hidden className="size-5" /> {label}
                  </label>
                ))}
              </div>
              {isWarehouse && direction === "out" && (
                <p className="text-sm text-ink-muted">Las salidas quedan pendientes hasta que el administrador las apruebe.</p>
              )}
            </fieldset>
            <DecimalInput
              label={`Cantidad (${product.unit.name})`}
              decimals={product.unit.decimals}
              value={quantity}
              error={fields.quantity_delta}
              hint={product.unit.decimals === 0 ? "Solo números enteros." : "Hasta 2 decimales (centímetros)."}
              onChange={setQuantity}
            />
            <SelectField
              label="Motivo"
              value={reason}
              error={fields.reason}
              onChange={(event) => setReason(event.target.value)}
              options={[{ value: "", label: "Elige el motivo" }, ...ADJUSTMENT_REASONS.map((item) => ({ value: item.value, label: item.label }))]}
            />
            <TextAreaField label="Nota (opcional)" maxLength={500} value={note} error={fields.note} onChange={(event) => setNote(event.target.value)} />
            <Button type="submit" loading={submitting} className="self-start">
              Registrar ajuste
            </Button>
          </form>
        )}
      </div>
    </AppShell>
  );
}

export default function AdjustmentPage() {
  return (
    <RequireAuth roles={["admin", "warehouse"]}>
      <Suspense fallback={null}>
        <AdjustmentContent />
      </Suspense>
    </RequireAuth>
  );
}
