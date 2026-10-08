import type { ReactNode } from "react";

// Tabla en PC y tarjetas apiladas en el teléfono (< 640 px), sin desplazamiento horizontal.
export type Column<T> = {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  className?: string;
};

type DataTableProps<T> = {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  emptyMessage: string;
  caption?: string;
};

export function DataTable<T>({ columns, rows, rowKey, emptyMessage, caption }: DataTableProps<T>) {
  if (rows.length === 0) {
    return (
      <p className="rounded-xl border border-line bg-surface p-6 text-center text-ink-muted">
        {emptyMessage}
      </p>
    );
  }

  return (
    <>
      <table className="hidden w-full overflow-hidden rounded-xl border border-line bg-surface text-left sm:table">
        {caption && <caption className="sr-only">{caption}</caption>}
        <thead className="bg-neutral-100 text-sm text-ink-muted">
          <tr>
            {columns.map((column) => (
              <th key={column.key} scope="col" className={`px-3 py-2 font-medium ${column.className ?? ""}`}>
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={rowKey(row)} className="border-t border-line align-top">
              {columns.map((column) => (
                <td key={column.key} className={`px-3 py-2 ${column.className ?? ""}`}>
                  {column.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>

      <ul className="flex flex-col gap-3 sm:hidden">
        {rows.map((row) => (
          <li key={rowKey(row)} className="rounded-xl border border-line bg-surface p-4 shadow-sm">
            <dl className="flex flex-col gap-2">
              {columns.map((column) => (
                <div key={column.key} className="flex flex-col">
                  <dt className="text-sm text-ink-muted">{column.header}</dt>
                  <dd className="break-words">{column.render(row)}</dd>
                </div>
              ))}
            </dl>
          </li>
        ))}
      </ul>
    </>
  );
}
