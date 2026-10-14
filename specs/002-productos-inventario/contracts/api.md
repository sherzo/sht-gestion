# Contrato de la API: productos, categorías e inventario

Prefijo `/api/v1`. Recursos y campos en inglés (ADR-0006). La fuente de verdad
ejecutable es el OpenAPI de FastAPI; este documento fija el comportamiento y la matriz
de permisos que verifican `test_permissions_matrix.py` y `test_no_cost_leak.py`.
Convenciones de autenticación, errores comunes y fechas: contrato de la etapa 1.1a
(`specs/001-usuarios-autenticacion-permisos/contracts/api.md`).

## Convenciones de la etapa

- **Decimales como cadenas** (ADR-0004): `"12.50"`, `"0.30"`, `"3.250000"`. Las
  entradas con más decimales de los permitidos se rechazan con 422, nunca se redondean.
- **Esquemas por rol** (research R6): las respuestas de producto, kardex y conteo usan
  un esquema según el rol del usuario leído de la base. Los campos marcados abajo con
  🅰 solo existen para Admin, y los marcados con 🆅 solo para Admin y Vendedor.
- **Paginación:** `?page=1&page_size=50` (máximo 100); respuesta
  `{"items": […], "total": n, "page": 1, "page_size": 50}`.

### Errores de la etapa

| HTTP | `code` | Cuándo |
|---|---|---|
| 404 | `not_found` | El recurso no existe |
| 409 | `product_has_movements` | Cambiar categoría o unidad de un producto con movimientos (FR-004) |
| 409 | `prefix_in_use` | Cambiar el prefijo de una categoría con productos, o prefijo repetido |
| 409 | `cost_locked` | Costo inicial de un producto con compras confirmadas (FR-013) |
| 409 | `max_photos` | Más de 5 fotos activas (FR-008) |
| 409 | `negative_stock` | Ajuste manual o aprobación que dejaría el stock negativo (FR-019) |
| 409 | `invalid_state` | Operación no permitida en el estado actual de la solicitud o del conteo |
| 409 | `product_in_open_count` | El producto ya está en otro conteo abierto (FR-024) |
| 409 | `uncounted_lines` | Aplicar un conteo con productos sin anotar sin confirmarlo; incluye `uncounted` |
| 409 | `not_publishable` | Publicar un producto inactivo o sin precio (FR-009) |
| 413 | `photo_too_large` | Foto de más de 5 MB |
| 415 | `photo_unsupported` | La foto no es JPG, PNG ni WebP válida |
| 422 | `validation_error` | Datos inválidos; `fields` indica cuáles (cantidades, atributos, unidades) |

## Esquemas principales

### Producto (`ProductAdmin` / `ProductSeller` / `ProductWarehouse`)

```json
{
  "id": "0192…",
  "sku": "MAN-0001",
  "name": "Manguera hidráulica R2 1/2\"",
  "description": "Dos mallas de acero",
  "category": {"id": "0192…", "name": "Mangueras", "sku_prefix": "MAN"},
  "unit": {"id": "0192…", "code": "m", "name": "metro", "decimals": 2},
  "attributes": {"hose_type": "R2", "diameter": "1/2\"", "material": "Caucho"},
  "stock": "35.50",
  "min_stock": "10.00",
  "is_low_stock": false,
  "is_active": true,
  "is_published": true,
  "photos": [{"id": "0192…", "url": "https://…/products/…/….webp", "sort_order": 0}],
  "sale_price_usd": "12.50",
  "avg_cost_usd": "7.250000",
  "cost_locked": false,
  "has_movements": true,
  "updated_at": "2026-10-08T14:00:00Z"
}
```

- 🆅 `sale_price_usd` (nulo si no tiene).
- 🅰 `avg_cost_usd` (nulo si no tiene), `cost_locked`.
- El Vendedor solo recibe productos activos.

### Movimiento (`StockMovement`)

```json
{
  "id": "0192…",
  "occurred_at": "2026-10-08T14:00:00Z",
  "type": "adjustment",
  "quantity_delta": "-2",
  "balance_after": "8",
  "adjustment_reason": "damage",
  "note": "Se rompió la rosca",
  "reference_type": "adjustment_request",
  "reference_id": "0192…",
  "created_by": {"id": "0192…", "full_name": "Admin"},
  "requested_by": {"id": "0192…", "full_name": "José (Almacén)"},
  "cost_before_usd": null,
  "cost_after_usd": null
}
```

