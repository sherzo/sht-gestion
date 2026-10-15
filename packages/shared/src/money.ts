// Cálculo de la venta en el equipo (RF-21, RF-22, RF-23, RF-25; RN-02, RN-04, RN-06;
// ADR-0004; research R1 de la etapa 1.3). Es la misma lógica que
// `backend/app/domain/sale_math.py` y `domain/units.py`, y los dos ejecutan los casos de
// `packages/shared/test-vectors/money.json`. Decimales exactos con decimal.js y redondeo
// mitad hacia arriba; los montos entran y salen como cadenas con punto decimal.
// Solo sintaxis de TypeScript borrable (sin enum ni namespace): Node lo ejecuta en las
// pruebas sin compilar (research R2).
import DecimalJs from "decimal.js";

const Dec = DecimalJs.clone({ precision: 40, rounding: DecimalJs.ROUND_HALF_UP });
type Dec = InstanceType<typeof Dec>;

const ZERO = new Dec(0);
const HUNDRED = new Dec(100);
const MAX_ABS_QUANTITY = new Dec("1E12");
const MAX_AMOUNT = new Dec("1E12");
export const MAX_LINES = 100;
export const MAX_PAYMENTS = 10;
export const MAX_CHANGE = 5;

export type EnteredUnit = "m" | "cm" | "unit";
export type Currency = "VES" | "USD" | "USDT";

export type DiscountInput = { type: "amount" | "percent"; value: string };
export type LineInput = {
  id: string;
  unit_price_usd: string;
  quantity: string;
  discount: DiscountInput | null;
};
export type MoneyInput = { method: string; currency: Currency; amount: string };
export type SaleCalcInput = {
  rate: string;
  lines: LineInput[];
  discount: DiscountInput | null;
  payments: MoneyInput[];
  change: MoneyInput[];
};
export type LineResult = {
  id: string;
  line_subtotal_usd: string;
  item_discount_usd: string;
  allocated_sale_discount_usd: string;
  line_total_usd: string;
};
export type SaleCalcResult = {
  lines: LineResult[];
  subtotal_usd: string;
  discount_usd: string;
  total_usd: string;
  total_ves: string;
  payments_usd: string[];
  paid_usd: string;
  balance_usd: string;
  balance_ves: string;
  excess_usd: string;
  change_usd: string[];
  change_total_usd: string;
  overpaid_usd: string;
};

/** Error de validación con el mismo mensaje en español que el servidor. */
export class MoneyError extends Error {}

function parse(text: string, invalid: string): Dec {
  let value: Dec;
  try {
    value = new Dec(text.trim());
  } catch {
    throw new MoneyError(invalid);
  }
  if (!value.isFinite()) throw new MoneyError(invalid);
  return value;
}

const round2 = (value: Dec): Dec => value.toDecimalPlaces(2, Dec.ROUND_HALF_UP);
const str2 = (value: Dec): string => value.toFixed(2);
const max = (a: Dec, b: Dec): Dec => (a.greaterThan(b) ? a : b);
const sum = (values: Dec[]): Dec => values.reduce((acc, value) => acc.plus(value), ZERO);

/** USD que cubre un monto en Bs con la tasa de la venta (RN-06): 2 decimales. */
export function vesToUsd(amountVes: string, rate: string): string {
  return str2(round2(new Dec(amountVes).dividedBy(new Dec(rate))));
}

/** Bs de un monto en USD (RN-02): 2 decimales. */
export function usdToVes(amountUsd: string, rate: string): string {
  return str2(round2(new Dec(amountUsd).times(new Dec(rate))));
}

/** Monto en Bs que cubre exactamente un saldo en USD (FR-036). */
export function suggestedVes(balanceUsd: string, rate: string): string {
  return usdToVes(balanceUsd, rate);
}

/**
 * Cantidad de una línea tal como la escribe el vendedor (RF-21): en `cm` se convierte a
 * metros (`cm ÷ 100`, exacto) y luego se valida con los decimales de la unidad, sin
 * redondear. Devuelve la cantidad en la unidad del producto o lanza MoneyError con el
 * mismo mensaje que `domain/units.py`.
 */
export function enteredQuantity(text: string, enteredUnit: EnteredUnit, decimals: number): string {
  let value = parse(text, "La cantidad no es válida");
  if (enteredUnit === "cm") value = value.dividedBy(HUNDRED);
  if (value.abs().greaterThanOrEqualTo(MAX_ABS_QUANTITY)) {
    throw new MoneyError("La cantidad es demasiado grande");
  }
  if (!value.toDecimalPlaces(decimals).equals(value)) {
    throw new MoneyError(
      decimals === 0
        ? "Esta unidad solo admite cantidades enteras"
        : `Esta unidad admite como máximo ${decimals} decimales`,
    );
  }
  if (value.isZero()) throw new MoneyError("La cantidad no puede ser cero");
  if (value.isNegative()) throw new MoneyError("La cantidad no puede ser negativa");
  return value.toFixed(decimals);
}

/** Variante para formularios: el error como valor en lugar de excepción. */
export function validateQuantity(
  text: string,
  enteredUnit: EnteredUnit,
  decimals: number,
): { quantity: string; error: null } | { quantity: null; error: string } {
  try {
    return { quantity: enteredQuantity(text, enteredUnit, decimals), error: null };
  } catch (error) {
    if (error instanceof MoneyError) return { quantity: null, error: error.message };
    throw error;
  }
}

