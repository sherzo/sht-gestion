"use client";

// Buscador de productos con filtros (RF-06/FR-032, FR-033): texto libre sin importar
// mayúsculas ni acentos (nombre, SKU o medida, ej. "r2 1/2"), categoría, atributos
// filtrables de la categoría, estado y "solo stock bajo". Espera 250 ms entre teclas.
import { useEffect, useState } from "react";

import { SelectField, TextField } from "@/components/ui/field";
import type { Category } from "@/lib/products";

export type SearchFilters = {
  q: string;
  category_id: string;
  is_active: string;
  low_stock: boolean;
  attributes: Record<string, string>;
};

export const EMPTY_FILTERS: SearchFilters = { q: "", category_id: "", is_active: "true", low_stock: false, attributes: {} };

/** Parámetros de `GET /products` (los atributos van como `attr.<clave>`). */
export function searchParams(filters: SearchFilters, extra: Record<string, string | number> = {}): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.q.trim()) params.set("q", filters.q.trim());
  if (filters.category_id) params.set("category_id", filters.category_id);
  if (filters.is_active) params.set("is_active", filters.is_active);
  if (filters.low_stock) params.set("low_stock", "true");
  for (const [key, value] of Object.entries(filters.attributes)) {
    if (value) params.set(`attr.${key}`, value);
  }
  for (const [key, value] of Object.entries(extra)) params.set(key, String(value));
  return params;
}

type ProductSearchProps = {
  categories: Category[];
  value: SearchFilters;
  onChange: (filters: SearchFilters) => void;
  /** Admin y Almacén pueden ver productos inactivos. */
  showStatus: boolean;
};

export function ProductSearch({ categories, value, onChange, showStatus }: ProductSearchProps) {
  const [text, setText] = useState(value.q);

  useEffect(() => {
    if (text === value.q) return;
    const timer = setTimeout(() => onChange({ ...value, q: text }), 250);
    return () => clearTimeout(timer);
  }, [text, value, onChange]);

  const category = categories.find((item) => item.id === value.category_id);
  const filterable = (category?.attributes ?? []).filter((attribute) => attribute.is_filterable && attribute.data_type === "option");

  return (
    <div className="flex flex-col gap-3">
      <TextField
        label="Buscar"
        type="search"
        placeholder="Nombre, SKU o medida (ej. R2 1/2)"
        value={text}
        onChange={(event) => setText(event.target.value)}
      />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <SelectField
          label="Categoría"
          value={value.category_id}
          onChange={(event) => onChange({ ...value, category_id: event.target.value, attributes: {} })}
          options={[{ value: "", label: "Todas" }, ...categories.map((item) => ({ value: item.id, label: item.name }))]}
        />
        {filterable.map((attribute) => (
          <SelectField
            key={attribute.id}
            label={attribute.label}
            value={value.attributes[attribute.key] ?? ""}
            onChange={(event) => onChange({ ...value, attributes: { ...value.attributes, [attribute.key]: event.target.value } })}
            options={[{ value: "", label: "Todos" }, ...attribute.options.map((option) => ({ value: option.value, label: option.value }))]}
          />
        ))}
        {showStatus && (
          <SelectField
            label="Estado"
            value={value.is_active}
            onChange={(event) => onChange({ ...value, is_active: event.target.value })}
            options={[
              { value: "true", label: "Activos" },
              { value: "false", label: "Inactivos" },
              { value: "", label: "Todos" },
            ]}
          />
        )}
      </div>
      <label className="flex min-h-11 items-center gap-3 self-start">
        <input type="checkbox" className="size-5" checked={value.low_stock} onChange={(event) => onChange({ ...value, low_stock: event.target.checked })} />
        Solo stock bajo
      </label>
    </div>
  );
}
