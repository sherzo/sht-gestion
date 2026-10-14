"use client";

// Unidades de medida (RF-05/FR-031), solo Admin: metro (2 decimales), unidad (enteros) y
// las que se agreguen, como caja o paquete. El código y los decimales no cambian.
import { Plus, Power } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { AppShell } from "@/components/app-shell";
import { RequireAuth } from "@/components/require-auth";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import type { Column } from "@/components/ui/data-table";
import { Dialog } from "@/components/ui/dialog";
import { SelectField, TextField } from "@/components/ui/field";
import { StatusChip } from "@/components/ui/status-chip";
import { ApiError, apiFetch } from "@/lib/api/client";
import { useCatalogConfig } from "@/lib/products";
import type { Unit } from "@/lib/products";

function UnitDialog({ unit, open, onClose, onSaved }: { unit: Unit | null; open: boolean; onClose: () => void; onSaved: (message: string) => void }) {
  const [form, setForm] = useState({ code: "", name: "", decimals: "0" });
  const [fields, setFields] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setForm(unit ? { code: unit.code, name: unit.name, decimals: String(unit.decimals) } : { code: "", name: "", decimals: "0" });
      setFields({});
      setError(null);
    }
  }, [open, unit]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      if (unit) {
        await apiFetch(`/units/${unit.id}`, { method: "PATCH", body: { name: form.name } });
        onSaved(`Unidad ${form.name} guardada.`);
      } else {
        await apiFetch("/units", { method: "POST", body: { code: form.code, name: form.name, decimals: Number(form.decimals) } });
        onSaved(`Unidad ${form.name} creada.`);
      }
    } catch (caught) {
      if (caught instanceof ApiError) {
        setError(caught.message);
        setFields(caught.fields);
      } else {
        setError("Ocurrió un error inesperado");
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} title={unit ? `Editar ${unit.name}` : "Nueva unidad"} onClose={onClose}>
      <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
        {error && <Alert variant="danger">{error}</Alert>}
        <TextField
          label="Código"
          hint="Abreviatura corta en minúsculas, por ejemplo caja o pq. No cambia después."
          maxLength={10}
          disabled={Boolean(unit)}
          value={form.code}
          error={fields.code}
          onChange={(event) => setForm({ ...form, code: event.target.value })}
        />
        <TextField label="Nombre" maxLength={40} value={form.name} error={fields.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
        <SelectField
          label="Decimales"
          disabled={Boolean(unit)}
          hint="Una unidad con productos no cambia sus decimales."
          value={form.decimals}
          error={fields.decimals}
          onChange={(event) => setForm({ ...form, decimals: event.target.value })}
          options={[
            { value: "0", label: "Sin decimales (enteros)" },
            { value: "2", label: "2 decimales (como el metro)" },
          ]}
        />
        <Button type="submit" loading={saving}>
          {unit ? "Guardar" : "Crear unidad"}
        </Button>
      </form>
    </Dialog>
  );
}

function UnitsContent() {
  const { units, reload } = useCatalogConfig(true);
  const [editing, setEditing] = useState<Unit | null>(null);
  const [creating, setCreating] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function toggle(unit: Unit) {
    setError(null);
    try {
      await apiFetch(`/units/${unit.id}`, { method: "PATCH", body: { is_active: !unit.is_active } });
      setNotice(unit.is_active ? `Unidad ${unit.name} desactivada.` : `Unidad ${unit.name} reactivada.`);
      reload();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No se pudo cambiar el estado");
    }
  }

  const columns: Column<Unit>[] = [
    { key: "name", header: "Unidad", render: (unit) => <span className="font-medium">{unit.name}</span> },
    { key: "code", header: "Código", render: (unit) => unit.code },
    { key: "decimals", header: "Decimales", render: (unit) => (unit.decimals === 0 ? "Enteros" : `${unit.decimals} decimales`) },
    { key: "status", header: "Estado", render: (unit) => (unit.is_active ? "Activa" : <StatusChip variant="inactive" label="Inactiva" />) },
    {
      key: "actions",
      header: "Acciones",
      render: (unit) => (
        <span className="flex flex-wrap gap-2">
          <Button variant="secondary" onClick={() => setEditing(unit)}>
            Editar
          </Button>
          <Button variant="secondary" onClick={() => toggle(unit)}>
            <Power aria-hidden className="size-4" /> {unit.is_active ? "Desactivar" : "Reactivar"}
          </Button>
        </span>
      ),
    },
  ];

  return (
    <AppShell>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Unidades</h1>
          <Link href="/configuracion/categorias/" className="text-primary underline-offset-2 hover:underline">
            Ir a categorías y atributos
          </Link>
        </div>
        <Button onClick={() => setCreating(true)}>
          <Plus aria-hidden className="size-5" /> Nueva unidad
        </Button>
      </div>
      <div className="mb-4 flex flex-col gap-2">
        {notice && <Alert variant="success">{notice}</Alert>}
        {error && <Alert variant="danger">{error}</Alert>}
      </div>
      <DataTable caption="Unidades" columns={columns} rows={units} rowKey={(unit) => unit.id} emptyMessage="No hay unidades." />
      <UnitDialog
        unit={editing}
        open={creating || editing !== null}
        onClose={() => {
          setCreating(false);
          setEditing(null);
        }}
        onSaved={(message) => {
          setCreating(false);
          setEditing(null);
          setNotice(message);
          reload();
        }}
      />
    </AppShell>
  );
}

export default function UnitsPage() {
  return (
    <RequireAuth roles={["admin"]}>
      <UnitsContent />
    </RequireAuth>
  );
}
