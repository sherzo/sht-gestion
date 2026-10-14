# Contrato de la API: proveedores, compras con gastos y tasa BCV

Prefijo `/api/v1`. Recursos y campos en inglés (ADR-0006). La fuente de verdad
ejecutable es el OpenAPI de FastAPI; este documento fija el comportamiento y la matriz
de permisos que verifican `test_permissions_matrix.py` y `test_no_cost_leak.py`.

Las convenciones de autenticación, errores comunes, fechas, decimales como cadenas y
paginación son las de los contratos de la 1.1a y la 1.1b
(`specs/002-productos-inventario/contracts/api.md`).

## Errores de la etapa

| HTTP | `code` | Cuándo |
|---|---|---|
| 404 | `not_found` | El recurso no existe |
| 409 | `rif_in_use` | RIF de otro proveedor; incluye `supplier_name` (FR-002) |
| 409 | `rate_exists` | Ya hay tasa BCV para esa fecha; se corrige con `PUT` (FR-025) |
| 409 | `exchange_rate_missing` | Compra en Bs o con gastos en Bs sin tasa en o antes de su fecha (FR-012) |
| 409 | `invalid_state` | Editar, confirmar o descartar una compra que no está en borrador; anular una que no está confirmada |
| 409 | `inactive_supplier` | Proveedor inactivo al crear o confirmar (FR-003) |
| 409 | `inactive_products` | Productos inactivos al confirmar; incluye sus `skus` |
| 409 | `template_name_in_use` | Nombre repetido entre los gastos frecuentes activos |
| 422 | `validation_error` | Datos inválidos; `fields` indica cuáles (cantidades por unidad, costos, porcentajes, fecha futura, producto repetido, motivo corto, más de 500 líneas o 20 gastos) |

## Esquemas principales

### Proveedor (`Supplier`)

```json
{
  "id": "0192…",
  "name": "Hidráulica Aragua",
  "rif": "J-12345678-9",
  "phone": "0414-5551234",
  "notes": "Despacha martes y jueves",
  "is_active": true,
  "updated_at": "2026-10-13T14:00:00Z"
}
```

### Tasa (`ExchangeRate`)

```json
{
  "rate_type": "BCV",
  "business_date": "2026-10-13",
  "rate": "36.50000000",
  "created_by": {"id": "0192…", "full_name": "Admin"},
  "created_at": "2026-10-13T12:00:00Z",
  "updated_by": null,
  "updated_at": null
}
```

### Gasto frecuente (`ChargeTemplate`)

```json
{
  "id": "0192…",
  "name": "Comisión de compra",
  "charge_type": "percent",
  "default_value": "10.00",
  "currency": null,
  "is_active": true
}
```

### Compra (`Purchase`), igual para Admin y Almacén

```json
{
  "id": "0192…",
  "number": null,
  "status": "draft",
  "supplier": {"id": "0192…", "name": "Proveedor China", "rif": null},
  "purchase_date": "2026-10-13",
  "supplier_invoice_number": "PI-2026-118",
  "currency": "USD",
  "exchange_rate": "36.50000000",
  "exchange_rate_date": "2026-10-13",
  "notes": null,
  "items": [
    {
      "id": "0192…",
      "line_number": 1,
      "product": {"id": "0192…", "sku": "CON-0004", "name": "Conexión JIC 1/2\"", "unit": {"code": "u", "decimals": 0}},
      "quantity": "60",
      "unit_cost_ves": null,
      "unit_cost_usd": "10.000000",
      "line_total_ves": null,
      "line_total_usd": "600.00",
      "allocated_charges_usd": "270.00",
      "landed_unit_cost_usd": "14.500000"
    }
  ],
  "charges": [
    {"id": "0192…", "line_number": 1, "description": "Comisión de compra", "charge_type": "percent", "percent": "10.00", "amount": null, "currency": null, "amount_usd": "100.00", "allocation_method": "value", "charge_template_id": "0192…"},
    {"id": "0192…", "line_number": 2, "description": "Envío China–Venezuela", "charge_type": "fixed", "percent": null, "amount": "250.00", "currency": "USD", "amount_usd": "250.00", "allocation_method": "value", "charge_template_id": null},
    {"id": "0192…", "line_number": 3, "description": "Entrega al local", "charge_type": "fixed", "percent": null, "amount": "3650.00", "currency": "VES", "amount_usd": "100.00", "allocation_method": "value", "charge_template_id": null}
  ],
  "merchandise_total_usd": "1000.00",
  "merchandise_total_ves": null,
  "charges_total_usd": "450.00",
  "total_usd": "1450.00",
  "created_by": {"id": "0192…", "full_name": "José (Almacén)"},
  "created_at": "2026-10-13T14:00:00Z",
  "updated_at": "2026-10-13T14:05:00Z",
  "confirmed_by": null,
  "confirmed_at": null,
  "void": null,
  "warnings": []
}
```

- `void`, si la compra está anulada: `{"reason", "voided_by", "voided_at"}`.
- `warnings` solo en las respuestas de crear y guardar: `stale_data`,
  `duplicate_invoice` (con el número de la otra compra) y `charges_over_100_percent`.
- Nunca incluye `avg_cost_usd`, `cost_before_usd` ni `cost_after_usd` (R7).

### Entrada de una compra (`PurchaseInput`, para crear y guardar)

```json
{
  "supplier_id": "0192…",
  "purchase_date": "2026-10-13",
  "supplier_invoice_number": "PI-2026-118",
  "currency": "USD",
  "notes": null,
  "items": [{"product_id": "0192…", "quantity": "60", "unit_cost": "10.00"}],
  "charges": [{"description": "Comisión de compra", "charge_type": "percent", "percent": "10", "charge_template_id": "0192…"}],
  "updated_at": "2026-10-13T14:05:00Z"
}
```

