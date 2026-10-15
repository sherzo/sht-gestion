// UUIDv7 del equipo (research R4): formato, versión, variante y orden por tiempo.
import assert from "node:assert/strict";
import { test } from "node:test";

import { uuidv7 } from "./uuid.ts";

const FORMAT = /^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

test("formato UUIDv7 con versión 7 y variante 10", () => {
  for (let i = 0; i < 1000; i++) assert.match(uuidv7(), FORMAT);
});

test("el prefijo de tiempo es la hora actual y no decrece", () => {
  const before = Date.now();
  const ids = Array.from({ length: 1000 }, () => uuidv7());
  const after = Date.now();
  const times = ids.map((id) => parseInt(id.replaceAll("-", "").slice(0, 12), 16));
  for (let i = 1; i < times.length; i++) assert.ok(times[i] >= times[i - 1]);
  assert.ok(times[0] >= before && times[times.length - 1] <= after);
  assert.equal(new Set(ids).size, ids.length);
});
