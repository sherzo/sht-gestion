// Cuadre de la caja por método de pago en el equipo (RF-31; FR-006, FR-007; ADR-0004;
// research R1 de la etapa 1.4). Es la misma lógica que `backend/app/domain/cash_math.py`,
// y los dos ejecutan los casos de `packages/shared/test-vectors/cash.json`:
//
//   esperado = fondo (solo cash_ves y cash_usd) + cobrado − vuelto − devuelto
//              + vuelto recuperado − egresos no anulados
//
// No convierte monedas: cada método se cuadra en la suya (RN-04, RN-05). Los montos entran
// y salen como cadenas con punto decimal. Solo sintaxis de TypeScript borrable (research R2
// de la etapa 1.3).
import DecimalJs from "decimal.js";

const Dec = DecimalJs.clone({ precision: 40, rounding: DecimalJs.ROUND_HALF_UP });
type Dec = InstanceType<typeof Dec>;

const ZERO = new Dec(0);

/** Los dos métodos con fondo inicial al abrir la caja (RF-29). */
export const CASH_METHODS = ["cash_ves", "cash_usd"] as const;
export const CASH_MOVEMENT_KINDS = ["sale_payment", "change", "void_refund", "void_change"] as const;

export type CashMovementKind = (typeof CASH_MOVEMENT_KINDS)[number];
export type CashMethodInfo = { code: string; currency: string };
export type CashMovementInput = { method: string; currency: string; kind: string; amount: string };
export type CashOutflowInput = { method: string; amount: string; voided: boolean };
export type ReconciliationInput = {
  opening_float_ves: string;
  opening_float_usd: string;
  movements: CashMovementInput[];
  outflows: CashOutflowInput[];
  /** Contado por método; un método que falta se toma como 0,00. null: sin contado. */
  counted: Record<string, string> | null;
};
export type ReconciliationRowResult = {
  method: string;
  currency: string;
  opening: string;
  collected: string;
  change_given: string;
  refunded: string;
  change_recovered: string;
  outflows: string;
  expected: string;
  counted: string | null;
  difference: string | null;
};

export class CashError extends Error {}

const str2 = (value: Dec): string => (value.isZero() ? "0.00" : value.toFixed(2));

const unknownMethod = (code: string) => new CashError(`Método de pago desconocido: ${code}`);

function isKind(kind: string): kind is CashMovementKind {
  return (CASH_MOVEMENT_KINDS as readonly string[]).includes(kind);
}

/** Una fila por método, en el orden de `methods` (el del catálogo). */
export function computeReconciliation(
  methods: CashMethodInfo[],
  input: ReconciliationInput,
): ReconciliationRowResult[] {
  const currency = new Map(methods.map((method) => [method.code, method.currency]));
  const totals = new Map<string, Record<CashMovementKind, Dec>>();
  const outflowTotals = new Map<string, Dec>();
  for (const method of methods) {
    totals.set(method.code, { sale_payment: ZERO, change: ZERO, void_refund: ZERO, void_change: ZERO });
    outflowTotals.set(method.code, ZERO);
  }

  for (const movement of input.movements) {
    if (!isKind(movement.kind)) {
      throw new CashError(`Tipo de movimiento de caja desconocido: ${movement.kind}`);
    }
    const kinds = totals.get(movement.method);
    if (!kinds) throw unknownMethod(movement.method);
    if (movement.currency !== currency.get(movement.method)) {
      throw new CashError(
        `El movimiento en ${movement.method} debe estar en ${currency.get(movement.method)}`,
      );
    }
    kinds[movement.kind] = kinds[movement.kind].plus(movement.amount);
  }

  for (const outflow of input.outflows) {
    const total = outflowTotals.get(outflow.method);
    if (total === undefined) throw unknownMethod(outflow.method);
    if (!outflow.voided) outflowTotals.set(outflow.method, total.plus(outflow.amount));
  }

  const counted = input.counted;
  if (counted !== null) {
    for (const [code, amount] of Object.entries(counted)) {
      if (!currency.has(code)) throw unknownMethod(code);
      if (new Dec(amount).lessThan(0)) {
        throw new CashError("El monto contado no puede ser negativo");
      }
    }
  }

  const openings: Record<string, string> = {
    cash_ves: input.opening_float_ves,
    cash_usd: input.opening_float_usd,
  };
  return methods.map((method) => {
    const kinds = totals.get(method.code)!;
    const outflows = outflowTotals.get(method.code)!;
    const opening = new Dec(openings[method.code] ?? 0);
    const expected = opening
      .plus(kinds.sale_payment)
      .minus(kinds.change)
      .minus(kinds.void_refund)
      .plus(kinds.void_change)
      .minus(outflows);
    const rowCounted = counted === null ? null : new Dec(counted[method.code] ?? 0);
    return {
      method: method.code,
      currency: method.currency,
      opening: str2(opening),
      collected: str2(kinds.sale_payment),
      change_given: str2(kinds.change),
      refunded: str2(kinds.void_refund),
      change_recovered: str2(kinds.void_change),
      outflows: str2(outflows),
      expected: str2(expected),
      counted: rowCounted === null ? null : str2(rowCounted),
      difference: rowCounted === null ? null : str2(rowCounted.minus(expected)),
    };
  });
}
