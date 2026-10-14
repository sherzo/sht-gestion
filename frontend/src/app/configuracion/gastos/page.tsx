"use client";

// Gastos frecuentes de las compras (RF-14/FR-032), solo Admin: por ejemplo "Comisión de
// compra" (10 % de la factura) o "Envío China–Venezuela" (monto fijo). Al registrar una
// compra se eligen de la lista y se pueden cambiar ahí; editar la lista no cambia las
// compras existentes. Se desactivan, nunca se borran.
import { formatPercent, formatUsd, formatVes, parseDecimalInput } from "@sht/shared";
import { Plus, Power } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";

import { AppShell } from "@/components/app-shell";
import { RequireAuth } from "@/components/require-auth";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import type { Column } from "@/components/ui/data-table";
import { DecimalInput } from "@/components/ui/decimal-input";
import { Dialog } from "@/components/ui/dialog";
import { SelectField, TextField } from "@/components/ui/field";
import { StatusChip } from "@/components/ui/status-chip";
import { ApiError, apiFetch } from "@/lib/api/client";
import type { ChargeTemplate } from "@/lib/purchases";

type Form = { name: string; charge_type: "percent" | "fixed"; value: string; currency: "USD" | "VES" };
const EMPTY: Form = { name: "", charge_type: "percent", value: "", currency: "USD" };

function valueLabel(template: ChargeTemplate): string {
  if (!template.default_value) return template.charge_type === "percent" ? "% sin valor sugerido" : "Monto sin valor sugerido";
  if (template.charge_type === "percent") return `${formatPercent(template.default_value)} de la factura`;
  return template.currency === "VES" ? formatVes(template.default_value) : `${formatUsd(template.default_value)} USD`;
}

function TemplateDialog({ template, open, onClose, onSaved }: { template: ChargeTemplate | null; open: boolean; onClose: () => void; onSaved: (message: string) => void }) {
  const [form, setForm] = useState<Form>(EMPTY);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setForm(
      template
        ? {
            name: template.name,
            charge_type: template.charge_type as Form["charge_type"],
            value: template.default_value ? template.default_value.replace(".", ",") : "",
            currency: (template.currency as Form["currency"] | null) ?? "USD",
          }
        : EMPTY,
    );
    setFields({});
    setError(null);
  }, [open, template]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const value = form.value.trim() ? parseDecimalInput(form.value, 2) : null;
    if (form.value.trim() && value === null) {
      setFields({ default_value: "Escribe un número con hasta 2 decimales" });
      return;
    }
    setSaving(true);
    setError(null);
    const currency = form.charge_type === "fixed" ? form.currency : null;
    try {
      if (template) {
        await apiFetch(`/charge-templates/${template.id}`, { method: "PATCH", body: { name: form.name, default_value: value, currency } });
        onSaved(`Gasto ${form.name} guardado.`);
      } else {
        await apiFetch("/charge-templates", { method: "POST", body: { name: form.name, charge_type: form.charge_type, default_value: value, currency } });
        onSaved(`Gasto ${form.name} creado.`);
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
    <Dialog open={open} title={template ? `Editar ${template.name}` : "Nuevo gasto frecuente"} onClose={onClose}>
      <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
        {error && <Alert variant="danger">{error}</Alert>}
        <TextField label="Nombre" maxLength={80} value={form.name} error={fields.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
        <SelectField
          label="Tipo"
          disabled={Boolean(template)}
          hint={template ? "El tipo no cambia después de crearlo." : undefined}
          value={form.charge_type}
          onChange={(event) => setForm({ ...form, charge_type: event.target.value as Form["charge_type"] })}
          options={[
            { value: "percent", label: "Porcentaje de la factura" },
            { value: "fixed", label: "Monto fijo" },
          ]}
        />
        {form.charge_type === "fixed" && (
          <SelectField
            label="Moneda"
            value={form.currency}
            error={fields.currency}
            onChange={(event) => setForm({ ...form, currency: event.target.value as Form["currency"] })}
            options={[
              { value: "USD", label: "USD" },
              { value: "VES", label: "Bs" },
            ]}
          />
        )}
        <DecimalInput
          label={form.charge_type === "percent" ? "Porcentaje sugerido (opcional)" : "Monto sugerido (opcional)"}
          hint="Se puede cambiar en cada compra."
          decimals={2}
          value={form.value}
          error={fields.default_value}
          onChange={(text) => setForm({ ...form, value: text })}
        />
        <Button type="submit" loading={saving}>
          {template ? "Guardar" : "Crear gasto"}
        </Button>
      </form>
    </Dialog>
  );
}

function ChargeTemplatesContent() {
  const [templates, setTemplates] = useState<ChargeTemplate[]>([]);
  const [editing, setEditing] = useState<ChargeTemplate | null>(null);
  const [creating, setCreating] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    apiFetch<ChargeTemplate[]>("/charge-templates", { query: { include_inactive: true } })
      .then(setTemplates)
      .catch((caught) => setError(caught instanceof ApiError ? caught.message : "No se pudieron cargar los gastos"));
  }, []);

  useEffect(load, [load]);

  async function toggle(template: ChargeTemplate) {
    setError(null);
    try {
      await apiFetch(`/charge-templates/${template.id}`, { method: "PATCH", body: { is_active: !template.is_active } });
      setNotice(template.is_active ? `${template.name} desactivado.` : `${template.name} reactivado.`);
      load();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No se pudo cambiar el estado");
    }
  }

  const columns: Column<ChargeTemplate>[] = [
    {
      key: "name",
      header: "Gasto",
      render: (t) => (
        <span className="flex flex-wrap items-center gap-2">
          <span className="font-medium">{t.name}</span>
          {!t.is_active && <StatusChip variant="inactive" />}
        </span>
      ),
    },
    { key: "value", header: "Valor sugerido", render: valueLabel },
    {
      key: "actions",
      header: "Acciones",
      render: (t) => (
        <span className="flex flex-wrap gap-2">
          <Button variant="secondary" onClick={() => setEditing(t)}>
            Editar
          </Button>
          <Button variant="secondary" onClick={() => toggle(t)}>
            <Power aria-hidden className="size-4" /> {t.is_active ? "Desactivar" : "Reactivar"}
          </Button>
        </span>
      ),
    },
  ];

  return (
    <AppShell>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Gastos frecuentes</h1>
          <Link href="/configuracion/categorias/" className="text-primary underline-offset-2 hover:underline">
            Ir a categorías y atributos
          </Link>
        </div>
        <Button onClick={() => setCreating(true)}>
          <Plus aria-hidden className="size-5" /> Nuevo gasto
        </Button>
      </div>
      <p className="mb-4 text-ink-muted">
        Gastos habituales de las compras, como el envío de la importadora o la comisión de compra. Se reparten entre los productos según su valor.
      </p>
      <div className="mb-4 flex flex-col gap-2">
        {notice && <Alert variant="success">{notice}</Alert>}
        {error && <Alert variant="danger">{error}</Alert>}
      </div>
      <DataTable caption="Gastos frecuentes" columns={columns} rows={templates} rowKey={(t) => t.id} emptyMessage="Todavía no hay gastos frecuentes." />
      <TemplateDialog
        template={editing}
        open={creating || editing !== null}
        onClose={() => {
          setCreating(false);
          setEditing(null);
        }}
        onSaved={(message) => {
          setCreating(false);
          setEditing(null);
          setNotice(message);
          load();
        }}
      />
    </AppShell>
  );
}

export default function ChargeTemplatesPage() {
  return (
    <RequireAuth roles={["admin"]}>
      <ChargeTemplatesContent />
    </RequireAuth>
  );
}
