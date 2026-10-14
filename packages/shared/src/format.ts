// Formato de fechas y números de la interfaz (RNF-07): dd/mm/aaaa hh:mm en
// America/Caracas y números `1.234,56`.

export const BUSINESS_TIME_ZONE = "America/Caracas";

const dateTimeFormat = new Intl.DateTimeFormat("es-VE", {
  timeZone: BUSINESS_TIME_ZONE,
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

const timeFormat = new Intl.DateTimeFormat("es-VE", {
  timeZone: BUSINESS_TIME_ZONE,
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

function parts(format: Intl.DateTimeFormat, value: string | Date): Record<string, string> {
  const date = typeof value === "string" ? new Date(value) : value;
  return Object.fromEntries(format.formatToParts(date).map((part) => [part.type, part.value]));
}

/** `07/10/2026 14:05`, en hora de Caracas. */
export function formatDateTime(value: string | Date): string {
  const p = parts(dateTimeFormat, value);
  return `${p.day}/${p.month}/${p.year} ${p.hour}:${p.minute}`;
}

/** `14:05`, en hora de Caracas. */
export function formatTime(value: string | Date): string {
  const p = parts(timeFormat, value);
  return `${p.hour}:${p.minute}`;
}

// Números de la interfaz (RNF-07, ADR-0004): `1.234,56`. Los decimales llegan de la API
// como cadenas y se formatean sin pasar por `number`, para no perder exactitud.

const DECIMAL_RE = /^(-?)(\d+)(?:\.(\d+))?$/;

/** Redondea mitad hacia arriba (ADR-0004) una cadena decimal a `decimals` decimales. */
function roundDecimalString(value: string, decimals: number): { negative: boolean; integer: string; fraction: string } {
  const match = DECIMAL_RE.exec(value.trim());
  if (!match) throw new Error(`Decimal inválido: ${value}`);
  const [, sign, intPart, fracPart = ""] = match;
  const digits = BigInt(intPart + fracPart.padEnd(decimals, "0").slice(0, decimals));
  const roundUp = fracPart.length > decimals && Number(fracPart[decimals]) >= 5;
  const scaled = (digits + (roundUp ? 1n : 0n)).toString().padStart(decimals + 1, "0");
  const integer = scaled.slice(0, scaled.length - decimals);
  const fraction = decimals > 0 ? scaled.slice(-decimals) : "";
  const isZero = /^0*$/.test(integer + fraction);
  return { negative: sign === "-" && !isZero, integer, fraction };
}

/** `"1234.5"` → `1.234,50` con 2 decimales. */
export function formatDecimal(value: string, decimals: number): string {
  const { negative, integer, fraction } = roundDecimalString(value, decimals);
  const grouped = integer.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return `${negative ? "-" : ""}${grouped}${fraction ? `,${fraction}` : ""}`;
}

/** Cantidad con los decimales de su unidad: metros con 2, unidades enteras. */
export function formatQuantity(value: string, unitDecimals: number): string {
  return formatDecimal(value, unitDecimals);
}

/** Monto en USD con 2 decimales: `12,50`. */
export function formatUsd(value: string): string {
  return formatDecimal(value, 2);
}

/**
 * Costo en USD (ADR-0004: se guarda con 6 decimales). Se muestra con al menos 2 y hasta
 * 6 decimales, sin los ceros que sobran: `100,00`, `7,25`, `0,125`, `7,253333`.
 */
export function formatCost(value: string): string {
  const full = formatDecimal(value, 6);
  const [integer, fraction = ""] = full.split(",");
  const trimmed = fraction.replace(/0+$/, "").padEnd(2, "0");
  return `${integer},${trimmed}`;
}

/**
 * Lee un número escrito por el usuario (`1.234,56`, `0,30`, `12`) y lo devuelve con punto
 * decimal para la API (`"1234.56"`). Devuelve null si no es un número o si tiene más de
 * `maxDecimals` decimales: no se redondea en silencio (ADR-0004). Un punto solo se toma
 * como separador de miles si agrupa de a tres y no empieza en cero (`1.500`); si no, como
 * decimal (`1.5`, `0.500`).
 */
export function parseDecimalInput(text: string, maxDecimals: number): string | null {
  let value = text.trim().replace(/\s/g, "");
  if (!value) return null;
  let negative = false;
  if (value.startsWith("-")) {
    negative = true;
    value = value.slice(1);
  }
  let normalized: string;
  if (value.includes(",")) {
    if (value.indexOf(",") !== value.lastIndexOf(",")) return null;
    const [intPart, fracPart] = value.split(",");
    if (intPart.includes(".") && !/^[1-9]\d{0,2}(\.\d{3})+$/.test(intPart)) return null;
    normalized = `${intPart.replace(/\./g, "")}.${fracPart}`;
  } else if (/^[1-9]\d{0,2}(\.\d{3})+$/.test(value)) {
    normalized = value.replace(/\./g, "");
  } else {
    normalized = value;
  }
  const match = /^(\d*)(?:\.(\d*))?$/.exec(normalized);
  if (!match || (!match[1] && !match[2])) return null;
  const intPart = (match[1] || "0").replace(/^0+(?=\d)/, "");
  const fracPart = match[2] ?? "";
  if (fracPart.length > maxDecimals) return null;
  const result = fracPart ? `${intPart}.${fracPart}` : intPart;
  return negative && /[1-9]/.test(result) ? `-${result}` : result;
}
