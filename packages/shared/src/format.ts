// Formato de fechas de la interfaz (RNF-07): dd/mm/aaaa hh:mm en America/Caracas.

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
