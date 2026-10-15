// Casos compartidos de dinero (ADR-0004, FR-040, SC-003): los mismos que ejecuta
// backend/tests/test_sale_math.py. Se corre con `pnpm test` (node --test, research R2).
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, test } from "node:test";

import {
  computeSale,
  enteredQuantity,
  MoneyError,
  suggestedVes,
  type EnteredUnit,
  type SaleCalcInput,
} from "./money.ts";

type QuantityCase = {
  name: string;
  input: string;
  entered_unit: EnteredUnit;
  decimals: number;
  expected?: string;
  error?: string;
};
type SuggestedCase = { name: string; balance_usd: string; rate: string; expected: string };
type SaleCase = { name: string; input: SaleCalcInput; expected?: unknown; error?: string };

const cases = JSON.parse(
  readFileSync(new URL("../test-vectors/money.json", import.meta.url), "utf-8"),
) as { quantities: QuantityCase[]; suggested_ves: SuggestedCase[]; sales: SaleCase[] };

function throwsWith(run: () => unknown, message: string): void {
  assert.throws(run, (error: unknown) => error instanceof MoneyError && error.message === message);
}

describe("cantidades por unidad y cm (RF-21/FR-011)", () => {
  for (const item of cases.quantities) {
    test(item.name, () => {
      const run = () => enteredQuantity(item.input, item.entered_unit, item.decimals);
      if (item.error) throwsWith(run, item.error);
      else assert.equal(run(), item.expected);
    });
  }
});

describe("monto en Bs sugerido (FR-036)", () => {
  for (const item of cases.suggested_ves) {
    test(item.name, () => assert.equal(suggestedVes(item.balance_usd, item.rate), item.expected));
  }
});

describe("venta (FR-013, FR-020, FR-021, FR-035 a FR-038)", () => {
  for (const item of cases.sales) {
    test(item.name, () => {
      const run = () => computeSale(item.input);
      if (item.error) throwsWith(run, item.error);
      else assert.deepEqual(run(), item.expected);
    });
  }
});
