"use client";

// Proveedores (RF-13/FR-001 a FR-003), Admin y Almacén: RIF normalizado y único; se
// desactivan, nunca se borran, para que las compras pasadas sigan mostrando de quién son.
import { ChevronLeft, ChevronRight, Plus, Power, Search } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";

import { AppShell } from "@/components/app-shell";
import { RequireAuth } from "@/components/require-auth";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import type { Column } from "@/components/ui/data-table";
import { Dialog } from "@/components/ui/dialog";
import { SelectField, TextAreaField, TextField } from "@/components/ui/field";
import { StatusChip } from "@/components/ui/status-chip";
import { ApiError, apiFetch } from "@/lib/api/client";
import type { Schemas } from "@/lib/api/client";

type Supplier = Schemas["SupplierOut"];
type SupplierPage = Schemas["SupplierPage"];

const PAGE_SIZE = 50;
const EMPTY = { name: "", rif: "", phone: "", notes: "" };

function SupplierDialog({
  supplier,
  open,
  onClose,
  onSaved,
}: {
  supplier: Supplier | null;
  open: boolean;
  onClose: () => void;
  onSaved: (message: string) => void;
}) {
  const [form, setForm] = useState(EMPTY);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setForm(
        supplier
          ? { name: supplier.name, rif: supplier.rif ?? "", phone: supplier.phone ?? "", notes: supplier.notes ?? "" }
          : EMPTY,
      );
      setFields({});
      setError(null);
    }
  }, [open, supplier]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    const body = { name: form.name, rif: form.rif || null, phone: form.phone || null, notes: form.notes || null };
    try {
      if (supplier) {
        await apiFetch(`/suppliers/${supplier.id}`, { method: "PATCH", body });
        onSaved(`Proveedor ${form.name} guardado.`);
      } else {
        await apiFetch("/suppliers", { method: "POST", body });
        onSaved(`Proveedor ${form.name} creado.`);
      }
    } catch (caught) {
      if (caught instanceof ApiError) {
        setError(caught.message);
        setFields(caught.code === "rif_in_use" ? { rif: caught.message } : caught.fields);
      } else {
        setError("Ocurrió un error inesperado");
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} title={supplier ? `Editar ${supplier.name}` : "Nuevo proveedor"} onClose={onClose}>
      <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
        {error && <Alert variant="danger">{error}</Alert>}
        <TextField label="Nombre" maxLength={120} value={form.name} error={fields.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
        <TextField
          label="RIF (opcional)"
          hint="Por ejemplo J-12345678-9. Se guarda con guiones y mayúsculas."
          maxLength={20}
          value={form.rif}
          error={fields.rif}
          onChange={(event) => setForm({ ...form, rif: event.target.value })}
        />
        <TextField label="Teléfono (opcional)" type="tel" maxLength={30} value={form.phone} error={fields.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} />
        <TextAreaField
          label="Notas (opcional)"
          hint="Por ejemplo, días de despacho o el vendedor que te atiende."
          maxLength={1000}
          rows={3}
          value={form.notes}
          error={fields.notes}
          onChange={(event) => setForm({ ...form, notes: event.target.value })}
        />
        <Button type="submit" loading={saving}>
          {supplier ? "Guardar" : "Crear proveedor"}
        </Button>
      </form>
    </Dialog>
  );
}

function SuppliersContent() {
  const [data, setData] = useState<SupplierPage | null>(null);
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState<Supplier | null>(null);
  const [creating, setCreating] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const result = await apiFetch<SupplierPage>("/suppliers", {
        query: { q: search || undefined, is_active: status || undefined, page, page_size: PAGE_SIZE },
      });
      setData(result);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No se pudieron cargar los proveedores");
    }
  }, [search, status, page]);

  useEffect(() => {
    void load();
  }, [load]);

  async function toggle(supplier: Supplier) {
    setError(null);
    try {
      await apiFetch(`/suppliers/${supplier.id}`, { method: "PATCH", body: { is_active: !supplier.is_active } });
      setNotice(supplier.is_active ? `${supplier.name} desactivado.` : `${supplier.name} reactivado.`);
      void load();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No se pudo cambiar el estado");
    }
  }

  const columns: Column<Supplier>[] = [
    {
      key: "name",
      header: "Proveedor",
      render: (supplier) => (
        <span className="flex flex-wrap items-center gap-2">
          <span className="font-medium">{supplier.name}</span>
          {!supplier.is_active && <StatusChip variant="inactive" label="Inactivo" />}
        </span>
      ),
    },
    { key: "rif", header: "RIF", render: (supplier) => supplier.rif ?? <span className="text-ink-muted">—</span> },
    { key: "phone", header: "Teléfono", render: (supplier) => supplier.phone ?? <span className="text-ink-muted">—</span> },
    {
      key: "actions",
      header: "Acciones",
      render: (supplier) => (
        <span className="flex flex-wrap gap-2">
          <Button variant="secondary" onClick={() => setEditing(supplier)}>
            Editar
          </Button>
          <Button variant="secondary" onClick={() => toggle(supplier)}>
            <Power aria-hidden className="size-4" /> {supplier.is_active ? "Desactivar" : "Reactivar"}
          </Button>
        </span>
      ),
    },
  ];

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <AppShell>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">Proveedores</h1>
        <Button onClick={() => setCreating(true)}>
          <Plus aria-hidden className="size-5" /> Nuevo proveedor
        </Button>
      </div>
      <form
        className="mb-4 grid gap-3 sm:grid-cols-[1fr_auto_auto] sm:items-end"
        onSubmit={(event) => {
          event.preventDefault();
          setPage(1);
          setSearch(query.trim());
        }}
      >
        <TextField label="Buscar por nombre o RIF" value={query} onChange={(event) => setQuery(event.target.value)} />
        <SelectField
          label="Estado"
          value={status}
          onChange={(event) => {
            setPage(1);
            setStatus(event.target.value);
          }}
          options={[
            { value: "", label: "Todos" },
            { value: "true", label: "Activos" },
            { value: "false", label: "Inactivos" },
          ]}
        />
        <Button type="submit" variant="secondary">
          <Search aria-hidden className="size-4" /> Buscar
        </Button>
      </form>
      <div className="mb-4 flex flex-col gap-2">
        {notice && <Alert variant="success">{notice}</Alert>}
        {error && <Alert variant="danger">{error}</Alert>}
      </div>
      {data && (
        <>
          <DataTable caption="Proveedores" columns={columns} rows={data.items} rowKey={(supplier) => supplier.id} emptyMessage="No hay proveedores que coincidan." />
          {data.total > data.page_size && (
            <nav aria-label="Paginación" className="mt-4 flex items-center justify-between gap-3">
              <Button variant="secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>
                <ChevronLeft aria-hidden className="size-4" /> Anterior
              </Button>
              <span className="text-sm text-ink-muted">
                Página {page} de {totalPages}
              </span>
              <Button variant="secondary" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>
                Siguiente <ChevronRight aria-hidden className="size-4" />
              </Button>
            </nav>
          )}
        </>
      )}
      <SupplierDialog
        supplier={editing}
        open={creating || editing !== null}
        onClose={() => {
          setCreating(false);
          setEditing(null);
        }}
        onSaved={(message) => {
          setCreating(false);
          setEditing(null);
          setNotice(message);
          void load();
        }}
      />
    </AppShell>
  );
}

export default function SuppliersPage() {
  return (
    <RequireAuth roles={["admin", "warehouse"]}>
      <SuppliersContent />
    </RequireAuth>
  );
}
