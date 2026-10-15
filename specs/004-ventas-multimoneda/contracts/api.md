# Contrato de la API: ventas multimoneda, pagos mixtos, descuentos y apertura de caja

Prefijo `/api/v1`. Recursos y campos en inglés (ADR-0006). La fuente de verdad
ejecutable es el OpenAPI de FastAPI. Este documento fija el comportamiento y la matriz
de permisos que verifican `test_permissions_matrix.py` y `test_no_cost_leak.py`.

Las convenciones de autenticación, errores comunes, fechas, decimales como cadenas y
paginación son las de los contratos de la 1.1a y la 1.1b
(`specs/002-productos-inventario/contracts/api.md`).

**Cabecera del equipo**: las operaciones de mostrador (`/sync/operations`,
`/devices/current` y `POST /discount-authorizations`) exigen `X-Device-Token`. Sin
ella, o con un token desconocido o de un equipo revocado, responden 403
`device_required` o `device_revoked`.

## Errores de la etapa

| HTTP | `code` | Cuándo |
|---|---|---|
| 403 | `device_required` | Falta `X-Device-Token` o no corresponde a un equipo |
| 403 | `device_revoked` | Equipo revocado (operación creada después de la revocación) |
| 403 | `pin_invalid` / 423 `pin_locked` | PIN de la autorización (etapa 1.1a) |
| 404 | `not_found` | Recurso inexistente, o venta ajena o de otro día para el Vendedor |
| 409 | `cash_session_open` | Ya hay una caja abierta en el equipo; incluye `opened_by` y `opened_at` |
| 409 | `cash_session_unavailable` | La caja de la venta no existe, no es del equipo o no está abierta |
| 409 | `exchange_rate_missing` | No hay ninguna tasa BCV cargada (apertura) |
| 409 | `sequence_conflict` | Correlativo de la serie ya usado por otra operación (R5) |
| 409 | `invalid_state` | Anular una venta ya anulada; decidir una autorización que no está pendiente |
| 409 | `operation_type_unknown` | Tipo de operación de cola no admitido |
| 422 | `validation_error` | Datos inválidos; `fields` indica cuáles: cantidades por unidad, descuentos fuera de rango, referencia faltante, pagos que no cubren, vuelto mayor que el excedente, límites de R16, documento del cliente |

Una operación de cola rechazada guarda su respuesta: reenviarla devuelve el mismo
código y cuerpo (R4).

## Esquemas principales

### Equipo (`Device`)

```json
{
  "id": "0192…",
  "name": "Mostrador principal",
  "series": "A",
  "last_sequence_number": 123,
  "registered_by": {"id": "…", "full_name": "Sherzo Flórez"},
  "registered_at": "2026-10-15T13:00:00Z",
  "revoked_at": null,
  "open_cash_session": {"id": "…", "opened_by": {"id": "…", "full_name": "…"}, "opened_at": "…", "business_date": "2026-10-15"}
}
```

`POST /devices` agrega `token` (solo en esa respuesta).

### Operación de cola (`OutboxOperationIn`)

```json
{
  "id": "0192…",
  "operation_type": "sale.create",
  "schema_version": 1,
  "created_at": "2026-10-15T14:03:11-04:00",
  "payload": { }
}
```

**`cash_session.open`**: `payload = {id, opening_float_ves, opening_float_usd}`.
Respuesta: `CashSession`.

**`sale.create`**: `payload` es `SaleInput`. Respuesta: `SaleSeller` o `SaleAdmin`,
según el rol de quien envía, más `alerts_created: [type]` y `warnings` (por ejemplo,
`negative_stock`).

### Entrada de una venta (`SaleInput`)

```json
{
  "id": "0192…",
  "sequence_number": 124,
  "cash_session_id": "…",
  "seller_id": "…",
  "occurred_at": "2026-10-15T14:03:00-04:00",
  "exchange_rate": "36.50000000",
  "exchange_rate_date": "2026-10-15",
  "customer": {"id": "…", "name": "Taller El Tornillo", "document_id": "J-40123456-7", "phone": "0414-5550000"},
  "customer_id": null,
  "items": [
    {"id": "…", "product_id": "…", "quantity": "0.30", "entered_unit": "cm", "unit_price_usd": "4.00",
     "discount": {"type": "percent", "value": "10.00", "authorization_id": "…"}}
  ],
  "discount": {"type": "amount", "value": "5.00", "authorization_id": null},
  "payments": [
    {"method": "cash_usd", "amount": "20.00", "reference": null},
    {"method": "mobile_payment", "amount": "730.00", "reference": "004512"}
  ],
  "change": [{"method": "cash_ves", "amount": "83.95", "reference": null}],
  "device_total_usd": "50.00"
}
```

