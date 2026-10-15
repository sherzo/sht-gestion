"use client";

// Buscador de la pantalla de venta (FR-010, RNF-04): productos activos con precio, por
// nombre, SKU o medida, con precio en USD y Bs y stock actual. Enter agrega el primero y
// F2 vuelve al buscador. El Vendedor nunca recibe costos (principio IV).
import { formatUsd, formatVes, usdToVes } from "@sht/shared";
import { Plus } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { Ref } from "react";

import { TextField } from "@/components/ui/field";
import { apiFetch } from "@/lib/api/client";
import { hasPrice, quantityWithUnit } from "@/lib/products";
import type { ProductPage } from "@/lib/products";
import type { SellableProduct } from "@/lib/sales";

type Props = { rate: string; onSelect: (product: SellableProduct) => void; inputRef?: Ref<HTMLInputElement> };

export function SaleProductSearch({ rate, onSelect, inputRef }: Props) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SellableProduct[]>([]);
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
      apiFetch<ProductPage>("/products", { query: { q: text, page_size: 20, is_active: true } })
        .then((page) => {
          if (request !== latest.current) return;
          setResults(page.items.filter((product): product is SellableProduct => hasPrice(product) && product.sale_price_usd !== null));
        })
        .catch(() => {
          if (request === latest.current) setResults([]);
        })
        .finally(() => {
          if (request === latest.current) setSearching(false);
        });
    }, 200);
    return () => clearTimeout(timer);
  }, [query]);

  function choose(product: SellableProduct) {
    onSelect(product);
    setQuery("");
    setResults([]);
  }

  return (
    <div className="flex flex-col gap-2">
      <TextField
        ref={inputRef}
        label="Agregar producto (F2)"
        type="search"
        placeholder="Nombre, SKU o medida (ej. R2 1/2)"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && results[0]) {
            event.preventDefault();
            choose(results[0]);
          }
        }}
      />
      {searching && <p className="text-sm text-ink-muted">Buscando…</p>}
      {!searching && query.trim() && results.length === 0 && <p className="text-sm text-ink-muted">No se encontraron productos con precio.</p>}
      {results.length > 0 && (
        <ul className="flex max-h-72 flex-col divide-y divide-line overflow-y-auto rounded-xl border border-line bg-surface">
          {results.map((product) => (
            <li key={product.id}>
              <button type="button" className="flex min-h-11 w-full items-center gap-3 px-3 py-2 text-left hover:bg-neutral-100" onClick={() => choose(product)}>
                <Plus aria-hidden className="size-4 shrink-0 text-ink-muted" />
                <span className="min-w-0 flex-1">
                  <span className="block text-sm text-ink-muted">{product.sku}</span>
                  <span className="block font-medium">{product.name}</span>
                  <span className="block text-sm tabular-nums">Stock: {quantityWithUnit(product.stock, product.unit)}</span>
                </span>
                <span className="text-right tabular-nums">
                  <span className="block font-semibold">{formatUsd(product.sale_price_usd ?? "0")} USD</span>
                  <span className="block text-sm text-ink-muted">{formatVes(usdToVes(product.sale_price_usd ?? "0", rate))}</span>
                  <span className="block text-xs text-ink-muted">por {product.unit.code}</span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
