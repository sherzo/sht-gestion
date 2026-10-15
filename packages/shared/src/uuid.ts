// UUIDv7 generado en el equipo (RFC 9562; ADR-0003, research R4 de la etapa 1.3): es la
// clave de idempotencia de cada operación de la cola y el id de ventas, líneas, cajas y
// clientes creados en el mostrador. Ordenado por tiempo, sin dependencias.

/** Devuelve un UUIDv7: 48 bits de milisegundos, versión 7, variante 10 y el resto al azar. */
export function uuidv7(): string {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  const millis = Date.now();
  // 48 bits del tiempo en milisegundos, big-endian (sin operadores de bits: superan 32 bits).
  let rest = millis;
  for (let i = 5; i >= 0; i--) {
    bytes[i] = rest % 256;
    rest = Math.floor(rest / 256);
  }
  bytes[6] = (bytes[6] & 0x0f) | 0x70; // versión 7
  bytes[8] = (bytes[8] & 0x3f) | 0x80; // variante 10
  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}
