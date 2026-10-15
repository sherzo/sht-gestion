"use client";

// Totales de la venta en USD y Bs (RN-02, RF-18): el total en Bs se calcula sobre el total
// en USD con la tasa de la venta, cuya fecha se muestra si no es la de hoy.
import { formatDate, formatRate, formatUsd, formatVes, todayInCaracas } from "@sht/shared";
import type { SaleCalcResult } from "@sht/shared";

import type { ApplicableRate } from "@/lib/sales";

export function SaleTotals({ result, rate }: { result: SaleCalcResult | null; rate: ApplicableRate }) {
  const today = todayInCaracas();
  return (
    <div className="flex flex-col gap-1 rounded-xl border border-line bg-surface p-4 tabular-nums">
      {result && result.discount_usd !== "0.00" && (
        <>
          <div className="flex justify-between">
            <span>Subtotal</span>
            <span>{formatUsd(result.subtotal_usd)} USD</span>
          </div>
          <div className="flex justify-between text-success">
            <span>Descuento sobre el total</span>
            <span>−{formatUsd(result.discount_usd)} USD</span>
          </div>
        </>
      )}
      <div className="flex items-baseline justify-between text-2xl font-bold">
        <span>Total</span>
        <span>{formatUsd(result?.total_usd ?? "0")} USD</span>
      </div>
      <div className="flex items-baseline justify-between text-xl font-semibold text-primary">
        <span className="sr-only">Total en bolívares</span>
        <span aria-hidden />
        <span>{formatVes(result?.total_ves ?? "0")}</span>
      </div>
      <p className={`text-sm ${rate.business_date === today ? "text-ink-muted" : "text-warning"}`}>
        Tasa BCV {formatRate(rate.rate)}
        {rate.business_date === today ? " (hoy)" : ` del ${formatDate(rate.business_date)}: no hay tasa de hoy`}
      </p>
    </div>
  );
}