- `customer` (cliente nuevo o conocido, R11) y `customer_id` son excluyentes, y ambos
  opcionales.
- `exchange_rate` y su fecha son las que usó el equipo y se guardan tal cual (RN-05).
  El servidor no las reemplaza por la tasa vigente.
- `authorization_id` es opcional. Si el vendedor es Vendedor y falta o no coincide, la
  venta se registra igual con `needs_review` (R8).
- `seller_id` debe ser un usuario Admin o Vendedor. Si está desactivado, la venta se
  registra con la alerta `inactive_user_sync`.

### Venta (`SaleSeller`; `SaleAdmin` agrega los costos)

```json
{
  "id": "…", "number": "A-000124", "status": "registered", "needs_review": false,
  "device": {"id": "…", "name": "Mostrador principal"},
  "cash_session_id": "…",
  "seller": {"id": "…", "full_name": "…"},
  "customer": {"id": "…", "name": "…", "document_id": "J-40123456-7", "phone": "…"},
  "occurred_at": "…", "business_date": "2026-10-15", "synced_at": "…",
  "exchange_rate": "36.50000000", "exchange_rate_date": "2026-10-15",
  "items": [
    {"line_number": 1, "product": {"id": "…", "sku": "MAN-0001", "name": "…", "unit": {"code": "metro", "decimals": 2}},
     "quantity": "0.30", "entered_unit": "cm", "unit_price_usd": "4.00", "server_price_usd": null,
     "line_subtotal_usd": "1.20",
     "item_discount": {"type": "percent", "value": "10.00", "amount_usd": "0.12", "authorized_by": {"id": "…", "full_name": "…"}, "method": "pin"},
     "allocated_sale_discount_usd": "0.00", "line_total_usd": "1.08"}
  ],
  "subtotal_usd": "…", "discount": null, "discount_usd": "0.00",
  "total_usd": "…", "total_ves": "…", "paid_usd": "…", "change_usd": "…", "overpaid_usd": "0.00",
  "payments": [{"kind": "sale_payment", "method": "cash_usd", "currency": "USD", "amount": "20.00", "amount_usd": "20.00", "reference": null}],
  "void": null
}
```

- `SaleAdmin` agrega, por línea, `unit_cost_usd` y `margin_usd` (`line_total_usd −
  unit_cost_usd × quantity`, nulo sin costo) y, por venta, `cost_usd` y `margin_usd`.
  El Vendedor nunca recibe estos campos (SC-006).
- `void` lleva `{reason, voided_by, voided_at}` cuando la venta está anulada; los pagos
  de la anulación aparecen con `kind` `void_refund` y `void_change`.

### Autorización de descuento (`DiscountAuthorization`)

```json
{
  "id": "…", "sale_id": "…", "sale_item_id": "…",
  "product": {"id": "…", "sku": "CON-0012", "name": "…"},
  "discount_type": "percent", "requested_value": "10.00", "discount_value": "10.00", "base_usd": "20.00", "discount_usd": "2.00",
  "method": "request", "status": "pending",
  "requested_by": {"id": "…", "full_name": "…"}, "requested_at": "…",
  "device": {"id": "…", "name": "Mostrador principal"},
  "decided_by": null, "decided_at": null, "rejection_reason": null
}
```

## Endpoints

### Equipos (FR-001 a FR-004; R3)

| Método y ruta | Quién | Descripción |
|---|---|---|
| `POST /devices` | Admin | `{name}` → 201 `Device` con `token`. Audita `device.registered` |
| `GET /devices` | Admin | Todos, vigentes primero |
| `POST /devices/{id}/revoke` | Admin | → `Device`; audita `device.revoked`; `invalid_state` si ya estaba revocado |
| `GET /devices/current` | Admin, Vendedor (+ `X-Device-Token`) | `Device` del token con su caja abierta y `last_sequence_number` |

### Cola de salida (FR-017, FR-018; R4)

