"use client";

import { Eye, EyeOff } from "lucide-react";
import { useId, useState } from "react";
import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from "react";

// Campos con etiqueta, ayuda y error accesibles (guía de estilos §6).
const CONTROL =
  "min-h-11 w-full rounded-lg border border-line bg-surface px-3 text-base text-ink aria-invalid:border-danger";

type FieldShellProps = {
  id: string;
  label: string;
  hint?: string;
  error?: string;
  children: ReactNode;
};

function FieldShell({ id, label, hint, error, children }: FieldShellProps) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium text-ink">
        {label}
      </label>
      {children}
      {hint && !error && (
        <p id={`${id}-hint`} className="text-sm text-ink-muted">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} className="text-sm text-danger">
          {error}
        </p>
      )}
    </div>
  );
}

function describedBy(id: string, hint?: string, error?: string): string | undefined {
  if (error) return `${id}-error`;
  if (hint) return `${id}-hint`;
  return undefined;
}

type TextFieldProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  hint?: string;
  error?: string;
};

export function TextField({ label, hint, error, id, type, className = "", ...props }: TextFieldProps) {
  const generated = useId();
  const fieldId = id ?? generated;
  const [visible, setVisible] = useState(false);
  const isSecret = type === "password";

  const input = (
    <input
      id={fieldId}
      type={isSecret && visible ? "text" : type}
      aria-invalid={error ? true : undefined}
      aria-describedby={describedBy(fieldId, hint, error)}
      className={`${CONTROL} ${isSecret ? "pr-12" : ""} ${className}`}
      {...props}
    />
  );

  return (
    <FieldShell id={fieldId} label={label} hint={hint} error={error}>
      {isSecret ? (
        // Contraseñas, PIN y código de instalación: botón para ver lo que se escribe.
        <div className="relative">
          {input}
          <button
            type="button"
            onClick={() => setVisible((current) => !current)}
            aria-label={visible ? "Ocultar contraseña" : "Mostrar contraseña"}
            aria-pressed={visible}
            aria-controls={fieldId}
            className="absolute inset-y-0 right-0 inline-flex size-11 items-center justify-center rounded-lg text-ink-muted hover:text-ink"
          >
            {visible ? <EyeOff aria-hidden className="size-5" /> : <Eye aria-hidden className="size-5" />}
          </button>
        </div>
      ) : (
        input
      )}
    </FieldShell>
  );
}

type SelectFieldProps = SelectHTMLAttributes<HTMLSelectElement> & {
  label: string;
  hint?: string;
  error?: string;
  options: { value: string; label: string }[];
};

export function SelectField({
  label,
  hint,
  error,
  id,
  options,
  className = "",
  ...props
}: SelectFieldProps) {
  const generated = useId();
  const fieldId = id ?? generated;
  return (
    <FieldShell id={fieldId} label={label} hint={hint} error={error}>
      <select
        id={fieldId}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy(fieldId, hint, error)}
        className={`${CONTROL} ${className}`}
        {...props}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </FieldShell>
  );
}
