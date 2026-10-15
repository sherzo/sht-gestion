// Venta en curso en el mostrador (RF-20 a RF-26; research R1, R4, R5 y R13 de la etapa
// 1.3). Todo lo que se muestra se calcula con `computeSale` de @sht/shared, la misma lógica
// que usa el servidor; al confirmar, la venta entra a la cola de salida con su número.
import { computeSale, MoneyError, parseDecimalInput, uuidv7, validateQuantity } from "@sht/shared";
import type { Currency, DiscountInput, EnteredUnit, SaleCalcResult } from "@sht/shared";

import type { Schemas } from "@/lib/api/client";
import { takeSequenceNumber } from "@/lib/device/device-store";
import type { DeviceRecord } from "@/lib/device/device-store";
import { enqueue, waitFor } from "@/lib/outbox/outbox";
import type { ProductAdmin, ProductSeller } from "@/lib/products";

export type SellableProduct = ProductAdmin | ProductSeller;
export type Sale = Schemas["SaleSeller"] | Schemas["SaleAdmin"];
export type ApplicableRate = Schemas["ApplicableRateOut"];
export type Customer = Schemas["CustomerOut"];

/** Los seis métodos de RF-24, fijos en esta etapa (data-model, `payment_method`). */
export const PAYMENT_METHODS = [
  { code: "cash_ves", name: "Efectivo Bs", currency: "VES", requiresReference: false },
  { code: "mobile_payment", name: "Pago móvil / transferencia", currency: "VES", requiresReference: true },
  { code: "pos_card", name: "Punto de venta", currency: "VES", requiresReference: true },
  { code: "cash_usd", name: "Efectivo USD", currency: "USD", requiresReference: false },
  { code: "zelle", name: "Zelle", currency: "USD", requiresReference: true },
  { code: "binance_usdt", name: "Binance USDT", currency: "USDT", requiresReference: true },
] as const satisfies readonly { code: string; name: string; currency: Currency; requiresReference: boolean }[];

export type PaymentMethodCode = (typeof PAYMENT_METHODS)[number]["code"];

export function paymentMethod(code: string) {
  return PAYMENT_METHODS.find((method) => method.code === code) ?? PAYMENT_METHODS[0];
}

export function methodLabel(code: string): string {
  return PAYMENT_METHODS.find((method) => method.code === code)?.name ?? code;
}

export type LineDiscount = DiscountInput & {
  authorizationId: string | null;
  /** Valor pedido, si el Admin aprobó uno menor (para mostrarlo). */
  requestedValue?: string;
};

export type SaleLine = {
  id: string;
  product: SellableProduct;
  text: string;
  enteredUnit: EnteredUnit;
  discount: LineDiscount | null;
};

export type MoneyEntry = {
  id: string;
  method: PaymentMethodCode;
  /** Monto como lo escribe el vendedor (`1.234,56`). */
  text: string;
  reference: string;
};

/** Monto de un pago o vuelto con punto decimal, o null si no es válido. */
export function entryAmount(entry: MoneyEntry): string | null {
  const amount = parseDecimalInput(entry.text, 2);
  return amount !== null && Number(amount) > 0 ? amount : null;
}

/** Primer problema de los pagos o vueltos que impide confirmar (RF-24). */
export function moneyProblem(entries: MoneyEntry[]): string | null {
  for (const entry of entries) {
    const method = paymentMethod(entry.method);
    if (entryAmount(entry) === null) return `${method.name}: escribe un monto mayor que cero`;
    if (method.requiresReference && !entry.reference.trim()) return `${method.name}: escribe la referencia`;
  }
  return null;
}

export type NewCustomer = { id: string; name: string; document_id: string; phone: string };
export type CustomerChoice = { kind: "existing"; customer: Customer } | { kind: "new"; data: NewCustomer };

export type SaleDraft = {
  saleId: string;
  rate: ApplicableRate;
  lines: SaleLine[];
  discount: LineDiscount | null;
  payments: MoneyEntry[];
  change: MoneyEntry[];
  customer: CustomerChoice | null;
};

export function newDraft(rate: ApplicableRate): SaleDraft {
  return { saleId: uuidv7(), rate, lines: [], discount: null, payments: [], change: [], customer: null };
}

export function isMeter(product: SellableProduct): boolean {
  return product.unit.decimals > 0;
}

export function newLine(product: SellableProduct): SaleLine {
  return { id: uuidv7(), product, text: "1", enteredUnit: isMeter(product) ? "m" : "unit", discount: null };
}

/** Cantidad de la línea en la unidad del producto, o el error para mostrar (RF-21). */
export function lineQuantity(line: SaleLine) {
  // `0,30` o `1.500` como los escribe el vendedor (RNF-07); la precisión la valida la unidad.
  const text = parseDecimalInput(line.text, 6);
  if (text === null) return { quantity: null, error: "Escribe una cantidad, por ejemplo 0,30" } as const;
  return validateQuantity(text, line.enteredUnit, line.product.unit.decimals);
}

