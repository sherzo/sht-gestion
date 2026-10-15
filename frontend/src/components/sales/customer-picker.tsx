"use client";

// Cliente opcional de la venta (RF-28/FR-019): buscar uno registrado por cédula, RIF o
// nombre, o escribir uno nuevo. El servidor normaliza el documento y no duplica clientes.
import { uuidv7 } from "@sht/shared";
import { UserRound, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { TextField } from "@/components/ui/field";
import { apiFetch } from "@/lib/api/client";
import type { Customer, CustomerChoice, NewCustomer } from "@/lib/sales";

type Props = { value: CustomerChoice | null; onChange: (value: CustomerChoice | null) => void };

function describe(choice: CustomerChoice): string {
  if (choice.kind === "existing") return [choice.customer.name, choice.customer.document_id].filter(Boolean).join(" · ");
  return [choice.data.name, choice.data.document_id].filter(Boolean).join(" · ");
}

export function CustomerPicker({ value, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Customer[]>([]);
  const [draft, setDraft] = useState<NewCustomer | null>(null);
  const latest = useRef(0);

  useEffect(() => {
    const text = query.trim();
    if (text.length < 2) {
      setResults([]);
      return;
    }
    const request = ++latest.current;
    const timer = setTimeout(() => {
      apiFetch<Customer[]>("/customers", { query: { q: text } })
        .then((found) => request === latest.current && setResults(found))
        .catch(() => request === latest.current && setResults([]));
    }, 250);
    return () => clearTimeout(timer);
  }, [query]);

  if (value) {
    return (
      <div className="flex items-center justify-between gap-2 rounded-xl border border-line bg-surface px-3 py-2">
        <span className="flex items-center gap-2">
          <UserRound aria-hidden className="size-5 text-ink-muted" />
          {describe(value)}
        </span>
        <button type="button" aria-label="Quitar cliente" onClick={() => onChange(null)} className="inline-flex size-11 items-center justify-center rounded-lg hover:bg-neutral-100">
          <X aria-hidden className="size-5" />
        </button>
      </div>
    );
  }
  if (!open) {
    return (
      <Button variant="secondary" onClick={() => setOpen(true)}>
        <UserRound aria-hidden className="size-5" /> Agregar cliente (opcional)
      </Button>
    );
  }
  if (draft) {
    const valid = draft.name.trim().length >= 2;
    return (
      <div className="flex flex-col gap-2 rounded-xl border border-line bg-surface p-3">
        <TextField label="Nombre" value={draft.name} maxLength={100} onChange={(event) => setDraft({ ...draft, name: event.target.value })} />
        <TextField label="Cédula o RIF" value={draft.document_id} maxLength={20} hint="Ej. V-12345678 o J-40123456-7" onChange={(event) => setDraft({ ...draft, document_id: event.target.value })} />
        <TextField label="Teléfono" type="tel" value={draft.phone} maxLength={30} onChange={(event) => setDraft({ ...draft, phone: event.target.value })} />
        <div className="flex gap-2">
          <Button disabled={!valid} onClick={() => onChange({ kind: "new", data: draft })}>
            Usar este cliente
          </Button>
          <Button variant="secondary" onClick={() => setDraft(null)}>
            Volver
          </Button>
        </div>
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-2 rounded-xl border border-line bg-surface p-3">
      <TextField label="Buscar cliente" type="search" placeholder="Cédula, RIF o nombre" value={query} onChange={(event) => setQuery(event.target.value)} />
      {results.length > 0 && (
        <ul className="flex flex-col divide-y divide-line">
          {results.map((customer) => (
            <li key={customer.id}>
              <button type="button" className="min-h-11 w-full px-2 py-2 text-left hover:bg-neutral-100" onClick={() => onChange({ kind: "existing", customer })}>
                <span className="block font-medium">{customer.name}</span>
                <span className="block text-sm text-ink-muted">{[customer.document_id, customer.phone].filter(Boolean).join(" · ")}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" onClick={() => setDraft({ id: uuidv7(), name: query.trim(), document_id: "", phone: "" })}>
          Cliente nuevo
        </Button>
        <Button variant="secondary" onClick={() => setOpen(false)}>
          Sin cliente
        </Button>
      </div>
    </div>
  );
}
