// Casos compartidos del cuadre de caja (RF-31, FR-006, FR-007, SC-003): los mismos que
// ejecuta backend/tests/test_cash_math.py. Se corre con `pnpm test` (node --test).
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, test } from "node:test";

import {
  CashError,
  computeReconciliation,
  type CashMethodInfo,
  type ReconciliationInput,
  type ReconciliationRowResult,
} from "./cash.ts";

type Case = {
  name: string;
  input: ReconciliationInput;
  expected?: ReconciliationRowResult[];
  error?: string;
};

const cases = JSON.parse(
  readFileSync(new URL("../test-vectors/cash.json", import.meta.url), "utf-8"),
) as { methods: CashMethodInfo[]; reconciliations: Case[]; errors: Case[] };

describe("esperado y diferencia por método (RF-31/FR-006)", () => {
  for (const item of cases.reconciliations) {
    test(item.name, () => {
      assert.deepEqual(computeReconciliation(cases.methods, item.input), item.expected);
    });
  }
});

describe("errores del cuadre", () => {
  for (const item of cases.errors) {
    test(item.name, () => {
      assert.throws(
        () => computeReconciliation(cases.methods, item.input),
        (error: unknown) => error instanceof CashError && error.message === item.error,
      );
    });
  }
});
