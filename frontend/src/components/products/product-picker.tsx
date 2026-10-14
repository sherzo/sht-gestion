"use client";

// Selector de un producto por búsqueda (RF-06): se usa en ajustes y conteos. Busca en el
// servidor por nombre, descripción, SKU o atributos, con espera de 250 ms entre teclas.
import { Search } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { ProductStatus } from "@/components/products/product-status";
import { TextField } from "@/components/ui/field";
import { apiFetch } from "@/lib/api/client";
import { quantityWithUnit } from "@/lib/products";
import type { Product, ProductPage } from "@/lib/products";

type ProductPickerProps = {
  label?: string;
  onSelect: (product: Product) => void;
  /** Incluir productos inactivos (inventario y conteos). */
  includeInactive?: boolean;
};

export function ProductPicker({ label = "Buscar producto", onSelect, includeInactive = false }: ProductPickerProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Product[]>([]);
  const [searching, setSearching] = useState(false);
  const latest = useRef(0);

  useEffect(() => {
    const text = query.trim();
    if (!text) {
      setResults([]);
      return;
    }
    const request = ++latest.current;
    const timer = setTimeout(() => {
      setSearching(true);
      apiFetch<ProductPage>("/products", { query: { q: text, page_size: 20, is_active: includeInactive ? undefined : true } })
        .then((page) => {
          if (request === latest.current) setResults(page.items);
        })
        .catch(() => {
          if (request === latest.current) setResults([]);
        })
        .finally(() => {
          if (request === latest.current) setSearching(false);
        });
    }, 250);
    return () => clearTimeout(timer);
  }, [query, includeInactive]);

  return (
    <div className="flex flex-col gap-2">
      <TextField
        label={label}
        type="search"
        placeholder="Nombre, SKU o medida (ej. R2 1/2)"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
      />
      {searching && <p className="text-sm text-ink-muted">Buscando…</p>}
      {!searching && query.trim() && results.length === 0 && <p className="text-sm text-ink-muted">No se encontraron productos.</p>}
      {results.length > 0 && (
        <ul className="flex max-h-80 flex-col divide-y divide-line overflow-y-auto rounded-xl border border-line bg-surface">
          {results.map((product) => (
            <li key={product.id}>
              <button
                type="button"
                className="flex min-h-11 w-full items-start gap-3 px-3 py-2 text-left hover:bg-neutral-100"
                onClick={() => {
                  onSelect(product);
                  setQuery("");
                  setResults([]);
                }}
              >
                <Search aria-hidden className="mt-1 size-4 shrink-0 text-ink-muted" />
                <span className="min-w-0 flex-1">
                  <span className="block text-sm text-ink-muted">{product.sku}</span>
                  <span className="block font-medium">{product.name}</span>
                  <span className="block text-sm tabular-nums">Stock: {quantityWithUnit(product.stock, product.unit)}</span>
                </span>
                <ProductStatus product={product} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
