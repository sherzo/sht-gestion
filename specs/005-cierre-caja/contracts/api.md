# Contrato de la API: caja, egresos, cierre y cuadre

Prefijo `/api/v1`. Recursos y campos en inglés (ADR-0006). La fuente de verdad
ejecutable es el OpenAPI de FastAPI. Este documento fija el comportamiento y la matriz
de permisos que verifican `test_permissions_matrix.py` y `test_no_cost_leak.py`.

Las convenciones (autenticación, errores comunes, fechas, decimales como cadenas,
paginación y la cabecera `X-Device-Token`) son las de
`specs/004-ventas-multimoneda/contracts/api.md`.

## Errores de la etapa

| HTTP | `code` | Cuándo |
|---|---|---|
| 404 | `not_found` | Caja o egreso inexistente; para el Vendedor, una caja que no es la abierta de su equipo ni un cierre suyo de hoy |
| 409 | `cash_session_unavailable` | La caja indicada no existe o no es del equipo que envía la operación |
| 409 | `cash_session_closed` | La caja ya está cerrada: segundo cierre, egreso o venta creados después del cierre (R7), o anulación de un egreso con la caja cerrada |
| 409 | `cash_session_required` | Anular una venta cuya caja está cerrada sin estar en un equipo registrado, vigente y con caja abierta (R8) |
| 409 | `insufficient_cash` | El egreso en efectivo supera el esperado del método; incluye `available` y `currency`. Los demás métodos no tienen tope |
| 409 | `invalid_state` | Anular un egreso ya anulado |
| 422 | `validation_error` | Método inexistente, referencia faltante en un método que la exige, monto ≤ 0, motivo u observación fuera de longitud, conteos incompletos, repetidos o negativos, observación faltante con diferencias o en el cierre fuera del equipo |

Las operaciones de cola rechazadas guardan su respuesta y la repiten en un reenvío (R4
de la 1.3).

## Operaciones de la cola (`POST /sync/operations`)

### `cash_outflow.create` (R3)

```json
{
  "id": "0192…",
  "cash_session_id": "…",
  "method": "cash_usd",
  "amount": "5.00",
  "reason": "Compra de botellones de agua",
  "reference": null
}
```

- `method`: cualquier método del catálogo. `reference` (1–60) es obligatoria en los que la
  exigen (todos excepto el efectivo, RF-24).
- Solo en efectivo el monto no puede superar el esperado del método (`insufficient_cash`).

Respuesta: `CashOutflow`. Queda a nombre del usuario de la sesión, con `occurred_at` =
`created_at` de la operación.

### `cash_session.close` (R4)

```json
{
  "cash_session_id": "…",
  "counts": [
    {"method": "cash_ves", "device_expected": "500.00", "counted": "500.00"},
    {"method": "mobile_payment", "device_expected": "730.00", "counted": "730.00"},
    {"method": "pos_card", "device_expected": "0.00", "counted": "0.00"},
    {"method": "cash_usd", "device_expected": "67.70", "counted": "66.70"},
    {"method": "zelle", "device_expected": "0.00", "counted": "0.00"},
    {"method": "binance_usdt", "device_expected": "0.00", "counted": "0.00"}
  ],
  "note": "Faltó 1 USD; se revisa mañana"
}
```

- `counts` debe traer exactamente los seis métodos del catálogo, sin repetir. `counted`
  ≥ 0 con como máximo 2 decimales.
- `note` se exige según las diferencias que vio el equipo (`counted − device_expected`);
  si el esperado del servidor da otra diferencia, el cierre se guarda igual con la alerta
  `expected_mismatch`.
- `note` es obligatoria (5–500) si algún `counted − device_expected` es distinto de cero.
- Respuesta: `CashSessionDetail` de la caja cerrada, más `alerts_created: [type]`.

## Esquemas

### Egreso (`CashOutflow`)

```json
{
  "id": "…", "cash_session_id": "…",
  "method": "cash_usd", "currency": "USD", "amount": "5.00",
  "reason": "Compra de botellones de agua", "reference": null,
  "created_by": {"id": "…", "full_name": "…"}, "occurred_at": "…",
  "void": null
}
```

`void` = `{reason, voided_by: {id, full_name}, voided_at}` cuando está anulado.

### Fila del cuadre (`ReconciliationRow`)

```json
{
  "method": "cash_usd", "method_name": "Efectivo USD", "currency": "USD",
  "opening": "20.00", "collected": "50.00", "change_given": "2.30",
  "refunded": "0.00", "change_recovered": "0.00", "outflows": "0.00",
  "expected": "67.70",
  "device_expected": "67.70", "counted": "66.70", "difference": "-1.00"
}
```

- En una caja abierta, `device_expected`, `counted` y `difference` son `null`.
- En una cerrada, `expected` es el guardado en `cash_count`, no un recálculo. Los
  componentes (`collected`, …) se calculan sin los movimientos posteriores al cierre.

### Resumen de caja (`CashSessionSummary`)

```json
{
  "id": "…",
  "device": {"id": "…", "name": "Mostrador principal", "series": "A"},
  "business_date": "2026-10-15", "status": "closed",
  "opened_by": {"id": "…", "full_name": "…"}, "opened_at": "…",
  "closed_by": {"id": "…", "full_name": "…"}, "closed_at": "…",
  "closed_outside_device": false,
  "has_differences": true,
  "opened_on_previous_day": false
}
```

`opened_on_previous_day` es true si la caja sigue abierta y su fecha de negocio no es la
de hoy (R5).

