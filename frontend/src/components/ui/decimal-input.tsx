"use client";

// Campo numérico con coma decimal (RNF-07, ADR-0004): el usuario escribe `1.234,56` y la
// pantalla envía `parseDecimalInput(texto)`. Avisa en el momento si el número no es
// válido o tiene más decimales de los que admite la unidad; nunca redondea.
import { parseDecimalInput } from "@sht/shared";
import type { InputHTMLAttributes } from "react";

import { TextField } from "./field";

type DecimalInputProps = Omit<InputHTMLAttributes<HTMLInputElement>, "onChange" | "value" | "type"> & {
  label: string;
  value: string;
  onChange: (text: string) => void;
  /** Decimales que admite la unidad o el monto: 0 (enteros), 2 (metros, USD) o 6 (costo). */
  decimals: number;
  hint?: string;
  error?: string;
};

export function decimalInputError(text: string, decimals: number): string | undefined {
  if (!text.trim() || parseDecimalInput(text, decimals) !== null) return undefined;
  if (parseDecimalInput(text, 20) !== null) {
    return decimals === 0 ? "Solo se admiten números enteros" : `Admite como máximo ${decimals} decimales`;
  }
  return "Escribe un número, por ejemplo 1.234,56";
}

export function DecimalInput({ label, value, onChange, decimals, hint, error, ...props }: DecimalInputProps) {
  const localError = decimalInputError(value, decimals);
  return (
    <TextField
      label={label}
      inputMode={decimals === 0 ? "numeric" : "decimal"}
      autoComplete="off"
      value={value}
      hint={hint}
      error={localError ?? error}
      onChange={(event) => onChange(event.target.value)}
      {...props}
    />
  );
}
