// Totales de una compra calculados por el servidor (FR-007): mercancía, gastos y total en
// USD, y la mercancía en Bs si la compra es en bolívares, con la tasa usada y su fecha.
import { formatDate, formatRate, formatUsd, formatVes } from "@sht/shared";

import type { Purchase } from "@/lib/purchases";

export function PurchaseTotals({ purchase }: { purchase: Purchase }) {
  return (
    <dl className="grid gap-2 rounded-xl border border-line bg-surface p-3 text-sm sm:grid-cols-2">
      {purchase.exchange_rate && purchase.exchange_rate_date && (
        <div className="sm:col-span-2">
          <dt className="text-ink-muted">Tasa BCV</dt>
          <dd className="tabular-nums">
            {formatRate(purchase.exchange_rate)} Bs/USD, del {formatDate(purchase.exchange_rate_date)}
          </dd>
        </div>
      )}
      {purchase.merchandise_total_ves && (
        <div>
          <dt className="text-ink-muted">Mercancía en Bs</dt>
          <dd className="tabular-nums">{formatVes(purchase.merchandise_total_ves)}</dd>
        </div>
      )}
      <div>
        <dt className="text-ink-muted">Mercancía</dt>
        <dd className="tabular-nums">{formatUsd(purchase.merchandise_total_usd)} USD</dd>
      </div>
      <div>
        <dt className="text-ink-muted">Gastos</dt>
        <dd className="tabular-nums">{formatUsd(purchase.charges_total_usd)} USD</dd>
      </div>
      <div>
        <dt className="font-semibold">Total</dt>
        <dd className="text-lg font-bold tabular-nums">{formatUsd(purchase.total_usd)} USD</dd>
      </div>
    </dl>
  );
}