- `requested_by` solo si viene de una solicitud aprobada.
- 🅰 `cost_before_usd`, `cost_after_usd`.

### Línea de conteo (`StockCountLine` / `StockCountLineBlind`)

```json
{
  "id": "0192…",
  "product": {"id": "0192…", "sku": "FER-0003", "name": "Ferrule 1/2\"", "unit": {"code": "u", "decimals": 0}},
  "counted_quantity": "12",
  "counted_at": "2026-10-08T15:00:00Z",
  "counted_by": {"id": "0192…", "full_name": "José"},
  "expected_quantity": "14",
  "difference": "-2"
}
```

- 🅰 `expected_quantity`, `difference` (el Almacén cuenta a ciegas, FR-025).

## Endpoints

### Configuración (RF-03 a RF-05; FR-028 a FR-031)

| Método y ruta | Quién | Descripción |
|---|---|---|
| `GET /units` | Cualquier rol | Unidades, con `?include_inactive=true` solo para Admin |
| `POST /units` | Admin | `{code, name, decimals}` → 201 |
| `PATCH /units/{id}` | Admin | `{name?, is_active?}`; `code` y `decimals` no se cambian (422 si se envían) |
| `GET /categories` | Cualquier rol | Categorías con sus definiciones de atributos activas |
| `POST /categories` | Admin | `{name, sku_prefix, default_unit_id, unit_locked}` → 201 |
| `PATCH /categories/{id}` | Admin | `{name?, sku_prefix?, default_unit_id?, unit_locked?, is_active?}`; `prefix_in_use` |
| `POST /categories/{id}/attributes` | Admin | `{key, label, data_type, options?, is_required, is_filterable, sort_order}` → 201 |
| `PATCH /attributes/{id}` | Admin | `{label?, options?, is_required?, is_filterable?, sort_order?, is_active?}`; las opciones se agregan o desactivan, no se borran; `key` y `data_type` no se cambian (422 si se envían) |

### Productos (RF-01, RF-02, RF-06, RF-07; FR-001 a FR-015, FR-032, FR-033)

| Método y ruta | Quién | Descripción |
|---|---|---|
| `GET /products` | Cualquier rol | Búsqueda paginada: `q`, `category_id`, `attr.<key>=<valor>` (filtrables), `is_active` (Admin y Almacén), `is_published`, `low_stock`. Orden: SKU exacto primero, luego nombre |
| `POST /products` | Admin, Almacén | `{category_id, unit_id?, name, description, attributes, min_stock}` → 201 con `warnings` (`duplicate_name`). Sin precio ni costo |
| `GET /products/{id}` | Cualquier rol | Ficha (esquema por rol). Vendedor: 404 si está inactivo |
| `PATCH /products/{id}` | Admin, Almacén | `{name?, description?, attributes?, min_stock?, category_id?, unit_id?, is_active?, updated_at}`; `product_has_movements`. Desactivar también despublica. Respuesta con `warnings`: `duplicate_name` (al renombrar), `has_stock` (al desactivar con stock distinto de cero) y `stale_data` (`updated_at` distinto del guardado; el cambio se aplica igual, R15) |
| `PUT /products/{id}/price` | Admin | `{sale_price_usd}` (`> 0`, 2 decimales); agrega a `product_price` y audita |
| `GET /products/{id}/prices` | Admin | Historial de precios, más reciente primero |
| `PUT /products/{id}/initial-cost` | Admin | `{avg_cost_usd}` (`>= 0`, hasta 6 decimales); `cost_locked` |
| `PUT /products/{id}/publication` | Admin | `{is_published}`; `not_publishable` |
| `POST /products/{id}/photos` | Admin, Almacén | `multipart/form-data` campo `file`; normaliza a WebP (R9); `max_photos`, `photo_too_large`, `photo_unsupported` |
| `DELETE /products/{id}/photos/{photo_id}` | Admin, Almacén | Quita la foto (marca `removed_at`, borra el objeto) → 204 |
| `PUT /products/{id}/photos/order` | Admin, Almacén | `{photo_ids: [...]}` con todas las fotos activas |
| `GET /products/{id}/movements` | Admin, Almacén | Kardex paginado; `from`, `to` (fechas de negocio), `type`. Más reciente primero |

### Inventario (RF-08 a RF-11; FR-016 a FR-023, RN-19)

