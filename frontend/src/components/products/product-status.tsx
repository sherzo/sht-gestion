import { StatusChip } from "@/components/ui/status-chip";
import { productChips } from "@/lib/products";
import type { Product } from "@/lib/products";

// Estados de un producto (stock bajo o negativo, inactivo, publicado) como etiquetas.
export function ProductStatus({ product }: { product: Product }) {
  const chips = productChips(product);
  if (chips.length === 0) return null;
  return (
    <span className="flex flex-wrap gap-1">
      {chips.map((chip) => (
        <StatusChip key={chip} variant={chip} />
      ))}
    </span>
  );
}