| Método y ruta | Quién | Descripción |
|---|---|---|
| `POST /sync/operations` | Admin, Vendedor (+ `X-Device-Token`) | `OutboxOperationIn` → 200 con el resultado. Idempotente por `id`; los rechazos (409, 422) también se guardan y se repiten |

### Tasa (cambio)

| Método y ruta | Quién | Descripción |
|---|---|---|
| `GET /exchange-rates/applicable?date=` | Admin, **Vendedor**, Almacén | Se abre al Vendedor (R13) |

### Clientes (FR-019; R11)

| Método y ruta | Quién | Descripción |
|---|---|---|
| `GET /customers?q=` | Admin, Vendedor | Por documento (exacto, normalizado) o nombre (contiene, sin acentos); máximo 20 |

### Autorizaciones de descuento (FR-023 a FR-027; R8)

| Método y ruta | Quién | Descripción |
|---|---|---|
| `POST /discount-authorizations` | Vendedor (+ `X-Device-Token`) | `{method: "pin", admin_username, pin, sale_id, sale_item_id?, product_id?, discount_type, discount_value, base_usd}` → 201 `approved`; o `{method: "request", …}` sin PIN → 201 `pending`. Audita `discount_authorization.requested` (y `auth.pin_verified` con PIN) |
| `GET /discount-authorizations/{id}` | Admin; Vendedor (solo las suyas) | Estado para la espera del vendedor |
| `GET /discount-authorizations?status=pending` | Admin | Solicitudes por decidir, más antiguas primero |
| `POST /discount-authorizations/{id}/approve` | Admin | `{discount_value?}` (por defecto el pedido; del mismo tipo, > 0 y ≤ el pedido, 422 si no) → `approved` con `discount_usd` recalculado; audita el valor pedido y el aprobado; `invalid_state` |
| `POST /discount-authorizations/{id}/reject` | Admin | `{reason?}` → `rejected`; audita; `invalid_state` |

### Ventas (FR-041 a FR-049; R10, R12)

| Método y ruta | Quién | Descripción |
|---|---|---|
| `GET /sales` | Admin, Vendedor | Paginado, más reciente primero. Admin: `from`, `to` (fecha de negocio), `q` (número), `seller_id`, `customer_id`, `device_id`, `status` (`registered`, `voided`, `needs_review`). Vendedor: siempre sus ventas de hoy; los filtros de fecha y vendedor se ignoran. Resumen: número, fecha y hora, vendedor, cliente, `total_usd`, `total_ves`, estado |
| `GET /sales/{id}` | Admin, Vendedor | `SaleAdmin` o `SaleSeller`; 404 para el Vendedor si no es suya del día |
| `POST /sales/{id}/void` | Admin | `{reason}` (5–500) → `SaleAdmin` anulada; audita `sale.voided`; `invalid_state` |

### Cambios en endpoints existentes

- `GET /alerts`: tipos nuevos (R6). Las alertas de venta traen
  `sale: {id, number}` para enlazar.
- `GET /inventory/summary` (Admin) suma `pending_discount_requests`.
- `GET /products/{id}/movements`: las salidas `sale` y los reversos `sale_void` traen
  `reference_type = 'sale_item'` y `sale: {id, number}` (FR-048).

## Matriz de permisos de la etapa

Se agrega a `test_permissions_matrix.py`. Todos los endpoints niegan el acceso sin
sesión (`not_authenticated`) y con contraseña temporal (`password_change_required`).

| Endpoint | Admin | Vendedor | Almacén |
|---|:-:|:-:|:-:|
| `POST /devices`, `GET /devices`, `POST /devices/{id}/revoke` | ✅ | ❌ | ❌ |
| `GET /devices/current` | ✅ | ✅ | ❌ |
| `POST /sync/operations` | ✅ | ✅ | ❌ |
| `GET /exchange-rates/applicable` | ✅ | ✅ | ✅ |
| `GET /customers` | ✅ | ✅ | ❌ |
| `POST /discount-authorizations` | ❌ (no la necesita, R8) | ✅ | ❌ |
| `GET /discount-authorizations/{id}` | ✅ | ✅ (solo las suyas) | ❌ |
| `GET /discount-authorizations`, `POST …/approve`, `POST …/reject` | ✅ | ❌ | ❌ |
| `GET /sales`, `GET /sales/{id}` | ✅ | ✅ (sus ventas de hoy, sin costos) | ❌ |
| `POST /sales/{id}/void` | ✅ | ❌ | ❌ |
