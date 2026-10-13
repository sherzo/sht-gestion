"use client";

// Alta y edición de productos (RF-01/FR-001, FR-004 a FR-006). El formulario se arma con
// los atributos que define la categoría; nunca pide precio ni costo (esos son del Admin,
// en la pestaña "Precio y costo"). Las reglas las verifica el servidor; aquí solo se guía.
import { parseDecimalInput } from "@sht/shared";
import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { DecimalInput } from "@/components/ui/decimal-input";
import { SelectField, TextAreaField, TextField } from "@/components/ui/field";
import { ApiError, apiFetch } from "@/lib/api/client";
import type { Attribute, Category, Product, Unit } from "@/lib/products";

type FormValues = {
  category_id: string;
  unit_id: string;
  name: string;
  description: string;
  attributes: Record<string, string>;
  min_stock: string;
};

type ProductFormProps = {
  categories: Category[];
  units: Unit[];
  /** Sin producto: alta. Con producto: edición. */
  product?: Product;
  onSaved: (product: Product) => void;
  onCancel?: () => void;
};

function toDisplayDecimal(value: string): string {
  return value.replace(".", ",");
}

function initialValues(product: Product | undefined, categories: Category[]): FormValues {
  if (product) {
    return {
      category_id: product.category.id,
      unit_id: product.unit.id,
      name: product.name,
      description: product.description,
      attributes: { ...product.attributes },
      min_stock: toDisplayDecimal(product.min_stock),
    };
  }
  const first = categories[0];
  return {
    category_id: first?.id ?? "",
    unit_id: first?.default_unit_id ?? "",
    name: "",
    description: "",
    attributes: {},
    min_stock: "0",
  };
}