### Detalle de caja (`CashSessionDetail`)

Extiende `CashSessionSummary` con:

```json
{
  "opening_float_ves": "500.00", "opening_float_usd": "20.00",
  "closed_from_device": {"id": "…", "name": "…"},
  "closing_note": "…",
  "reconciliation": [ReconciliationRow, "… seis filas en el orden del catálogo"],
  "movements": [
    {"sale": {"id": "…", "number": "A-000012"}, "kind": "sale_payment",
     "method": "mobile_payment", "currency": "VES", "amount": "730.00",
     "reference": "004512", "occurred_at": "…", "after_close": false}
  ],
  "outflows": [CashOutflow],
  "voided_after_close": [
    {"sale": {"id": "…", "number": "A-000001"}, "voided_at": "…",
     "refund_cash_session": {"id": "…", "device": {"id": "…", "name": "…"}}}
  ],
  "post_close_operations": [
    {"type": "sale", "id": "…", "number": "A-000031", "occurred_at": "…"},
    {"type": "cash_outflow", "id": "…", "occurred_at": "…", "method": "cash_ves", "amount": "…"}
  ]
}
```

- `movements` incluye todos los pagos con `cash_session_id` = la caja. Eso cubre las
  devoluciones de ventas de otras cajas anuladas aquí: su `sale` es la venta original.
  El equipo los usa para calcular el cuadre con `computeReconciliation` (FR-007).
- `after_close = true` en los movimientos de operaciones posteriores al cierre (R7): las
  que el servidor registró después de `closed_recorded_at`.
- `voided_after_close`: ventas de esta caja con `sale_void.voided_at` posterior a
  `closed_recorded_at`.
- La caja no tiene costos ni márgenes: el mismo esquema sirve para todos los roles.

### Cambios en esquemas existentes

- `Device.open_cash_session` suma `opening_float_ves`, `opening_float_usd` y
  `opened_on_previous_day`.
- `SaleAdmin.void` / `SaleSeller.void` suma `refund_cash_session: {id, device: {id,
  name}}` (FR-023).

## Endpoints

### Cajas (FR-018, FR-024, FR-025; R6, R9)

| Método y ruta | Quién | Descripción |
|---|---|---|
| `GET /cash-sessions` | Admin, Vendedor | Paginado, más recientes primero. Admin: `from`, `to` (fecha de negocio), `device_id`, `opened_by`, `closed_by`, `status` (`open`, `closed`), `with_differences` (bool). Vendedor: solo la caja abierta del equipo de `X-Device-Token` (si la manda) y las cajas que él cerró hoy; los filtros se ignoran. → página de `CashSessionSummary` |
| `GET /cash-sessions/{id}` | Admin, Vendedor | `CashSessionDetail`; 404 para el Vendedor fuera de lo que puede ver |
| `POST /cash-sessions/{id}/close` | Admin | Cierre desde otro equipo o navegador: `{counts: [{method, counted}], note}` con los seis métodos y observación obligatoria. `X-Device-Token` opcional (registra `closed_from_device`). → `CashSessionDetail` con `closed_outside_device = true`; audita `cash_session.closed`; alertas como en la cola. `cash_session_closed` si ya estaba cerrada |

### Egresos (FR-003; R3)

| Método y ruta | Quién | Descripción |
|---|---|---|
| `POST /cash-outflows/{id}/void` | Admin | `{reason}` (5–200) → `CashOutflow` anulado; audita `cash_outflow.voided`. `cash_session_closed` si la caja está cerrada e `invalid_state` si ya estaba anulado |

Los egresos se crean por la cola (`cash_outflow.create`) y se consultan en el detalle de
la caja.

### Ventas (cambio; FR-020 a FR-023; R8)

| Método y ruta | Quién | Descripción |
|---|---|---|
| `POST /sales/{id}/void` | Admin (+ `X-Device-Token` opcional) | Igual que en la 1.3. Si la caja de la venta está cerrada, exige un equipo vigente con caja abierta y registra la devolución en esa caja; si no, 409 `cash_session_required`. Audita `sale.voided` con `refund_cash_session_id` y `refund_device_id` |

### Cambios en endpoints existentes

- `GET /alerts`: tipos `cash_difference`, `expected_mismatch` y `post_close_operation`,
  con `cash_session: {id, device_name}` para enlazar.
- `POST /sync/operations`: tipos `cash_outflow.create` y `cash_session.close`. Una
  `sale.create` para una caja cerrada se acepta si se creó antes del cierre (alerta
  `post_close_operation`, R7); si no, 409 `cash_session_closed`.
- `GET /devices/current`: campos nuevos de `open_cash_session`.

## Matriz de permisos de la etapa

Se agrega a `test_permissions_matrix.py`. Todos los endpoints niegan el acceso sin
sesión (`not_authenticated`) y con contraseña temporal (`password_change_required`).

| Endpoint u operación | Admin | Vendedor | Almacén |
|---|:-:|:-:|:-:|
| `POST /sync/operations` `cash_outflow.create` | ✅ | ✅ | ❌ |
| `POST /sync/operations` `cash_session.close` (caja del equipo) | ✅ | ✅ | ❌ |
| `GET /cash-sessions`, `GET /cash-sessions/{id}` | ✅ | ✅ (caja abierta de su equipo y sus cierres de hoy) | ❌ |
| `POST /cash-sessions/{id}/close` | ✅ | ❌ | ❌ |
| `POST /cash-outflows/{id}/void` | ✅ | ❌ | ❌ |