function moneyInputs(entries: MoneyEntry[]) {
  // Los montos inválidos no cuentan: el panel muestra su error y no deja confirmar.
  return entries.flatMap((entry) => {
    const amount = entryAmount(entry);
    return amount ? [{ method: entry.method, currency: paymentMethod(entry.method).currency, amount }] : [];
  });
}

export type DraftCalc = { result: SaleCalcResult; error: null } | { result: null; error: string };

/** Totales, saldo y vuelto de la venta en curso con las reglas del servidor (ADR-0004). */
export function calculate(draft: SaleDraft, options: { withChange?: boolean } = {}): DraftCalc {
  const lines = draft.lines.map((line) => ({ line, quantity: lineQuantity(line) }));
  const invalid = lines.find(({ quantity }) => quantity.error !== null);
  if (invalid) return { result: null, error: `${invalid.line.product.name}: ${invalid.quantity.error}` };
  try {
    const result = computeSale({
      rate: draft.rate.rate,
      lines: lines.map(({ line, quantity }) => ({
        id: line.id,
        unit_price_usd: line.product.sale_price_usd ?? "0",
        quantity: quantity.quantity ?? "0",
        discount: line.discount ? { type: line.discount.type, value: line.discount.value } : null,
      })),
      discount: draft.discount ? { type: draft.discount.type, value: draft.discount.value } : null,
      payments: moneyInputs(draft.payments),
      change: options.withChange === false ? [] : moneyInputs(draft.change),
    });
    return { result, error: null };
  } catch (error) {
    if (error instanceof MoneyError) return { result: null, error: error.message };
    throw error;
  }
}

/** Suma de cantidades de un producto en la venta, para la advertencia de stock (RN-10). */
export function quantityOf(draft: SaleDraft, productId: string): number {
  return draft.lines
    .filter((line) => line.product.id === productId)
    .reduce((total, line) => total + Number(lineQuantity(line).quantity ?? 0), 0);
}

function customerPayload(choice: CustomerChoice | null) {
  if (!choice) return { customer: null, customer_id: null };
  if (choice.kind === "existing") return { customer: null, customer_id: choice.customer.id };
  return {
    customer: {
      id: choice.data.id,
      name: choice.data.name.trim(),
      document_id: choice.data.document_id.trim() || null,
      phone: choice.data.phone.trim() || null,
    },
    customer_id: null,
  };
}

function moneyPayload(entries: MoneyEntry[]) {
  return entries.map((entry) => ({ method: entry.method, amount: entryAmount(entry), reference: entry.reference.trim() || null }));
}

function discountPayload(discount: LineDiscount | null) {
  return discount ? { type: discount.type, value: discount.value, authorization_id: discount.authorizationId } : null;
}

export type ConfirmOutcome =
  | { status: "sent"; sale: Sale & { alerts_created?: string[]; warnings?: string[] } }
  | { status: "pending"; number: string }
  | { status: "rejected"; message: string };

/** Numera la venta, la guarda en la cola de salida y espera la respuesta del servidor. */
export async function confirmSale(
  draft: SaleDraft,
  context: { device: DeviceRecord; cashSessionId: string; sellerId: string },
): Promise<ConfirmOutcome> {
  const calc = calculate(draft);
  if (!calc.result) return { status: "rejected", message: calc.error };
  const sequence = await takeSequenceNumber();
  const number = `${context.device.series}-${String(sequence).padStart(6, "0")}`;
  const payload = {
    id: draft.saleId,
    sequence_number: sequence,
    cash_session_id: context.cashSessionId,
    seller_id: context.sellerId,
    occurred_at: new Date().toISOString(),
    exchange_rate: draft.rate.rate,
    exchange_rate_date: draft.rate.business_date,
    ...customerPayload(draft.customer),
    items: draft.lines.map((line) => ({
      id: line.id,
      product_id: line.product.id,
      quantity: lineQuantity(line).quantity,
      entered_unit: line.enteredUnit,
      unit_price_usd: line.product.sale_price_usd,
      discount: discountPayload(line.discount),
    })),
    discount: discountPayload(draft.discount),
    payments: moneyPayload(draft.payments),
    change: moneyPayload(draft.change),
    device_total_usd: calc.result.total_usd,
  };
  const id = await enqueue("sale.create", payload);
  const record = await waitFor(id);
  if (!record) return { status: "pending", number };
  if (record.status === "rejected") return { status: "rejected", message: record.error?.message ?? "La venta fue rechazada" };
  return { status: "sent", sale: record.result as Extract<ConfirmOutcome, { status: "sent" }>["sale"] };
}
