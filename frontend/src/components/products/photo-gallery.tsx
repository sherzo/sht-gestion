"use client";

// Fotos de un producto (FR-008): hasta 5, la primera es la principal. Admin y Almacén
// suben, quitan y reordenan; el Vendedor solo las ve. Antes de subir, el navegador reduce
// la foto (R9) para que suba rápido con datos móviles.
import { ArrowLeft, ArrowRight, ImagePlus, Star, Trash2 } from "lucide-react";
import { useRef, useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { ApiError, apiFetch } from "@/lib/api/client";
import { resizeForUpload } from "@/lib/photos/resize";
import type { Product } from "@/lib/products";

const MAX_PHOTOS = 5;

type PhotoGalleryProps = {
  product: Product;
  editable: boolean;
  onChanged: (product: Product) => void;
};

export function PhotoGallery({ product, editable, onChanged }: PhotoGalleryProps) {
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [removing, setRemoving] = useState<string | null>(null);
  const photos = product.photos;

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No se pudo completar la operación");
    } finally {
      setBusy(false);
    }
  }

  function upload(file: File) {
    void run(async () => {
      const blob = await resizeForUpload(file);
      const form = new FormData();
      form.append("file", blob, file.name);
      onChanged(await apiFetch<Product>(`/products/${product.id}/photos`, { method: "POST", body: form }));
    });
  }

  function move(index: number, offset: number) {
    const ids = photos.map((photo) => photo.id);
    const [moved] = ids.splice(index, 1);
    ids.splice(index + offset, 0, moved);
    void run(async () => {
      onChanged(await apiFetch<Product>(`/products/${product.id}/photos/order`, { method: "PUT", body: { photo_ids: ids } }));
    });
  }

  function remove(photoId: string) {
    setRemoving(null);
    void run(async () => {
      await apiFetch(`/products/${product.id}/photos/${photoId}`, { method: "DELETE" });
      onChanged(await apiFetch<Product>(`/products/${product.id}`));
    });
  }

  return (
    <div className="flex flex-col gap-4">
      {error && <Alert variant="danger">{error}</Alert>}
      {photos.length === 0 ? (
        <p className="rounded-xl border border-line bg-surface p-6 text-center text-ink-muted">Este producto no tiene fotos.</p>
      ) : (
        <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {photos.map((photo, index) => (
            <li key={photo.id} className="flex flex-col gap-2 rounded-xl border border-line bg-surface p-2">
              <div className="relative">
                <img
                  src={photo.url}
                  alt={`Foto ${index + 1} de ${product.name}`}
                  width={photo.width}
                  height={photo.height}
                  loading="lazy"
                  className="aspect-square w-full rounded-lg bg-neutral-100 object-contain"
                />
                {index === 0 && (
                  <span className="absolute left-1 top-1 inline-flex items-center gap-1 rounded-md bg-accent px-2 py-0.5 text-sm font-medium text-on-accent">
                    <Star aria-hidden className="size-4" /> Principal
                  </span>
                )}
              </div>
              {editable && (
                <div className="flex justify-between gap-1">
                  <button
                    type="button"
                    className="inline-flex size-11 items-center justify-center rounded-lg hover:bg-neutral-100 disabled:opacity-40"
                    aria-label={`Mover la foto ${index + 1} antes`}
                    disabled={busy || index === 0}
                    onClick={() => move(index, -1)}
                  >
                    <ArrowLeft aria-hidden className="size-5" />
                  </button>
                  <button
                    type="button"
                    className="inline-flex size-11 items-center justify-center rounded-lg text-danger hover:bg-danger-soft disabled:opacity-40"
                    aria-label={`Quitar la foto ${index + 1}`}
                    disabled={busy}
                    onClick={() => setRemoving(photo.id)}
                  >
                    <Trash2 aria-hidden className="size-5" />
                  </button>
                  <button
                    type="button"
                    className="inline-flex size-11 items-center justify-center rounded-lg hover:bg-neutral-100 disabled:opacity-40"
                    aria-label={`Mover la foto ${index + 1} después`}
                    disabled={busy || index === photos.length - 1}
                    onClick={() => move(index, 1)}
                  >
                    <ArrowRight aria-hidden className="size-5" />
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
      {editable && (
        <div className="flex flex-col gap-1">
          <input
            ref={input}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="sr-only"
            tabIndex={-1}
            onChange={(event) => {
              const file = event.target.files?.[0];
              event.target.value = "";
              if (file) upload(file);
            }}
          />
          <Button variant="secondary" loading={busy} disabled={photos.length >= MAX_PHOTOS} onClick={() => input.current?.click()} className="self-start">
            <ImagePlus aria-hidden className="size-5" /> Agregar foto
          </Button>
          <p className="text-sm text-ink-muted">
            JPG, PNG o WebP de hasta 5 MB. Máximo {MAX_PHOTOS} fotos; la primera es la principal.
          </p>
        </div>
      )}
      <Dialog open={removing !== null} title="Quitar foto" onClose={() => setRemoving(null)}>
        <p>La foto se quitará del producto y del catálogo. ¿Continuar?</p>
        <div className="flex flex-wrap gap-2">
          <Button variant="danger" onClick={() => removing && remove(removing)}>
            Quitar foto
          </Button>
          <Button variant="secondary" onClick={() => setRemoving(null)}>
            Cancelar
          </Button>
        </div>
      </Dialog>
    </div>
  );
}