- `unit_cost` va en la moneda de la compra: hasta 6 decimales en USD y hasta 2 en Bs.
- El orden de `items` y `charges` define `line_number`.
- `updated_at` solo se envía al guardar; si no coincide, se guarda igual con el aviso
  `stale_data` (R4).

## Endpoints

### Proveedores (RF-13; FR-001 a FR-003)

| Método y ruta | Quién | Descripción |
|---|---|---|
| `GET /suppliers` | Admin, Almacén | Paginado; `q` (nombre o RIF) e `is_active` |
| `POST /suppliers` | Admin, Almacén | `{name, rif?, phone?, notes?}` → 201; `rif_in_use` |
| `GET /suppliers/{id}` | Admin, Almacén | |
| `PATCH /suppliers/{id}` | Admin, Almacén | `{name?, rif?, phone?, notes?, is_active?}`; `rif_in_use` |

### Tasa BCV (RF-17, RN-15; FR-025 a FR-028)

| Método y ruta | Quién | Descripción |
|---|---|---|
| `GET /exchange-rates` | Admin | Histórico paginado, de la más reciente a la más antigua |
| `POST /exchange-rates` | Admin | `{business_date, rate}` → 201; `rate_exists`; fecha futura → 422 |
| `PUT /exchange-rates/{business_date}` | Admin | `{rate}`; corrige y audita `exchange_rate.corrected`; 404 si no existe |
| `GET /exchange-rates/applicable?date=` | Admin, Almacén | `{rate, business_date}` de la tasa aplicable a la fecha, o 404 |

### Gastos frecuentes (RF-14; FR-032)

| Método y ruta | Quién | Descripción |
|---|---|---|
| `GET /charge-templates` | Admin, Almacén | Activos; `?include_inactive=true` solo para el Admin |
| `POST /charge-templates` | Admin | `{name, charge_type, default_value?, currency?}` → 201; `template_name_in_use` |
| `PATCH /charge-templates/{id}` | Admin | `{name?, default_value?, currency?, is_active?}`; `charge_type` no cambia (422) |

### Compras (RF-14 a RF-16, RN-09, RN-14, RN-20; FR-004 a FR-021, FR-029 a FR-031)

| Método y ruta | Quién | Descripción |
|---|---|---|
| `GET /purchases` | Admin, Almacén | Paginado. Filtros: `supplier_id`, `from`, `to` (fechas de factura), `status`, `product_id`, `q` (número o factura del proveedor). Resumen: número, fecha, proveedor, moneda, `total_usd`, estado y cantidad de líneas. Más reciente primero |
| `POST /purchases` | Admin, Almacén | `PurchaseInput` → 201 `Purchase` en `draft`; `inactive_supplier`, `exchange_rate_missing` |
| `GET /purchases/{id}` | Admin, Almacén | `Purchase` |
| `PUT /purchases/{id}` | Admin, Almacén | Reemplaza el borrador completo y recalcula (R4); `invalid_state` |
| `DELETE /purchases/{id}` | Admin, Almacén | Descarta un borrador → 204; `invalid_state` |
| `POST /purchases/{id}/confirm` | Admin, Almacén | Confirma (R3) → 200 `Purchase`. Para el Admin agrega `cost_changes: [{product_id, sku, cost_before_usd, cost_after_usd}]`. Errores: `invalid_state`, `inactive_supplier`, `inactive_products`, `exchange_rate_missing` |
| `GET /purchases/{id}/void-preview` | Admin | `{items: [{product_id, sku, stock_before, stock_after, cost_before_usd, cost_after_usd, keeps_cost}]}` (FR-019); `invalid_state` |
| `POST /purchases/{id}/void` | Admin | `{reason}` (5–500 caracteres) → 200 `Purchase` con `void` y `alerts_created`; `invalid_state` |

### Alertas (RN-14; FR-018)

| Método y ruta | Quién | Descripción |
|---|---|---|
| `GET /alerts` | Admin | `?status=open\|resolved` (por defecto `open`), más recientes primero |
| `POST /alerts/{id}/resolve` | Admin | Marca revisada; audita `alert.resolved`; `invalid_state` si ya estaba resuelta |

### Cambios en endpoints existentes

- `GET /inventory/summary` (Admin) suma `open_alerts` y `draft_purchases`; para el
  Almacén suma `draft_purchases`.
- `GET /products/{id}/movements`: los movimientos de compra y de anulación traen
  `reference_type = 'purchase_item'` y `purchase: {id, number}` para enlazar con la
  compra (FR-021). El costo antes y después sigue siendo solo para el Admin.

## Matriz de permisos de la etapa

Se agrega a `test_permissions_matrix.py`. Todos los endpoints niegan el acceso sin
sesión (`not_authenticated`) y con contraseña temporal (`password_change_required`).

| Endpoint | Admin | Vendedor | Almacén |
|---|:-:|:-:|:-:|
| `GET/POST /suppliers`, `GET/PATCH /suppliers/{id}` | ✅ | ❌ | ✅ |
| `GET/POST /exchange-rates`, `PUT /exchange-rates/{date}` | ✅ | ❌ | ❌ |
| `GET /exchange-rates/applicable` | ✅ | ❌ | ✅ |
| `GET /charge-templates` | ✅ | ❌ | ✅ (solo activos) |
| `POST/PATCH /charge-templates` | ✅ | ❌ | ❌ |
| `GET/POST /purchases`, `GET/PUT/DELETE /purchases/{id}`, `confirm` | ✅ | ❌ | ✅ (sin `cost_changes`) |
| `void-preview`, `void` | ✅ | ❌ | ❌ |
| `GET /alerts`, `resolve` | ✅ | ❌ | ❌ |