function AttributeInput({
  attribute,
  value,
  error,
  onChange,
}: {
  attribute: Attribute;
  value: string;
  error?: string;
  onChange: (value: string) => void;
}) {
  const label = attribute.is_required ? `${attribute.label} *` : attribute.label;
  if (attribute.data_type === "option") {
    // Una opción desactivada que el producto ya tenía se conserva y se muestra así.
    const options = attribute.options.filter((option) => option.is_active || option.value === value);
    return (
      <SelectField
        label={label}
        value={value}
        error={error}
        onChange={(event) => onChange(event.target.value)}
        options={[
          { value: "", label: attribute.is_required ? "Elige una opción" : "—" },
          ...options.map((option) => ({
            value: option.value,
            label: option.is_active ? option.value : `${option.value} (desactivada)`,
          })),
        ]}
      />
    );
  }
  return (
    <TextField
      label={label}
      value={value}
      error={error}
      inputMode={attribute.data_type === "number" ? "decimal" : undefined}
      maxLength={200}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}

function attributeValue(attribute: Attribute, text: string): string {
  if (attribute.data_type !== "number") return text.trim();
  return parseDecimalInput(text, 6) ?? text.trim();
}

export function ProductForm({ categories, units, product, onSaved, onCancel }: ProductFormProps) {
  const [values, setValues] = useState<FormValues>(() => initialValues(product, categories));
  const [fields, setFields] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!product && !values.category_id && categories.length > 0) setValues(initialValues(undefined, categories));
  }, [categories, product, values.category_id]);

  const category = categories.find((item) => item.id === values.category_id);
  const unit = units.find((item) => item.id === values.unit_id);
  const structureLocked = Boolean(product?.has_movements);
  const attributes = useMemo(
    () => [...(category?.attributes ?? [])].filter((item) => item.is_active).sort((a, b) => a.sort_order - b.sort_order),
    [category],
  );

  function changeCategory(categoryId: string) {
    const next = categories.find((item) => item.id === categoryId);
    setValues((current) => ({
      ...current,
      category_id: categoryId,
      unit_id: next?.default_unit_id ?? current.unit_id,
      // Se conservan los valores de atributos con la misma clave en la nueva categoría.
      attributes: Object.fromEntries(
        Object.entries(current.attributes).filter(([key]) => next?.attributes.some((item) => item.key === key)),
      ),
    }));
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setFields({});
    const minStock = parseDecimalInput(values.min_stock || "0", unit?.decimals ?? 2);
    if (minStock === null) {
      setFields({ min_stock: "Revisa el stock mínimo" });
      return;
    }
    const cleanAttributes = Object.fromEntries(
      attributes
        .map((attribute) => [attribute.key, attributeValue(attribute, values.attributes[attribute.key] ?? "")] as const)
        .filter(([, value]) => value !== ""),
    );
    setSubmitting(true);
    try {
      let saved: Product;
      if (!product) {
        saved = await apiFetch<Product>("/products", {
          method: "POST",
          body: {
            category_id: values.category_id,
            unit_id: category?.unit_locked ? undefined : values.unit_id,
            name: values.name,
            description: values.description,
            attributes: cleanAttributes,
            min_stock: minStock,
          },
        });
      } else {
        const changes: Record<string, unknown> = { updated_at: product.updated_at };
        if (values.name !== product.name) changes.name = values.name;
        if (values.description !== product.description) changes.description = values.description;
        if (values.category_id !== product.category.id) changes.category_id = values.category_id;
        if (values.unit_id !== product.unit.id && !category?.unit_locked) changes.unit_id = values.unit_id;
        if (minStock !== product.min_stock) changes.min_stock = minStock;
        if (JSON.stringify(cleanAttributes) !== JSON.stringify(product.attributes) || changes.category_id) {
          changes.attributes = cleanAttributes;
        }
        saved = await apiFetch<Product>(`/products/${product.id}`, { method: "PATCH", body: changes });
      }
      onSaved(saved);
    } catch (caught) {
      if (caught instanceof ApiError) {
        setError(caught.message);
        setFields(caught.fields);
      } else {
        setError("Ocurrió un error inesperado");
      }
    } finally {
      setSubmitting(false);
    }
  }

  const unitOptions = units
    .filter((item) => item.is_active || item.id === values.unit_id)
    .map((item) => ({ value: item.id, label: `${item.name} (${item.decimals === 0 ? "enteros" : `${item.decimals} decimales`})` }));

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
      {error && <Alert variant="danger">{error}</Alert>}
      <div className="grid gap-4 sm:grid-cols-2">
        <SelectField
          label="Categoría"
          value={values.category_id}
          disabled={structureLocked}
          hint={structureLocked ? "El producto ya tiene movimientos: su categoría no cambia." : undefined}
          error={fields.category_id}
          onChange={(event) => changeCategory(event.target.value)}
          options={categories.map((item) => ({ value: item.id, label: `${item.name} (${item.sku_prefix})` }))}
        />
        <SelectField
          label="Unidad"
          value={values.unit_id}
          disabled={structureLocked || Boolean(category?.unit_locked)}
          hint={category?.unit_locked ? `Los productos de ${category.name} siempre van por ${unit?.name ?? "la misma unidad"}.` : undefined}
          error={fields.unit_id}
          onChange={(event) => setValues({ ...values, unit_id: event.target.value })}
          options={unitOptions}
        />
      </div>
      <TextField
        label="Nombre *"
        required
        maxLength={120}
        value={values.name}
        error={fields.name}
        onChange={(event) => setValues({ ...values, name: event.target.value })}
      />
      <TextAreaField
        label="Descripción"
        maxLength={2000}
        value={values.description}
        error={fields.description}
        onChange={(event) => setValues({ ...values, description: event.target.value })}
      />
      {attributes.length > 0 && (
        <fieldset className="grid gap-4 sm:grid-cols-2">
          <legend className="mb-2 font-semibold">Atributos de {category?.name}</legend>
          {attributes.map((attribute) => (
            <AttributeInput
              key={attribute.id}
              attribute={attribute}
              value={values.attributes[attribute.key] ?? ""}
              error={fields[`attributes.${attribute.key}`]}
              onChange={(value) => setValues({ ...values, attributes: { ...values.attributes, [attribute.key]: value } })}
            />
          ))}
        </fieldset>
      )}
      <DecimalInput
        label="Stock mínimo"
        decimals={unit?.decimals ?? 2}
        hint="Al llegar a este stock o menos, el producto se marca como stock bajo."
        value={values.min_stock}
        error={fields.min_stock}
        onChange={(text) => setValues({ ...values, min_stock: text })}
      />
      <div className="flex flex-wrap gap-2">
        <Button type="submit" loading={submitting}>
          {product ? "Guardar cambios" : "Crear producto"}
        </Button>
        {onCancel && (
          <Button variant="secondary" onClick={onCancel}>
            Cancelar
          </Button>
        )}
      </div>
    </form>
  );
}
