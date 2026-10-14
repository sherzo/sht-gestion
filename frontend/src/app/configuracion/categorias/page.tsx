"use client";

// Categorías y atributos (RF-02 a RF-04/FR-029, FR-030), solo Admin. El prefijo del SKU
// no cambia cuando la categoría ya tiene productos; los atributos y sus opciones no se
// borran, se desactivan, y los productos conservan los valores que ya tenían.
import { Plus, Power, Tags } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { AppShell } from "@/components/app-shell";
import { RequireAuth } from "@/components/require-auth";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { SelectField, TextField } from "@/components/ui/field";
import { StatusChip } from "@/components/ui/status-chip";
import { ApiError, apiFetch } from "@/lib/api/client";
import { useCatalogConfig } from "@/lib/products";
import type { Attribute, Category, Unit } from "@/lib/products";

type Option = { value: string; is_active: boolean };

const DATA_TYPE_LABELS: Record<string, string> = { text: "Texto", number: "Número", option: "Lista de opciones" };

function useForm() {
  const [error, setError] = useState<string | null>(null);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  async function submit(action: () => Promise<void>) {
    setSaving(true);
    setError(null);
    setFields({});
    try {
      await action();
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
  return { error, fields, saving, submit, reset: () => (setError(null), setFields({})) };
}

function Checkbox({ label, checked, onChange, disabled }: { label: string; checked: boolean; onChange: (value: boolean) => void; disabled?: boolean }) {
  return (
    <label className="flex min-h-11 items-center gap-3">
      <input type="checkbox" className="size-5" checked={checked} disabled={disabled} onChange={(event) => onChange(event.target.checked)} />
      {label}
    </label>
  );
}

function CategoryDialog({
  category,
  open,
  units,
  onClose,
  onSaved,
}: {
  category: Category | null;
  open: boolean;
  units: Unit[];
  onClose: () => void;
  onSaved: (message: string) => void;
}) {
  const [form, setForm] = useState({ name: "", sku_prefix: "", default_unit_id: "", unit_locked: false });
  const { error, fields, saving, submit, reset } = useForm();

  useEffect(() => {
    if (!open) return;
    reset();
    setForm(
      category
        ? { name: category.name, sku_prefix: category.sku_prefix, default_unit_id: category.default_unit_id, unit_locked: category.unit_locked }
        : { name: "", sku_prefix: "", default_unit_id: units.find((unit) => unit.code === "u")?.id ?? units[0]?.id ?? "", unit_locked: false },
    );
  }, [open, category]);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    void submit(async () => {
      if (category) {
        const changes: Record<string, unknown> = {};
        if (form.name !== category.name) changes.name = form.name;
        if (form.sku_prefix !== category.sku_prefix) changes.sku_prefix = form.sku_prefix;
        if (form.default_unit_id !== category.default_unit_id) changes.default_unit_id = form.default_unit_id;
        if (form.unit_locked !== category.unit_locked) changes.unit_locked = form.unit_locked;
        await apiFetch(`/categories/${category.id}`, { method: "PATCH", body: changes });
        onSaved(`Categoría ${form.name} guardada.`);
      } else {
        await apiFetch("/categories", { method: "POST", body: form });
        onSaved(`Categoría ${form.name} creada. Sus productos tendrán SKU ${form.sku_prefix}-0001, ${form.sku_prefix}-0002…`);
      }
    });
  }

  return (
    <Dialog open={open} title={category ? `Editar ${category.name}` : "Nueva categoría"} onClose={onClose}>
      <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
        {error && <Alert variant="danger">{error}</Alert>}
        <TextField label="Nombre" maxLength={60} value={form.name} error={fields.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
        <TextField
          label="Prefijo del SKU"
          hint={category?.has_products ? "La categoría ya tiene productos: su prefijo no cambia." : "Tres letras mayúsculas, por ejemplo ACE."}
          maxLength={3}
          disabled={category?.has_products}
          value={form.sku_prefix}
          error={fields.sku_prefix}
          onChange={(event) => setForm({ ...form, sku_prefix: event.target.value.toUpperCase() })}
        />
        <SelectField
          label="Unidad sugerida"
          value={form.default_unit_id}
          error={fields.default_unit_id}
          onChange={(event) => setForm({ ...form, default_unit_id: event.target.value })}
          options={units.filter((unit) => unit.is_active).map((unit) => ({ value: unit.id, label: unit.name }))}
        />
        <Checkbox
          label="Unidad fija (como las mangueras, siempre por metro)"
          checked={form.unit_locked}
          onChange={(value) => setForm({ ...form, unit_locked: value })}
        />
        <Button type="submit" loading={saving}>
          {category ? "Guardar" : "Crear categoría"}
        </Button>
      </form>
    </Dialog>
  );
}

function AttributeDialog({
  category,
  attribute,
  open,
  onClose,
  onSaved,
}: {
  category: Category | null;
  attribute: Attribute | null;
  open: boolean;
  onClose: () => void;
  onSaved: (message: string) => void;
}) {
  const [form, setForm] = useState({ key: "", label: "", data_type: "option", is_required: false, is_filterable: false, sort_order: "0" });
  const [options, setOptions] = useState<Option[]>([]);
  const [newOption, setNewOption] = useState("");
  const { error, fields, saving, submit, reset } = useForm();

  useEffect(() => {
    if (!open) return;
    reset();
    setNewOption("");
    if (attribute) {
      setForm({
        key: attribute.key,
        label: attribute.label,
        data_type: attribute.data_type,
        is_required: attribute.is_required,
        is_filterable: attribute.is_filterable,
        sort_order: String(attribute.sort_order),
      });
      setOptions(attribute.options.map((option) => ({ ...option })));
    } else {
      setForm({ key: "", label: "", data_type: "option", is_required: false, is_filterable: false, sort_order: String((category?.attributes.length ?? 0) + 1) });
      setOptions([]);
    }
  }, [open, attribute]);

  function addOption() {
    const value = newOption.trim();
    if (!value || options.some((option) => option.value === value)) return;
    setOptions([...options, { value, is_active: true }]);
    setNewOption("");
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    void submit(async () => {
      const common = {
        label: form.label,
        is_required: form.is_required,
        is_filterable: form.is_filterable,
        sort_order: Number(form.sort_order) || 0,
        options: form.data_type === "option" ? options : undefined,
      };
      if (attribute) {
        await apiFetch(`/attributes/${attribute.id}`, { method: "PATCH", body: common });
        onSaved(`Atributo ${form.label} guardado.`);
      } else if (category) {
        await apiFetch(`/categories/${category.id}/attributes`, { method: "POST", body: { ...common, key: form.key, data_type: form.data_type } });
        onSaved(`Atributo ${form.label} agregado a ${category.name}.`);
      }
    });
  }

  return (
    <Dialog open={open} title={attribute ? `Editar ${attribute.label}` : `Nuevo atributo de ${category?.name ?? ""}`} onClose={onClose}>
      <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
        {error && <Alert variant="danger">{error}</Alert>}
        <TextField label="Nombre visible" maxLength={60} value={form.label} error={fields.label} onChange={(event) => setForm({ ...form, label: event.target.value })} />
        <TextField
          label="Clave interna"
          hint="Minúsculas sin espacios ni acentos, por ejemplo rosca o medida_2. No cambia después."
          maxLength={40}
          disabled={Boolean(attribute)}
          value={form.key}
          error={fields.key}
          onChange={(event) => setForm({ ...form, key: event.target.value })}
        />
        <SelectField
          label="Tipo"
          disabled={Boolean(attribute)}
          value={form.data_type}
          error={fields.data_type}
          onChange={(event) => setForm({ ...form, data_type: event.target.value })}
          options={Object.entries(DATA_TYPE_LABELS).map(([value, label]) => ({ value, label }))}
        />
        {form.data_type === "option" && (
          <fieldset className="flex flex-col gap-2">
            <legend className="mb-1 text-sm font-medium">Opciones</legend>
            {fields.options && <p className="text-sm text-danger">{fields.options}</p>}
            {options.map((option, index) => (
              <Checkbox
                key={option.value}
                label={option.value}
                checked={option.is_active}
                onChange={(value) => setOptions(options.map((item, position) => (position === index ? { ...item, is_active: value } : item)))}
              />
            ))}
            <p className="text-sm text-ink-muted">Desmarca una opción para desactivarla: los productos que ya la tienen la conservan.</p>
            <div className="flex items-end gap-2">
              <div className="flex-1">
                <TextField label="Nueva opción" maxLength={60} value={newOption} onChange={(event) => setNewOption(event.target.value)} />
              </div>
              <Button variant="secondary" onClick={addOption}>
                Agregar
              </Button>
            </div>
          </fieldset>
        )}
        <Checkbox label="Obligatorio al crear productos" checked={form.is_required} onChange={(value) => setForm({ ...form, is_required: value })} />
        <Checkbox label="Sirve como filtro en la búsqueda y el catálogo" checked={form.is_filterable} onChange={(value) => setForm({ ...form, is_filterable: value })} />
        <TextField label="Orden" inputMode="numeric" value={form.sort_order} error={fields.sort_order} onChange={(event) => setForm({ ...form, sort_order: event.target.value })} />
        <Button type="submit" loading={saving}>
          {attribute ? "Guardar" : "Agregar atributo"}
        </Button>
      </form>
    </Dialog>
  );
}

function CategoriesContent() {
  const { categories, units, reload } = useCatalogConfig(true);
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);
  const [creatingCategory, setCreatingCategory] = useState(false);
  const [attributeTarget, setAttributeTarget] = useState<{ category: Category; attribute: Attribute | null } | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function saved(message: string) {
    setCreatingCategory(false);
    setEditingCategory(null);
    setAttributeTarget(null);
    setNotice(message);
    reload();
  }

  async function toggle(path: string, active: boolean, label: string) {
    setError(null);
    try {
      await apiFetch(path, { method: "PATCH", body: { is_active: !active } });
      saved(active ? `${label} desactivado.` : `${label} reactivado.`);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No se pudo cambiar el estado");
    }
  }

  return (
    <AppShell>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Categorías y atributos</h1>
          <span className="flex flex-wrap gap-4">
            <Link href="/configuracion/unidades/" className="text-primary underline-offset-2 hover:underline">
              Ir a unidades
            </Link>
            <Link href="/configuracion/gastos/" className="text-primary underline-offset-2 hover:underline">
              Ir a gastos frecuentes
            </Link>
          </span>
        </div>
        <Button onClick={() => setCreatingCategory(true)}>
          <Plus aria-hidden className="size-5" /> Nueva categoría
        </Button>
      </div>
      <div className="mb-4 flex flex-col gap-2">
        {notice && <Alert variant="success">{notice}</Alert>}
        {error && <Alert variant="danger">{error}</Alert>}
      </div>
      <div className="flex flex-col gap-4">
        {categories.map((category) => {
          const unit = units.find((item) => item.id === category.default_unit_id);
          return (
            <section key={category.id} aria-labelledby={`categoria-${category.id}`} className="rounded-xl border border-line bg-surface p-4">
              <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 id={`categoria-${category.id}`} className="text-lg font-semibold">
                    {category.name} <span className="text-ink-muted">({category.sku_prefix})</span>
                  </h2>
                  <p className="text-sm text-ink-muted">
                    Unidad {category.unit_locked ? "fija" : "sugerida"}: {unit?.name ?? "—"}
                  </p>
                  {!category.is_active && <StatusChip variant="inactive" label="Inactiva" />}
                </div>
                <span className="flex flex-wrap gap-2">
                  <Button variant="secondary" onClick={() => setEditingCategory(category)}>
                    Editar
                  </Button>
                  <Button variant="secondary" onClick={() => toggle(`/categories/${category.id}`, category.is_active, `Categoría ${category.name}`)}>
                    <Power aria-hidden className="size-4" /> {category.is_active ? "Desactivar" : "Reactivar"}
                  </Button>
                  <Button variant="secondary" onClick={() => setAttributeTarget({ category, attribute: null })}>
                    <Tags aria-hidden className="size-4" /> Nuevo atributo
                  </Button>
                </span>
              </div>
              {category.attributes.length === 0 ? (
                <p className="text-ink-muted">Sin atributos.</p>
              ) : (
                <ul className="flex flex-col divide-y divide-line">
                  {category.attributes.map((attribute) => (
                    <li key={attribute.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                      <span>
                        <span className="font-medium">{attribute.label}</span>{" "}
                        <span className="text-sm text-ink-muted">
                          {DATA_TYPE_LABELS[attribute.data_type]}
                          {attribute.is_required && " · obligatorio"}
                          {attribute.is_filterable && " · filtro"}
                          {attribute.data_type === "option" && ` · ${attribute.options.filter((option) => option.is_active).length} opciones`}
                        </span>
                        {!attribute.is_active && (
                          <span className="ml-2">
                            <StatusChip variant="inactive" />
                          </span>
                        )}
                      </span>
                      <span className="flex flex-wrap gap-2">
                        <Button variant="secondary" onClick={() => setAttributeTarget({ category, attribute })}>
                          Editar
                        </Button>
                        <Button variant="secondary" onClick={() => toggle(`/attributes/${attribute.id}`, attribute.is_active, `Atributo ${attribute.label}`)}>
                          {attribute.is_active ? "Desactivar" : "Reactivar"}
                        </Button>
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          );
        })}
      </div>
      <CategoryDialog
        category={editingCategory}
        open={creatingCategory || editingCategory !== null}
        units={units}
        onClose={() => {
          setCreatingCategory(false);
          setEditingCategory(null);
        }}
        onSaved={saved}
      />
      <AttributeDialog
        category={attributeTarget?.category ?? null}
        attribute={attributeTarget?.attribute ?? null}
        open={attributeTarget !== null}
        onClose={() => setAttributeTarget(null)}
        onSaved={saved}
      />
    </AppShell>
  );
}

export default function CategoriesPage() {
  return (
    <RequireAuth roles={["admin"]}>
      <CategoriesContent />
    </RequireAuth>
  );
}
