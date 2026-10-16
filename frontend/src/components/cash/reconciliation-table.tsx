"use client";

// Cuadre de la caja por método de pago (RF-31; FR-006, FR-008; research R13 de la etapa
// 1.4): fondo, cobrado, vuelto, devoluciones, egresos y esperado, cada método en su moneda.
// En el cierre agrega lo contado (efectivo) o verificado (electrónicos) y la diferencia en
// vivo. Tabla en PC y una tarjeta por método en el teléfono.
import { DecimalInput } from "@/components/ui/decimal-input";
import { DataTable } from "@/components/ui/data-table";
import type { Column } from "@/components/ui/data-table";
import { formatMethodAmount, isCashMethod } from "@/lib/cash";

export type ReconciliationLine = {
  method: string;
  method_name: string;
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
  device_expected?: string | null;
};

type Props = {
  rows: ReconciliationLine[];
  /** Campos de contado del cierre: texto escrito por método y su cambio. */
  counting?: { values: Record<string, string>; onChange: (method: string, text: string) => void };
  caption: string;
};

/** Diferencia con signo y texto, nunca solo color (guía de estilos §2.4). */
export function DifferenceText({ value, currency }: { value: string; currency: string }) {
  const amount = formatMethodAmount(value.replace(/^-/, ""), currency);
  if (/^-?0(\.0+)?$/.test(value)) return <span className="text-ink-muted">Sin diferencia</span>;
  if (value.startsWith("-")) return <span className="font-semibold text-danger">Faltante −{amount}</span>;
  return <span className="font-semibold text-success">Sobrante +{amount}</span>;
}

export function ReconciliationTable({ rows, counting, caption }: Props) {
  const money = (key: keyof ReconciliationLine, header: string, className = "text-right"): Column<ReconciliationLine> => ({
    key,
    header,
    className,
    render: (row) => formatMethodAmount(String(row[key] ?? "0"), row.currency),
  });
  const columns: Column<ReconciliationLine>[] = [
    { key: "method", header: "Método", render: (row) => <span className="font-medium">{row.method_name}</span> },
    money("opening", "Fondo"),
    money("collected", "Cobrado"),
    money("change_given", "Vuelto"),
    money("refunded", "Devuelto"),
    money("change_recovered", "Vuelto recuperado"),
    money("outflows", "Egresos"),
    {
      key: "expected",
      header: "Esperado",
      className: "text-right font-semibold",
      render: (row) => formatMethodAmount(row.expected, row.currency),
    },
  ];
  if (counting) {
    columns.push({
      key: "counted",
      header: "Contado o verificado",
      render: (row) => (
        <DecimalInput
          label={isCashMethod(row.method) ? `Contado en ${row.method_name}` : `Verificado en ${row.method_name}`}
          decimals={2}
          value={counting.values[row.method] ?? ""}
          placeholder="0,00"
          onChange={(text) => counting.onChange(row.method, text)}
        />
      ),
    });
  } else if (rows.some((row) => row.counted !== null)) {
    columns.push(money("counted", "Contado o verificado"));
  }
  if (rows.some((row) => row.difference !== null)) {
    columns.push({
      key: "difference",
      header: "Diferencia",
      render: (row) => (row.difference === null ? "—" : <DifferenceText value={row.difference} currency={row.currency} />),
    });
  }
  return <DataTable columns={columns} rows={rows} rowKey={(row) => row.method} emptyMessage="Sin métodos de pago" caption={caption} />;
}