function positiveAmount(text: string): Dec {
  const value = parse(text, "El monto no es válido");
  if (value.lessThanOrEqualTo(0)) throw new MoneyError("El monto debe ser mayor que cero");
  if (value.greaterThanOrEqualTo(MAX_AMOUNT)) throw new MoneyError("El monto es demasiado grande");
  if (!value.toDecimalPlaces(2).equals(value)) throw new MoneyError("Admite como máximo 2 decimales");
  return value;
}

/** Descuento en USD sobre `base` (RF-22): el monto tal cual o la base por el porcentaje. */
export function discountAmount(discount: DiscountInput, base: string): string {
  return str2(discountOf(discount, new Dec(base)));
}

function discountOf(discount: DiscountInput, base: Dec): Dec {
  const value = parse(discount.value, "El descuento debe ser mayor que cero");
  if (value.lessThanOrEqualTo(0)) throw new MoneyError("El descuento debe ser mayor que cero");
  if (!round2(value).equals(value)) throw new MoneyError("El descuento admite como máximo 2 decimales");
  if (discount.type === "percent") {
    if (value.greaterThan(HUNDRED)) throw new MoneyError("El porcentaje no puede ser mayor que 100");
    return round2(base.times(value).dividedBy(HUNDRED));
  }
  if (discount.type !== "amount") throw new MoneyError("El tipo de descuento no es válido");
  const amount = round2(value);
  if (amount.greaterThan(base)) {
    throw new MoneyError("El descuento no puede ser mayor que el monto al que se aplica");
  }
  return amount;
}

/** Reparto del descuento total en proporción al neto; residuo a la línea de mayor neto. */
function allocateDiscount(nets: Dec[], discount: Dec): Dec[] {
  const base = sum(nets);
  if (discount.isZero() || base.isZero()) return nets.map(() => ZERO);
  const shares = nets.map((net) => round2(discount.times(net).dividedBy(base)));
  const residue = discount.minus(sum(shares));
  if (!residue.isZero()) {
    let largest = 0;
    nets.forEach((net, i) => {
      if (net.greaterThan(nets[largest])) largest = i;
    });
    shares[largest] = shares[largest].plus(residue);
  }
  return shares;
}

function amountUsd(money: MoneyInput, rate: Dec): Dec {
  const amount = positiveAmount(money.amount);
  return money.currency === "VES" ? round2(amount.dividedBy(rate)) : amount;
}

/**
 * Calcula la venta completa con las mismas reglas que el servidor (ADR-0004). Lanza
 * MoneyError con un mensaje en español si algo no es válido.
 */
export function computeSale(sale: SaleCalcInput): SaleCalcResult {
  if (sale.lines.length === 0) throw new MoneyError("La venta no tiene productos");
  if (sale.lines.length > MAX_LINES) throw new MoneyError(`Una venta admite como máximo ${MAX_LINES} productos`);
  if (sale.payments.length > MAX_PAYMENTS) throw new MoneyError(`Una venta admite como máximo ${MAX_PAYMENTS} pagos`);
  if (sale.change.length > MAX_CHANGE) throw new MoneyError(`Una venta admite como máximo ${MAX_CHANGE} vueltos`);
  const rate = new Dec(sale.rate);

  const subtotals = sale.lines.map((line) =>
    round2(new Dec(line.unit_price_usd).times(new Dec(line.quantity))),
  );
  const itemDiscounts = sale.lines.map((line, i) =>
    line.discount ? discountOf(line.discount, subtotals[i]) : ZERO,
  );
  const nets = subtotals.map((subtotal, i) => subtotal.minus(itemDiscounts[i]));
  const subtotal = sum(nets);
  const discount = sale.discount ? discountOf(sale.discount, subtotal) : ZERO;
  const allocated = allocateDiscount(nets, discount);
  const total = subtotal.minus(discount);

  const paymentsUsd = sale.payments.map((payment) => amountUsd(payment, rate));
  const paid = sum(paymentsUsd);
  const balance = max(total.minus(paid), ZERO);
  const excess = max(paid.minus(total), ZERO);
  const changeUsd = sale.change.map((change) => amountUsd(change, rate));
  const changeTotal = sum(changeUsd);
  if (changeTotal.greaterThan(excess)) throw new MoneyError("El vuelto no puede ser mayor que el excedente");

  return {
    lines: sale.lines.map((line, i) => ({
      id: line.id,
      line_subtotal_usd: str2(subtotals[i]),
      item_discount_usd: str2(itemDiscounts[i]),
      allocated_sale_discount_usd: str2(allocated[i]),
      line_total_usd: str2(nets[i].minus(allocated[i])),
    })),
    subtotal_usd: str2(subtotal),
    discount_usd: str2(discount),
    total_usd: str2(total),
    total_ves: str2(round2(total.times(rate))),
    payments_usd: paymentsUsd.map(str2),
    paid_usd: str2(paid),
    balance_usd: str2(balance),
    balance_ves: str2(round2(balance.times(rate))),
    excess_usd: str2(excess),
    change_usd: changeUsd.map(str2),
    change_total_usd: str2(changeTotal),
    overpaid_usd: str2(excess.minus(changeTotal)),
  };
}
