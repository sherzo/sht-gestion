# ADR-0004: Dinero, cantidades y redondeo

- **Estado:** Aceptada
- **Fecha:** 2026-10-05
- **Requisitos relacionados:** RN-01, RN-02, RN-04, RN-05, RN-06, RN-09, RF-05, RF-15, RF-21, RF-25; principios I y VII

## Contexto

Los montos y las cantidades se calculan en dos lugares: en el navegador (TypeScript,
para vender sin conexión) y en el servidor (Python, autoridad). Ambos deben dar
exactamente el mismo resultado. El principio I prohíbe el punto flotante.

## Decisión

### Tipos

| Dato | Postgres | Python | TypeScript |
|---|---|---|---|
| Precios de venta y montos en USD | `NUMERIC(14,2)` | `Decimal` | `Decimal` (decimal.js) |
| Costos en USD (incluye promedio ponderado) | `NUMERIC(18,6)` | `Decimal` | — (no viaja al mostrador) |
| Montos en Bs | `NUMERIC(16,2)` | `Decimal` | `Decimal` |
| Tasa BCV | `NUMERIC(18,8)` | `Decimal` | `Decimal` |
| Cantidades y stock | `NUMERIC(14,2)` | `Decimal` | `Decimal` |

- En JSON, todo valor decimal viaja como **cadena** (`"12.50"`), nunca como número.
- Cada unidad de medida declara cuántos decimales admite: `metro` 2 (precisión de
  centímetro, RF-05) y `unidad` 0. El servidor rechaza cantidades con más decimales de
  los permitidos.
- Ingreso en centímetros (RF-21): `cm ÷ 100`, exacto. Si la cantidad resultante tiene
  más de 2 decimales en metros, se rechaza; no se redondea en silencio.

### Redondeo

- Modo único: **mitad hacia arriba** (`ROUND_HALF_UP`), configurado explícitamente en
  Python y en decimal.js. No se usa el redondeo por defecto de Python
  (`ROUND_HALF_EVEN`).
- Se redondea en puntos definidos, no en cada operación intermedia:

| Cálculo | Fórmula | Redondeo |
|---|---|---|
| Subtotal de línea (USD) | precio unitario × cantidad | 2 decimales |
| Descuento porcentual (USD) | base × porcentaje | 2 decimales |
| Total de la venta (USD) | Σ subtotales − descuentos | ya exacto a 2 decimales |
| Total en Bs (RN-02) | total USD × tasa | 2 decimales, sobre el **total**, no sumando líneas |
| Precio unitario en Bs (pantalla y catálogo) | precio USD × tasa | 2 decimales |
| USD cubiertos por un pago en Bs (RN-06) | monto Bs ÷ tasa de la venta | 2 decimales |
| Monto en Bs para cubrir un saldo en USD | saldo USD × tasa | 2 decimales |
| Vuelto en Bs | excedente USD × tasa | 2 decimales |
| Costo de compra en Bs a USD (RF-15) | costo Bs ÷ tasa de la compra | 6 decimales |
| Costo promedio ponderado (RN-09) | (stock × costo + cantidad × costo compra) ÷ (stock + cantidad) | 6 decimales |

- USDT, Zelle y efectivo USD cubren su monto 1:1 en USD (RN-04).
- La suma de los precios en Bs de cada línea puede diferir en céntimos del total en Bs.
  Prevalece el total; la pantalla lo muestra así.

### Un solo punto de implementación

- Backend: un módulo de dominio de dinero (por ejemplo `backend/app/domain/money.py`).
- Frontend: `packages/shared/src/money.ts`, usado por la app interna y por el catálogo.
- Ningún otro código multiplica, divide ni redondea montos por su cuenta.

### Casos de prueba compartidos (principio VII)

- `shared/test-vectors/money.json` contiene casos con entradas y resultados esperados:
  líneas por metro y por unidad, ingreso en cm, conversión a Bs, pagos mixtos, vuelto y
  casos borde de redondeo.
- La suite de Python y la de TypeScript ejecutan **los mismos casos**. Si una de las dos
  difiere, la CI falla.

### Pendiente de definir (pregunta abierta en PRD §10)

- El costo promedio cuando el stock previo es cero o negativo (por ventas sin conexión).
  La fórmula no aplica en ese caso; se decide antes de especificar la etapa 1.2.

## Alternativas consideradas

- **Enteros en centavos:** exactos, pero incómodos con tasas de 8 decimales, costos de 6
  y cantidades fraccionadas, y propensos a errores de escala.
- **Redondeo bancario (`ROUND_HALF_EVEN`):** menos sesgo estadístico, pero contraintuitivo
  para el vendedor y el cliente en montos individuales.
- **Redondear en Bs línea por línea y sumar:** la suma podría no coincidir con
  "total USD × tasa", que es la regla RN-02.

## Consecuencias

- La misma venta da el mismo resultado en el equipo y en el servidor, verificado por la CI.
- Cambiar una regla de redondeo es cambiar un módulo y sus casos de prueba.
- Las escalas de la tabla se confirman en `docs/modelo-de-datos.md`; ampliarlas después
  es una migración sencilla.
