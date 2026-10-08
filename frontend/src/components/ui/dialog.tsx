"use client";

import { X } from "lucide-react";
import { useEffect, useId, useRef } from "react";
import type { ReactNode } from "react";

// Diálogo modal con <dialog> nativo: el navegador vuelve inerte el resto de la página y
// Escape lo cierra.
type DialogProps = {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  dismissible?: boolean;
};

export function Dialog({ open, title, onClose, children, dismissible = true }: DialogProps) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      onCancel={(event) => {
        event.preventDefault();
        if (dismissible) onClose();
      }}
      className="m-auto w-[calc(100%-2rem)] max-w-lg rounded-xl bg-surface p-0 text-ink shadow-lg backdrop:bg-neutral-950/50"
    >
      {open && (
        <div className="flex flex-col gap-4 p-4 sm:p-6">
          <div className="flex items-start justify-between gap-4">
            <h2 id={titleId} className="text-xl font-semibold">
              {title}
            </h2>
            {dismissible && (
              <button
                type="button"
                onClick={onClose}
                aria-label="Cerrar"
                className="inline-flex size-11 items-center justify-center rounded-lg text-ink-muted hover:bg-neutral-100"
              >
                <X aria-hidden className="size-5" />
              </button>
            )}
          </div>
          {children}
        </div>
      )}
    </dialog>
  );
}