| Método y ruta | Quién | Descripción |
|---|---|---|
| `POST /inventory/adjustments` | Admin, Almacén | `{product_id, quantity_delta, reason, note?}`. **201** `{"status": "applied", "movement": …}` si es del Admin o positivo del Almacén; **202** `{"status": "pending", "request": …}` si es negativo del Almacén. `negative_stock`, `validation_error` (cero, decimales, motivo) |
| `GET /inventory/adjustment-requests` | Admin, Almacén | `?status=`; el Almacén solo ve las suyas |
| `POST /inventory/adjustment-requests/{id}/approve` | Admin | Crea el movimiento; `negative_stock`, `invalid_state` |
| `POST /inventory/adjustment-requests/{id}/reject` | Admin | `{reason}` obligatorio; `invalid_state` |
| `POST /inventory/adjustment-requests/{id}/withdraw` | Almacén (solo el solicitante) | `invalid_state`; 403 si no es suya |
| `GET /inventory/low-stock` | Admin, Almacén | Productos activos con `stock <= min_stock`, por categoría, con el esquema de producto por rol (sin precio ni costo para el Almacén) |
| `GET /inventory/summary` | Admin, Almacén | `{low_stock, pending_adjustments, counts_ready_for_review}` (Admin) o `{low_stock, my_pending_requests, open_counts}` (Almacén; `open_counts` cuenta todos los conteos abiertos, que el Almacén anota) |

### Conteos físicos (RF-12; FR-024 a FR-027, RN-19)

| Método y ruta | Quién | Descripción |
|---|---|---|
| `GET /stock-counts` | Admin, Almacén | `?status=`; resumen con avance (anotadas / total) |
| `POST /stock-counts` | Admin, Almacén | `{scope, notes?}` → 201; con `all` y categorías entran los activos y los inactivos con stock distinto de cero; con productos, los elegidos (FR-024); `product_in_open_count` con los SKU en conflicto |
| `GET /stock-counts/{id}` | Admin, Almacén | Conteo con líneas (esquema por rol: a ciegas para Almacén) |
| `PUT /stock-counts/{id}/lines/{line_id}` | Admin, Almacén | `{counted_quantity}`; solo con el conteo `open`; toma el stock del momento (FR-025) |
| `POST /stock-counts/{id}/ready` | Admin, Almacén | `open` → `ready_for_review` |
| `POST /stock-counts/{id}/reopen` | Admin | `ready_for_review` → `open` |
| `POST /stock-counts/{id}/apply` | Admin | `{acknowledge_uncounted: bool}`; genera los ajustes; responde con los movimientos y `negative_products`; `uncounted_lines`, `invalid_state` |
| `POST /stock-counts/{id}/cancel` | Admin, Almacén | `{reason}` obligatorio; el Almacén solo cancela conteos `open` (403 si está `ready_for_review`); libera los productos para otro conteo; `invalid_state` |

## Matriz de permisos de la etapa

Se agrega a `test_permissions_matrix.py`. Además de lo anterior, todos los endpoints
niegan el acceso sin sesión (`not_authenticated`) y con contraseña temporal
(`password_change_required`).

| Endpoint | Admin | Vendedor | Almacén |
|---|:-:|:-:|:-:|
| `GET /units`, `GET /categories` | ✅ | ✅ | ✅ |
| `POST/PATCH` de unidades, categorías y atributos | ✅ | ❌ | ❌ |
| `GET /products`, `GET /products/{id}` | ✅ | ✅ (sin costo) | ✅ (sin precio ni costo) |
| `POST /products`, `PATCH /products/{id}`, fotos | ✅ | ❌ | ✅ |
| `PUT …/price`, `GET …/prices`, `PUT …/initial-cost`, `PUT …/publication` | ✅ | ❌ | ❌ |
| `GET /products/{id}/movements` | ✅ | ❌ | ✅ (sin costo) |
| `POST /inventory/adjustments` | ✅ | ❌ | ✅ (negativos quedan pendientes) |
| `GET /inventory/adjustment-requests` | ✅ (todas) | ❌ | ✅ (solo propias) |
| `approve`, `reject` | ✅ | ❌ | ❌ |
| `withdraw` | ❌ | ❌ | ✅ (solo propias) |
| `GET /inventory/low-stock`, `GET /inventory/summary` | ✅ | ❌ | ✅ |
| `GET/POST /stock-counts`, `GET /stock-counts/{id}`, anotar, `ready` | ✅ | ❌ | ✅ (a ciegas) |
| `cancel` | ✅ | ❌ | ✅ (solo conteos `open`) |
| `reopen`, `apply` | ✅ | ❌ | ❌ |
