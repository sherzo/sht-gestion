---

description: "Tareas de la etapa 1.1b: productos, categorías e inventario"
---

# Tasks: Productos, categorías e inventario (etapa 1.1b)

**Input**: documentos de diseño en `specs/002-productos-inventario/`

**Prerequisites**: plan.md, spec.md, research.md (R1–R16), data-model.md, contracts/api.md, quickstart.md

**Tests**: se incluyen. La constitución los exige (principio VII: movimientos de kardex, validación de unidades y permisos por rol) y la especificación también (SC-003, SC-004, SC-005a, SC-006). Cada prueba nombra en su docstring el RF/RN del PRD y el FR/SC de la especificación que verifica. Las pruebas de cada historia se escriben primero y deben fallar antes de implementar.

**Organization**: tareas agrupadas por historia de usuario de spec.md (US1–US6), cada una probable por separado.

**Trazabilidad con el PRD** (constitución, "Flujo de trabajo" y principio VII):

| FR de la especificación | RF/RN/RNF del PRD |
|---|---|
| FR-001 a FR-010 | RF-01, RF-02, RF-05, RF-07, RN-13 |
| FR-011 a FR-015 | RF-01, RN-01, RN-09, RN-17, RN-18, RF-46, RNF-05 |
| FR-016 a FR-023 (con FR-019a, FR-019b) | RF-08 a RF-11, RN-08, RN-19 |
| FR-024 a FR-027 (con FR-025a) | RF-12, RN-19 |
| FR-028 a FR-031 | RF-03, RF-04, RF-05 |
| FR-032 y FR-033 | RF-06, RNF-04 |
| FR-034 | RF-46, RNF-08 |
| FR-035 y FR-036 | RNF-02, RNF-07 |

Los commits y las docstrings de las pruebas citan el RF/RN del PRD y el FR de la especificación, por ejemplo `RF-08/FR-021`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede hacer en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia a la que pertenece (US1…US6)
- Rutas relativas a la raíz del repositorio

## Path Conventions

- Backend: `backend/app/`, `backend/tests/`, `backend/migrations/`
- App interna: `frontend/src/`
- Compartido: `packages/shared/src/`
- Comandos del backend desde `backend/` (`uv run …`); los de Node desde la raíz (`pnpm …`)
- Decimales en JSON siempre como cadenas (ADR-0004); en Python siempre `Decimal`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: dependencias y configuración que todo lo demás usa.

- [ ] T001 Agregar dependencias del backend con `uv add pillow httpx python-multipart` en `backend/pyproject.toml` y `backend/uv.lock` (R9: normalizar fotos, API de Supabase Storage y subida `multipart/form-data`)
- [ ] T002 [P] Documentar las variables nuevas en `backend/.env.example` con comentarios en español: `PHOTO_STORAGE=local` (`local` o `supabase`), `PHOTO_LOCAL_DIR=.media`, `SUPABASE_URL=`, `SUPABASE_STORAGE_KEY=`, `PHOTO_BUCKET=product-photos` (R9, quickstart)
- [ ] T003 [P] Agregar `backend/.media/` a `.gitignore` (fotos de desarrollo local, R9)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: reglas de dominio, tablas, triggers, datos iniciales, servicio de movimientos, esquemas por rol y base de pruebas que necesitan todas las historias.

**⚠️ CRITICAL**: ninguna historia empieza antes de terminar esta fase.

- [ ] T004 Ampliar `Settings` en `backend/app/core/config.py`: `photo_storage: Literal["local", "supabase"] = "local"`, `photo_local_dir: str = ".media"`, `supabase_url: str | None = None`, `supabase_storage_key: SecretStr | None = None`, `photo_bucket: str = "product-photos"`, `photo_max_upload_bytes: int = 5 * 1024 * 1024`; el validador existente exige `supabase_url` y `supabase_storage_key` cuando `photo_storage == "supabase"` y prohíbe `photo_storage == "local"` en `staging` y `production` (R9)
- [ ] T005 [P] Crear `backend/app/domain/units.py` con `validate_quantity(value: Decimal, decimals: int, *, allow_zero: bool, allow_negative: bool) -> Decimal` que rechaza (con `ValueError` y mensaje en español) más decimales de los permitidos sin redondear, cero si no se permite y negativos si no se permiten, y sus pruebas en `backend/tests/test_units_domain.py`: `1.5` con 0 decimales falla, `0.305` con 2 falla, `0.30` con 2 pasa, `-2` según `allow_negative` (RF-05/FR-020, R3)
- [ ] T006 [P] Crear `backend/app/domain/search.py` con `normalize_text(text) -> str` (NFKD, sin marcas diacríticas, minúsculas, espacios simples, conserva `/`, `"`, `-` y dígitos), `build_search_text(name, description, sku, attribute_values) -> str` y `search_tokens(query) -> list[str]` (palabras no vacías, sin repetidos), y sus pruebas en `backend/tests/test_search_domain.py`: "Conexión" → "conexion", "R2 1/2\"" conserva `1/2"`, `CON-0012` → `con-0012` (RF-06/FR-032, R4)
- [ ] T007 [P] Crear `backend/app/domain/sku.py` con `format_sku(prefix: str, number: int) -> str` (`f"{prefix}-{number:04d}"`: `MAN-0001`, `MAN-9999`, `MAN-10000`) y sus pruebas unitarias al inicio de `backend/tests/test_sku.py` (RF-02/FR-002, R1)
- [ ] T008 [P] Crear `backend/app/domain/attributes.py` con `AttributeSpec` (`key`, `label`, `data_type` en `text | number | option`, `options: list[{"value", "is_active"}]`, `is_required`, `is_active`) y `validate_attributes(values: dict, specs: list[AttributeSpec], previous: dict | None) -> dict` que: rechaza claves desconocidas o de atributos inactivos nuevos; exige los obligatorios activos; `number` como decimal válido guardado en cadena; `option` existente y activa, salvo que el valor no cambie respecto de `previous` (una opción desactivada ya guardada se conserva); `text` recortado, hasta 200 caracteres; devuelve errores por clave. Pruebas en `backend/tests/test_attributes_domain.py` (RF-04/FR-006, R5)
- [ ] T009 Agregar a `backend/app/db/models.py` los modelos `Unit`, `Category`, `AttributeDefinition`, `Product`, `ProductPrice`, `ProductPhoto`, `StockMovement`, `AdjustmentRequest`, `StockCount` y `StockCountLine` exactamente como en data-model.md, con `id` UUIDv7, `Numeric` sobre los dominios (`usd_amount`, `usd_cost`, `quantity`) y estas reglas literales: `unit.code` "Único, 1–10 caracteres en minúscula", `unit.decimals` `CHECK (decimals IN (0, 2))`; `category.sku_prefix` "Único, `^[A-Z]{3}$`", `category.next_sku_number` "`>= 1`", `category.name` "1–60 caracteres"; `attribute_definition.key` "`^[a-z][a-z0-9_]{1,39}$`, único por categoría", `data_type` "`text` \| `number` \| `option`"; `product.name` "1–120 caracteres, recortado", `product.description` "0–2.000 caracteres", `sale_price_usd` "`> 0`; nulo = sin precio", `avg_cost_usd` "`>= 0`; nulo = sin costo", `min_stock` "`>= 0`", `is_published` `CHECK (NOT is_published OR (is_active AND sale_price_usd IS NOT NULL))`; `product_price.price_usd` "`> 0`"; `stock_movement.type` "`purchase` \| `sale` \| `sale_void` \| `purchase_void` \| `adjustment`", `quantity_delta` "`<> 0`", `adjustment_reason` "Obligatorio si `type = 'adjustment'`: `physical_count` \| `damage` \| `loss` \| `correction`", `note` "Hasta 500 caracteres"; `adjustment_request.quantity_delta` "`< 0`", `status` "`pending` \| `approved` \| `rejected` \| `withdrawn`", `rejection_reason` "Obligatorio si `rejected`", `stock_movement_id` "Obligatorio si `approved`"; `stock_count.status` "`open` \| `ready_for_review` \| `applied` \| `cancelled`"; `stock_count_line.counted_quantity` "`>= 0`", único `(stock_count_id, product_id)`
- [ ] T010 Crear la migración `backend/migrations/versions/0004_productos_e_inventario.py` (revisión `0004`, anterior `0003`) con: las diez tablas y sus `CHECK` de T009; índices `UNIQUE (sku)`, `product (category_id, is_active)`, `product (is_active, stock)`, `stock_movement (product_id, occurred_at DESC)`, `adjustment_request (status, requested_at)` y el índice único parcial `stock_count_line (product_id) WHERE is_open` (FR-024); triggers: `stock_movement` `BEFORE INSERT` que bloquea el producto, verifica `balance_after = stock + quantity_delta`, actualiza `product.stock` y pone `has_movements = true`; `stock_movement` y `product_price` rechazan `UPDATE` y `DELETE`; `product` `BEFORE UPDATE` que rechaza cambiar `stock` o `has_movements` cuando `pg_trigger_depth() <= 1` (R2); `category` rechaza cambiar `sku_prefix` si tiene productos; `adjustment_request` solo admite `UPDATE` desde `pending` hacia un estado final sin tocar otros campos (R7); `stock_count` y `stock_count_line` rechazan cambios con el conteo `applied` o `cancelled`; en las líneas, los campos de anotación (`counted_quantity`, `expected_quantity`, `counted_by`, `counted_at`) solo cambian con el conteo `open`, y los de cierre (`is_open` de `true` a `false` y `stock_movement_id`) con el conteo `open` o `ready_for_review`, para que aplicar o cancelar desde la revisión funcione (R8); `stock_count.cancel_reason` obligatorio si `cancelled`; datos iniciales con UUIDv7 fijos: unidades `m` metro 2 y `u` unidad 0; categorías Mangueras `MAN` (metro, `unit_locked`), Conexiones `CON`, Ferrules `FER`, Ferretería `FRT` (unidad); atributos de research R5 con sus obligatorios, filtrables y opciones. `downgrade` lo quita todo. Comprobar `alembic upgrade head`, `downgrade 0003` y `upgrade head` contra el Postgres local (FR-016, FR-028)
- [ ] T011 Ampliar `backend/tests/conftest.py`: después de migrar, leer en memoria (fixture de sesión) las filas iniciales de `unit`, `category` y `attribute_definition`; antes de cada prueba, `TRUNCATE` de las tablas nuevas además de las de 1.1a y reinsertar esas filas iniciales; fixture `photo_dir` que apunta `PHOTO_LOCAL_DIR` a un directorio temporal; fábricas `make_category`, `make_product(category="MAN", *, name, attributes, min_stock="0", sale_price=None, avg_cost=None, is_active=True)` y `give_stock(product, quantity)` (usa `post_movement` con motivo `correction`); helper `category_id(prefix)`
- [ ] T012 Crear `backend/app/services/inventory.py` con `post_movement(db, *, product_id, type, quantity_delta, created_by, adjustment_reason=None, note=None, reference_type=None, reference_id=None, allow_negative=False) -> StockMovement`: bloquea el producto con `FOR UPDATE`, calcula `balance_after`, rechaza con 409 `negative_stock` si queda negativo y `allow_negative` es falso, inserta el movimiento (el trigger actualiza el stock) sin confirmar; única función que cambia stock (FR-016, FR-021, R2). Pruebas en `backend/tests/test_stock_movements.py` (marca `db`): saldo correcto encadenado; `UPDATE product SET stock = …` directo con la sesión de la API falla; `UPDATE` y `DELETE` sobre `stock_movement` fallan; un `balance_after` incorrecto insertado a mano falla; dos `post_movement` simultáneos en hilos sobre el mismo producto dan el saldo final correcto; la suma de los deltas siempre es igual al stock (SC-003)
- [ ] T013 Crear `backend/app/api/product_schemas.py`: `CategoryRef`, `UnitRef`, `PhotoOut` (con `url` pública de `photo_storage`), `ProductWarehouse` (campos comunes del contrato, sin precio ni costo), `ProductSeller(ProductWarehouse)` + `sale_price_usd`, `ProductAdmin(ProductSeller)` + `avg_cost_usd`, `cost_locked`; decimales serializados como cadena; `is_low_stock = is_active and stock <= min_stock`; y `product_for_role(role, product) -> ProductAdmin | ProductSeller | ProductWarehouse`. Los campos prohibidos no existen en el esquema del rol (principio IV, R6)
- [ ] T014 Crear `backend/tests/test_no_cost_leak.py` dirigido por datos: una lista `LEAK_CASES` de `(método, ruta construida con fixtures, cuerpo)`; por cada caso y por Vendedor y Almacén recorre recursivamente el JSON de respuesta y falla si una clave contiene `cost` o `margin`, o `price` en el caso del Almacén. Cada historia agrega sus casos (FR-014, SC-004, R6)
- [ ] T015 [P] Agregar a `packages/shared/src/format.ts` `formatDecimal(value: string, decimals: number): string` (`1.234,56` sin pasar por `number`, operando sobre la cadena), `formatQuantity(value: string, unitDecimals: number)` y `parseDecimalInput(text: string, maxDecimals: number): string | null` (acepta coma decimal y punto de miles; devuelve la cadena con punto o `null` si es inválida o tiene más decimales), exportadas desde `packages/shared/src/index.ts` (RNF-07/FR-036, R13)
- [ ] T016 [P] Agregar a `packages/shared/src/audit-actions.ts` las etiquetas en español de las acciones de research R14 y los grupos "Productos", "Inventario" y "Configuración", y mostrar esos grupos en el filtro de `frontend/src/app/auditoria/page.tsx` (FR-034)
- [ ] T017 [P] Crear en `frontend/src/components/ui/` según `docs/guia-de-estilos.md`: `decimal-input.tsx` (campo de texto con `inputMode="decimal"`, usa `parseDecimalInput` y muestra error si excede los decimales de la unidad), `status-chip.tsx` (variantes `low_stock`, `negative_stock` (stock bajo cero, destacado, caso borde de la spec), `inactive`, `published`, `pending`, `approved`, `rejected`, `withdrawn`, con ícono y texto, no solo color) y `tabs.tsx` (pestañas accesibles con teclado)
- [ ] T018 Agregar a `NAV_ITEMS` en `frontend/src/components/app-shell.tsx`: `Productos` (todos los roles), `Inventario` con Ajuste, Stock bajo y Conteos (Admin y Almacén), `Mis solicitudes` (Almacén), `Pendientes` (Admin) y `Configuración` (Admin), con íconos de `lucide-react`
- [ ] T019 Crear `backend/app/services/photo_storage.py` con la interfaz `PhotoStorage` (`save(path, data, content_type)`, `delete(path)`, `public_url(path)`), `LocalPhotoStorage` (escribe en `photo_local_dir`; URL `{base}/media/{path}`) y `SupabasePhotoStorage` (`httpx`: `POST {supabase_url}/storage/v1/object/{bucket}/{path}` con `Authorization: Bearer <clave>` y `x-upsert: false`; `DELETE` del mismo recurso; URL pública `{supabase_url}/storage/v1/object/public/{bucket}/{path}`), y `get_photo_storage()` según `Settings`. En `backend/app/main.py`, montar `StaticFiles` en `/media` solo si `photo_storage == "local"` y `environment` es `local` o `test` (R9)

**Checkpoint**: base lista. `uv run pytest` pasa (dominio, movimientos y triggers) y la migración sube y baja con los datos iniciales.

---

## Phase 3: User Story 1 - Registro de productos con SKU automático (Priority: P1) 🎯 MVP

**Goal**: Admin y Almacén crean, editan, activan y desactivan productos con SKU automático, atributos validados, unidad correcta y fotos; Almacén nunca ve ni fija precio.

**Independent Test**: como Almacén, crear una manguera y una conexión, comprobar `MAN-0001` y `CON-0001`, unidad metro fija en la manguera y ausencia de precio y costo; subir y ordenar fotos.

### Tests for User Story 1 ⚠️

> Escribir primero y comprobar que fallan.

- [ ] T020 [P] [US1] Pruebas de SKU en `backend/tests/test_sku.py` (marca `db`): primera manguera `MAN-0001`; `CON-0007` existente → la siguiente `CON-0008` aunque se hayan desactivado productos; 20 altas simultáneas en hilos en la misma categoría dan 20 SKU distintos y consecutivos (SC-006); cambiar de categoría un producto sin movimientos le asigna el siguiente SKU de la categoría destino y el anterior no se reutiliza; un `sku` enviado en el cuerpo se rechaza con 422 (esquemas con `extra="forbid"`) (RF-02/FR-002 a FR-004)
- [ ] T021 [P] [US1] Pruebas de productos en `backend/tests/test_products.py` (marca `db`): alta por Almacén y por Admin sin precio ni costo, con stock `"0"`; Mangueras con unidad distinta de metro → 422; atributo de opción fuera de la lista → 422 con `fields` por clave; obligatorio faltante → 422; Ferretería solo con nombre y descripción → 201; nombre activo repetido en la categoría → 201 con `warnings: ["duplicate_name"]`, y renombrar a un nombre activo repetido → 200 con la misma advertencia; stock mínimo `1.5` en unidad o `0.305` en metro → 422, y al cambiar la unidad de metro a unidad un stock mínimo `2.50` existente → 422; `PATCH` con un `updated_at` viejo → 200, cambio aplicado y `warnings: ["stale_data"]`; `PATCH` de categoría o unidad con movimientos → 409 `product_has_movements`; desactivar deja `is_published = false`, conserva SKU e historial y se puede reactivar; desactivar con stock distinto de cero → 200 con `warnings: ["has_stock"]`; Vendedor recibe 404 en un producto inactivo y no lo ve en la lista; auditoría `product.created`, `product.updated`, `product.category_changed` (SKU anterior y nuevo), `product.activated`/`deactivated` (RF-01/FR-001, FR-004 a FR-007, FR-010)
- [ ] T022 [P] [US1] Pruebas de fotos en `backend/tests/test_photos.py` (marca `db`, con `photo_dir`): un JPEG de 3000×2000 con EXIF de orientación queda en WebP de lado mayor 1.200 px, orientado y sin EXIF; la primera es la principal; la sexta foto activa → 409 `max_photos`; más de 5 MB → 413 `photo_too_large`; un PDF o un archivo con extensión `.jpg` falsa → 415 `photo_unsupported`; quitar marca `removed_at` y borra el archivo; reordenar con todas las fotos activas cambia `sort_order` y con una lista incompleta → 422; Vendedor → 403; auditoría `product.photo_added`/`removed` (FR-008, R9)
- [ ] T023 [US1] Agregar a `MATRIX` de `backend/tests/test_permissions_matrix.py` las filas de `GET /units`, `GET /categories`, `GET /products`, `POST /products`, `GET /products/{id}`, `PATCH /products/{id}` y los tres endpoints de fotos según `contracts/api.md`, y a `LEAK_CASES` de `backend/tests/test_no_cost_leak.py` la lista y la ficha de producto, las respuestas de `POST /products` y `PATCH /products/{id}`, y las de `POST /products/{id}/photos` y `PUT /products/{id}/photos/order` (Almacén; el Vendedor recibe 403) (SC-004)

### Implementation for User Story 1

- [ ] T024 [US1] Crear en `backend/app/services/products.py`: `create_product` (bloquea la categoría con `FOR UPDATE`, rechaza categoría inactiva, usa `default_unit_id` si no se indica unidad y la impone si `unit_locked`, valida atributos con `domain/attributes`, valida `min_stock` con `domain/units` según los decimales de la unidad, calcula `search_text` con `domain/search`, asigna el SKU con `domain/sku` e incrementa `next_sku_number`, calcula `warnings` (`duplicate_name`), audita), `update_product` (mismas validaciones, y `min_stock` se revalida si cambia la unidad; categoría y unidad solo si `has_movements` es falso, con SKU nuevo al cambiar de categoría; desactivar también despublica; recalcula `search_text`; `warnings`: `duplicate_name` al renombrar, `has_stock` al desactivar con stock distinto de cero y `stale_data` si el `updated_at` recibido no coincide con el guardado, aplicando el cambio igual (R10, R15); audita con antes y después), `get_product` y `list_products(db, *, role, category_id, is_active, page, page_size)` básica ordenada por nombre (la búsqueda completa llega en US3) (FR-001 a FR-007, R1, R10)
- [ ] T025 [US1] Crear `backend/app/services/photos.py`: `add_photo` (lee como máximo `photo_max_upload_bytes + 1`; abre con Pillow y exige formato `JPEG`, `PNG` o `WEBP`; `ImageOps.exif_transpose`; conserva transparencia si la hay; `thumbnail((1200, 1200))`; guarda WebP calidad 80 sin metadatos; bloquea el producto y rechaza más de 5 fotos activas; guarda con `photo_storage` en `products/{product_id}/{photo_id}.webp` y registra `width`, `height`, `size_bytes`), `remove_photo` (marca `removed_at`/`removed_by` y borra el objeto) y `reorder_photos`, con auditoría (FR-008, R9)
- [ ] T026 [US1] Crear `backend/app/api/catalog_config.py` con `GET /units` y `GET /categories` (`require_authenticated()`, categorías con sus atributos activos y opciones) y `backend/app/api/products.py` con `POST /products`, `GET /products`, `GET /products/{id}`, `PATCH /products/{id}` (Admin y Almacén para escribir, cualquier rol para leer, respuesta con `product_for_role`) y `POST /products/{id}/photos` (`UploadFile`), `DELETE /products/{id}/photos/{photo_id}` y `PUT /products/{id}/photos/order` (Admin y Almacén). Esquemas de entrada con `extra="forbid"` y decimales como cadena. Registrar los routers en `backend/app/main.py` (contracts/api.md)
- [ ] T027 [P] [US1] Crear `frontend/src/lib/photos/resize.ts`: `resizeForUpload(file: File): Promise<Blob>` que reduce a lado mayor 1.600 px con `createImageBitmap` (respetando la orientación) y `canvas.toBlob("image/jpeg", 0.85)`; si falla, envía el archivo original (R9)
- [ ] T028 [US1] Crear `frontend/src/components/products/product-form.tsx` (categoría; unidad deshabilitada si `unit_locked`; nombre; descripción; campos de atributos generados desde las definiciones de la categoría con su tipo, opciones activas y obligatorios; stock mínimo con `DecimalInput` según los decimales de la unidad; envía el `updated_at` leído; muestra `warnings` (`duplicate_name`, `has_stock` y `stale_data`, este último con la opción de recargar los datos actuales) y errores por campo) y `frontend/src/components/products/photo-gallery.tsx` (miniaturas, principal destacada, subir con `resizeForUpload`, quitar con confirmación y reordenar con botones accesibles; oculto para el Vendedor)
- [ ] T029 [US1] Crear `frontend/src/app/productos/page.tsx` (lista paginada con SKU, nombre, categoría, stock con `formatQuantity` y chips de estado, incluido `negative_stock` cuando el stock es menor que cero; botón "Nuevo producto" para Admin y Almacén), `frontend/src/app/productos/nuevo/page.tsx` y `frontend/src/app/productos/ficha/page.tsx` (`?id=`, pestañas "Datos" y "Fotos"; edición, activar y desactivar para Admin y Almacén; solo lectura para el Vendedor), todo dentro de `RequireAuth` y `AppShell`
- [ ] T030 [US1] Ejecutar `pnpm api:types` y tipar con `packages/shared/src/api/schema.d.ts` las llamadas de las pantallas de productos

**Checkpoint**: US1 funciona sola: altas con SKU, atributos, unidad fija, fotos, activar y desactivar, sin precio ni costo para el Almacén.

---

## Phase 4: User Story 2 - Kardex y ajustes de inventario con motivo (Priority: P1)

**Goal**: ajustes con motivo que generan movimientos; los negativos del Almacén esperan la aprobación del Admin; kardex consultable por Admin y Almacén.

**Independent Test**: sobre un producto con stock 10, ajuste −2 por daño del Admin, +0,50 m de corrección en una manguera, −2 del Almacén pendiente y luego aprobado; el kardex muestra cada movimiento con saldo, usuario, motivo y quién aprobó.

### Tests for User Story 2 ⚠️

- [ ] T031 [P] [US2] Pruebas de ajustes en `backend/tests/test_adjustments.py` (marca `db`): Admin −2 por `damage` → 201 `applied`, stock 8; Almacén +3 por `correction` → 201 `applied`; Almacén −2 por `loss` → 202 `pending` y el stock no cambia; aprobar → movimiento con `created_by` del Admin y la solicitud con `requested_by` del Almacén y `stock_movement_id`; aprobar cuando el stock ya bajó y quedaría negativo → 409 `negative_stock`; rechazar sin motivo → 422 y con motivo → `rejected` sin movimiento; retirar la propia → `withdrawn`; otro Almacén retira una ajena → 403; decidir una solicitud ya decidida → 409 `invalid_state`; `UPDATE` directo de una solicitud decidida falla (trigger); cantidad cero, sin motivo, `1.5` en unidad o `0.305` en metro → 422; ajuste manual −5 con stock 3 → 409 `negative_stock`; el Almacén solo lista sus solicitudes; auditoría `inventory.adjustment_applied`, `adjustment_requested`, `adjustment_approved`, `adjustment_rejected`, `adjustment_withdrawn` con stock antes y después (RF-08 a RF-10/FR-019, FR-019a, FR-020, RN-19, SC-005a)
- [ ] T032 [P] [US2] Pruebas del kardex en `backend/tests/test_kardex.py` (marca `db`): `GET /products/{id}/movements` ordenado del más reciente al más antiguo, con `balance_after` de cada uno; filtros `from`/`to` por fecha de negocio de Caracas y `type`; `requested_by` en los movimientos que vienen de una solicitud; Vendedor → 403; Almacén sin `cost_before_usd`/`cost_after_usd` (FR-017, FR-022)
- [ ] T033 [US2] Agregar a `MATRIX` las filas de `POST /inventory/adjustments`, `GET /inventory/adjustment-requests`, `approve`, `reject`, `withdraw` y `GET /products/{id}/movements`, y a `LEAK_CASES` el kardex, la lista de solicitudes y las respuestas de `POST /inventory/adjustments` (201 con el movimiento y 202 con la solicitud) (SC-004)

### Implementation for User Story 2

- [ ] T034 [US2] Agregar a `backend/app/services/inventory.py`: `register_adjustment` (valida cantidad con `domain/units` según la unidad del producto, motivo obligatorio y nota hasta 500 caracteres; Admin o positivo del Almacén → `post_movement` inmediato; negativo del Almacén → `AdjustmentRequest` `pending` comprobando que no dejaría el stock negativo en ese momento), `approve_request` (bloquea solicitud y producto, valida `pending`, `post_movement` con `reference_type = 'adjustment_request'`), `reject_request` (motivo obligatorio), `withdraw_request` (solo el solicitante), `list_requests` (el Almacén solo las suyas) y `list_movements` (filtros, paginación y `requested_by` por unión con la solicitud), con auditoría en la misma transacción (FR-019, FR-019a, FR-022, R7)
- [ ] T035 [US2] Crear `backend/app/api/inventory.py` con `POST /inventory/adjustments` (201 `{"status": "applied", "movement"}` o 202 `{"status": "pending", "request"}`), `GET /inventory/adjustment-requests` y `approve`, `reject`, `withdraw`, y agregar `GET /products/{id}/movements` en `backend/app/api/products.py` con esquema de movimiento por rol (sin campos de costo para el Almacén). Registrar el router en `backend/app/main.py`
- [ ] T036 [P] [US2] Crear `frontend/src/components/products/kardex-table.tsx` (fecha `dd/mm/aaaa hh:mm`, tipo, cantidad con signo, saldo, motivo, nota, quién registró y quién solicitó; filtros por fechas y tipo; tarjetas en el teléfono) y agregar la pestaña "Kardex" a `frontend/src/app/productos/ficha/page.tsx`, visible solo para Admin y Almacén
- [ ] T037 [P] [US2] Crear `frontend/src/app/inventario/ajuste/page.tsx`: buscar el producto, elegir entrada o salida, cantidad con `DecimalInput` según la unidad, motivo (Conteo físico, Daño, Pérdida, Corrección) y nota; al guardar muestra el stock nuevo o, si quedó pendiente, "Tu salida quedó pendiente de aprobación del administrador"
- [ ] T038 [P] [US2] Crear `frontend/src/app/pendientes/page.tsx` (solo Admin): lista de ajustes por aprobar con producto, cantidad, motivo, nota, quién y cuándo; aprobar con confirmación y rechazar con diálogo de motivo obligatorio; mensaje claro ante `negative_stock`. La sección de conteos listos llega en US5
- [ ] T039 [P] [US2] Crear `frontend/src/app/inventario/mis-solicitudes/page.tsx` (solo Almacén): solicitudes con `StatusChip`, motivo de rechazo y botón para retirar las pendientes
- [ ] T040 [US2] Ejecutar `pnpm api:types` y tipar las pantallas de inventario

**Checkpoint**: US2 funciona sola: ajustes inmediatos y pendientes, aprobación y rechazo, kardex por rol.

---

## Phase 5: User Story 3 - Búsqueda rápida y alerta de stock bajo (Priority: P2)

**Goal**: búsqueda sin acentos ni mayúsculas por nombre, descripción, SKU y atributos en menos de 1 segundo, con filtros, y listado de stock bajo con tarjetas en el inicio.

**Independent Test**: con 1.000 productos de prueba, buscar "r2 1/2", "conexion giratoria" y un SKU; poner un producto en su stock mínimo y verlo en el listado y en la tarjeta del inicio.

### Tests for User Story 3 ⚠️

- [ ] T041 [P] [US3] Pruebas de búsqueda en `backend/tests/test_search.py` (marca `db`): "conexion giratoria" encuentra "Conexión hembra giratoria"; "r2 1/2" encuentra las mangueras R2 de 1/2" por sus atributos; palabras en cualquier orden; el SKU exacto aparece primero; filtros `category_id`, `attr.hose_type=R2`, `is_active`, `is_published` y `low_stock`; el Vendedor solo recibe activos aunque pida `is_active=false`; paginación con `total` (RF-06/FR-032, FR-033)
- [ ] T042 [P] [US3] Prueba de rendimiento en `backend/tests/test_search_performance.py` (marca `db`): inserta 1.000 productos sintéticos y verifica que cada una de 10 búsquedas típicas responde en menos de 200 ms en el servidor (SC-001, R16)
- [ ] T043 [P] [US3] Pruebas de stock bajo y resumen en `backend/tests/test_inventory_summary.py` (marca `db`): un producto con mínimo 5 aparece en `GET /inventory/low-stock` con stock 5 y deja de aparecer con 6; un inactivo nunca aparece; con mínimo 0 aparece solo al agotarse; `GET /inventory/summary` devuelve los contadores del Admin y los del Almacén según el contrato; Vendedor → 403 en ambos; agregar sus filas a `MATRIX` y `GET /inventory/low-stock` a `LEAK_CASES` (el Almacén no recibe precio ni costo) (RF-11/FR-023, FR-019b, R11, SC-004)

### Implementation for User Story 3

- [ ] T044 [US3] Ampliar `list_products` en `backend/app/services/products.py` con `q` (normaliza con `search_tokens` y exige cada palabra con `search_text LIKE '%palabra%'`, escapando `%` y `_`), filtros de atributos filtrables `attr.<key>`, `is_published` y `low_stock`, orden por SKU exacto primero y luego nombre, y paginación (máximo 100); en `backend/app/api/products.py`, leer los parámetros `attr.<key>` de la consulta y validar que la clave sea filtrable (R4)
- [ ] T045 [US3] Agregar `low_stock_products` y `summary(role, user)` en `backend/app/services/inventory.py`, y `GET /inventory/low-stock` (cada producto con `product_for_role`) y `GET /inventory/summary` (Admin y Almacén) en `backend/app/api/inventory.py` (R11, principio IV)
- [ ] T046 [P] [US3] Agregar en `backend/app/cli.py` el comando `seed-demo-products N` que crea N productos sintéticos repartidos en las cuatro categorías con atributos válidos, solo si `environment` es `local` (se niega en otro ambiente) (quickstart escenario 10)
- [ ] T047 [US3] Crear `frontend/src/components/products/product-search.tsx` (campo de búsqueda con espera de 250 ms, filtros de categoría, atributos filtrables de la categoría elegida, estado y "solo stock bajo"; mensaje sin resultados con "Crear producto" para Admin y Almacén) y usarlo en `frontend/src/app/productos/page.tsx` y en la búsqueda de `frontend/src/app/inventario/ajuste/page.tsx`
- [ ] T048 [P] [US3] Crear `frontend/src/app/inventario/stock-bajo/page.tsx` (agrupado por categoría, stock y mínimo con `formatQuantity`) y agregar a `frontend/src/app/page.tsx` las tarjetas del resumen con enlace (stock bajo; ajustes pendientes y conteos listos para el Admin; mis solicitudes y conteos abiertos para el Almacén)

**Checkpoint**: US3 funciona sola: búsqueda con filtros en menos de 1 segundo y stock bajo visible en el inicio.

---

## Phase 6: User Story 4 - Precio de venta y costo, solo para quien corresponde (Priority: P2)

**Goal**: el Admin fija precios con historial, define el costo inicial mientras no haya compras y decide la publicación; nadie más ve costos.

**Independent Test**: como Admin, cambiar el precio dos veces y ver historial y auditoría; fijar costo inicial; publicar. Como Vendedor y Almacén, comprobar contra el servidor que no reciben costo y que el Almacén tampoco recibe precio.

### Tests for User Story 4 ⚠️

- [ ] T049 [P] [US4] Pruebas en `backend/tests/test_prices_costs.py` (marca `db`): fijar 12,50 y luego 13,00 → `product_price` con ambos y auditoría `product.price_set` con valor anterior y nuevo; precio con 3 decimales, cero o negativo → 422; `GET /products/{id}/prices` del más reciente al más antiguo; costo inicial `"7.250000"` → guardado; `"0"` distinto de nulo; más de 6 decimales o negativo → 422; con `cost_locked = true` (puesto en la base) → 409 `cost_locked`; auditoría `product.initial_cost_set`; publicar sin precio o inactivo → 409 `not_publishable`; publicar y despublicar con auditoría `product.published`/`unpublished`; Vendedor y Almacén → 403 en los cuatro endpoints (RF-01, RF-07/FR-009, FR-011 a FR-015, RN-09)
- [ ] T050 [US4] Agregar a `MATRIX` las filas de `PUT /products/{id}/price`, `GET /products/{id}/prices`, `PUT /products/{id}/initial-cost` y `PUT /products/{id}/publication`, y a `LEAK_CASES` la ficha de un producto con precio y costo definidos (SC-004)

### Implementation for User Story 4

- [ ] T051 [US4] Agregar en `backend/app/services/products.py`: `set_price` (bloquea el producto, valida `> 0` con 2 decimales, actualiza `sale_price_usd` e inserta `product_price`), `list_prices`, `set_initial_cost` (`>= 0` con hasta 6 decimales; 409 `cost_locked`) y `set_publication` (409 `not_publishable` si está inactivo o sin precio), con auditoría de valor anterior y nuevo (FR-009, FR-011 a FR-013, R6)
- [ ] T052 [US4] Agregar en `backend/app/api/products.py` `PUT /products/{id}/price`, `GET /products/{id}/prices`, `PUT /products/{id}/initial-cost` y `PUT /products/{id}/publication`, solo Admin
- [ ] T053 [US4] Agregar a `frontend/src/app/productos/ficha/page.tsx` la pestaña "Precio y costo" (solo Admin): precio vigente e historial con fecha y usuario, formulario de precio con `DecimalInput` de 2 decimales, costo inicial con hasta 6 decimales deshabilitado y explicado si `cost_locked`, "Sin costo" cuando es nulo, e interruptor de publicación con el motivo si no se puede publicar; mostrar el precio en la ficha y la lista para el Vendedor
- [ ] T054 [US4] Ejecutar `pnpm api:types` y tipar la pestaña de precio y costo

**Checkpoint**: US4 funciona sola: precios con historial, costo inicial con bloqueo futuro y publicación solo del Admin; la prueba de fuga pasa.

---

## Phase 7: User Story 5 - Conteo físico (Priority: P2)

**Goal**: el Almacén abre conteos y anota a ciegas; el Admin revisa diferencias y aplica, generando ajustes de "conteo físico".

**Independent Test**: abrir un conteo de Ferrules como Almacén, anotar dos productos con diferencia y uno igual sin ver el stock del sistema, marcarlo listo; como Admin, aplicarlo y comprobar exactamente dos ajustes.

### Tests for User Story 5 ⚠️

- [ ] T055 [P] [US5] Pruebas en `backend/tests/test_stock_counts.py` (marca `db`): abrir por todo y por categorías crea líneas de los productos activos y de los inactivos con stock distinto de cero, y no de los inactivos con stock cero; abrir por productos incluye un inactivo elegido (FR-007, FR-024); abrir otro conteo con un producto ya incluido → 409 `product_in_open_count` con los SKU; dos aperturas simultáneas en hilos sobre los mismos productos → solo una tiene éxito; anotar guarda `expected_quantity` con el stock del momento y anotar de nuevo lo vuelve a tomar; decimales según la unidad; las respuestas al Almacén no contienen `expected_quantity` ni `difference`; `ready` bloquea nuevas anotaciones; el Almacén no puede `apply` ni `reopen` (403) ni cancelar un conteo `ready_for_review` (403), y sí uno `open`; el Admin devuelve a `open`; aplicar desde `ready_for_review` (el flujo normal) y desde `open` funciona y deja las líneas con `is_open = false` y `stock_movement_id`; aplicar con líneas sin anotar → 409 `uncounted_lines` con la cantidad, y con `acknowledge_uncounted` las ignora; aplicar genera un ajuste `physical_count` con `reference_type = 'stock_count_line'` solo por cada diferencia distinta de cero; un movimiento entre la anotación y la aplicación se conserva (la diferencia es la de la anotación); un saldo resultante negativo se permite y se informa en `negative_products`; un conteo aplicado o cancelado no se modifica (API 409 e intento directo en la base falla); anotar directo en la base una línea de un conteo `ready_for_review` falla (trigger); cancelar sin motivo → 422; cancelar con motivo no genera movimientos, cierra las líneas y deja abrir otro conteo con los mismos productos; auditoría `stock_count.opened`, `ready`, `returned`, `applied` (con el resumen de líneas, ajustes y negativos), `cancelled` (con el motivo), y un `inventory.adjustment_applied` por cada ajuste generado, con producto, cantidad, stock antes y después y `stock_count_id` (RF-12/FR-024 a FR-027, FR-025a, FR-034, RN-19, SC-005, SC-007)
- [ ] T056 [US5] Agregar a `MATRIX` las filas de `/stock-counts` según `contracts/api.md`, y a `LEAK_CASES` la lista y el detalle del conteo y la respuesta de anotar una línea, verificando además que la respuesta al Almacén no tenga `expected_quantity` ni `difference` (FR-025)

### Implementation for User Story 5

- [ ] T057 [US5] Crear `backend/app/services/stock_counts.py`: `open_count` (resuelve el alcance: con `all` y categorías, productos activos e inactivos con stock distinto de cero; con productos, los elegidos; crea las líneas con `is_open = true`; traduce la violación del índice único parcial a 409 `product_in_open_count` con los SKU), `record_line` (solo `open`; valida la cantidad con `domain/units`, `>= 0`; guarda `expected_quantity` con el stock actual bajo bloqueo del producto), `mark_ready`, `reopen`, `apply_count` (bloquea el conteo; 409 `uncounted_lines` salvo `acknowledge_uncounted`; `post_movement` con `allow_negative=True` por cada diferencia, con un `inventory.adjustment_applied` por ajuste; marca primero las líneas `is_open = false` con su `stock_movement_id` y después el conteo `applied`; devuelve movimientos y `negative_products`) y `cancel_count` (motivo obligatorio; el Almacén solo desde `open`, 403 si está `ready_for_review`; marca primero las líneas `is_open = false` y después el conteo `cancelled`), con auditoría (FR-024 a FR-027, FR-034, R8, R14)
- [ ] T058 [US5] Crear `backend/app/api/stock_counts.py` con los ocho endpoints de `contracts/api.md`, esquemas `StockCountLine` (Admin) y `StockCountLineBlind` (Almacén) y avance (anotadas / total) en la lista. Registrar el router en `backend/app/main.py`
- [ ] T059 [P] [US5] Crear `frontend/src/app/inventario/conteos/page.tsx`: conteos con estado, avance y fechas; diálogo "Nuevo conteo" con alcance (todo, categorías o productos) y notas; mensaje con los SKU en conflicto
- [ ] T060 [US5] Crear `frontend/src/app/inventario/conteo/page.tsx` (`?id=`): modo anotar (lista por producto con `DecimalInput` según la unidad, guardado por línea, sin stock del sistema para el Almacén, botón "Listo para revisión" y "Cancelar" con motivo; "Cancelar" no se ofrece al Almacén en un conteo listo para revisión) y modo revisar del Admin (stock al anotar, contado y diferencia, total con diferencia, devolver, y aplicar con confirmación que avisa los productos sin anotar y los que quedarían negativos)
- [ ] T061 [US5] Agregar a `frontend/src/app/pendientes/page.tsx` la sección de conteos listos para revisión con enlace al conteo, y ejecutar `pnpm api:types`

**Checkpoint**: US5 funciona sola: conteo a ciegas, revisión y aplicación solo del Admin.

---

## Phase 8: User Story 6 - Categorías, atributos y unidades configurables (Priority: P3)

**Goal**: el Admin crea y edita categorías con prefijo, atributos y opciones, y unidades, sin código.

**Independent Test**: agregar la opción "R12" a Tipo de Mangueras, crear la unidad "paquete" sin decimales y la categoría `ACE`, crear un producto en ella y verificar `ACE-0001`.

### Tests for User Story 6 ⚠️

- [ ] T062 [P] [US6] Pruebas en `backend/tests/test_catalog_config.py` (marca `db`): los datos iniciales existen (cuatro categorías con prefijos, unidad fija en Mangueras, atributos de R5, unidades `m` y `u`); prefijo repetido o fuera de `^[A-Z]{3}$` → 409/422; cambiar el prefijo de una categoría con productos → 409 `prefix_in_use` y renombrarla funciona; categoría inactiva no admite productos nuevos; atributo con `key` inválida → 422; agregar una opción la deja disponible; desactivar una opción usada conserva el valor del producto pero no se puede elegir en uno nuevo; `key` o `data_type` en `PATCH /attributes/{id}` → 422 (nunca cambian); unidad con 1 decimal → 422; `code` o `decimals` en `PATCH /units/{id}` → 422 (nunca cambian); desactivar una unidad usada por productos activos → 409; Vendedor y Almacén → 403 en las escrituras; auditoría `category.*`, `attribute.*`, `unit.*` (RF-03 a RF-05/FR-028 a FR-031)
- [ ] T063 [US6] Agregar a `MATRIX` las filas de `POST /units`, `PATCH /units/{id}`, `POST /categories`, `PATCH /categories/{id}`, `POST /categories/{id}/attributes` y `PATCH /attributes/{id}` (SC-004)

### Implementation for User Story 6

- [ ] T064 [US6] Crear `backend/app/services/catalog_config.py` con alta y edición de unidades, categorías y atributos según las reglas de data-model.md (opciones que se agregan o desactivan, nunca se borran; `key` inmutable), con auditoría de antes y después (FR-029 a FR-031)
- [ ] T065 [US6] Agregar a `backend/app/api/catalog_config.py` `POST /units`, `PATCH /units/{id}`, `POST /categories`, `PATCH /categories/{id}`, `POST /categories/{id}/attributes` y `PATCH /attributes/{id}` (solo Admin), y `?include_inactive=true` para el Admin en las lecturas
- [ ] T066 [P] [US6] Crear `frontend/src/app/configuracion/categorias/page.tsx` (categorías con prefijo, unidad sugerida y fija; atributos por categoría con tipo, obligatorio, filtrable, orden y opciones activables) y `frontend/src/app/configuracion/unidades/page.tsx` (unidades con decimales 0 o 2 y estado), solo Admin, y ejecutar `pnpm api:types`

**Checkpoint**: US6 funciona sola: estructura del inventario editable por el Admin.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: despliegue de fotos, respaldo, documentación (RNF-09) y validación final.

- [ ] T067 Actualizar `.github/workflows/deploy-api.yml`: agregar `SUPABASE_STORAGE_KEY=supabase-storage-key:latest` a `--set-secrets` y `PHOTO_STORAGE=supabase@SUPABASE_URL=<url>@PHOTO_BUCKET=product-photos` a `--set-env-vars` (la URL como variable de GitHub `SUPABASE_URL`) (R9)
- [ ] T068 **Manual (dueño), antes de integrar a `main`:** en Supabase, crear el bucket público `product-photos` con límite de 1 MB por archivo y tipos `image/webp`; copiar la clave secreta del proyecto a Secret Manager como `supabase-storage-key` y dar a la cuenta de servicio de la API `roles/secretmanager.secretAccessor`; crear claves de acceso S3 de Storage y guardarlas como secretos de GitHub `SUPABASE_S3_ACCESS_KEY_ID`, `SUPABASE_S3_SECRET_ACCESS_KEY` y la variable `SUPABASE_S3_ENDPOINT`, siguiendo el procedimiento de T070
- [ ] T069 Agregar a `.github/workflows/backup.yml` un paso que instala `rclone` y sincroniza el bucket `product-photos` (remoto S3 de Supabase) con `gs://sht-gestion-respaldos/fotos/`. Aplicar en el bucket real, antes del primer respaldo de fotos, la regla de borrado limitada a los volcados (`{"rule": [{"action": {"type": "Delete"}, "condition": {"age": 30, "matchesPrefix": ["sht-"]}}]}` con `gcloud storage buckets update --lifecycle-file`), comprobarla con `gcloud storage buckets describe` y actualizar el bloque de `docs/despliegue.md` que la crea (R9)
- [ ] T070 [P] Actualizar `docs/despliegue.md`: bucket `product-photos`, secreto `supabase-storage-key`, claves S3 y variables nuevas, respaldo de fotos y su restauración (cierra el pendiente de §8), y el comando `seed-demo-products` solo para local
- [ ] T071 [P] Actualizar `docs/modelo-de-datos.md` con los cambios listados en data-model.md ("Cambios a `docs/modelo-de-datos.md`"): §1.4, §3.2, §3.3 y §4
- [ ] T072 [P] Actualizar `docs/arquitectura.md`: búsqueda con texto normalizado sin extensiones (R4), flujo de fotos (navegador → API → Storage, R9), glosario (`adjustment_request`, aprobación `approve`, conteo listo `ready_for_review`, publicación `is_published`) y quitar de §8 lo ya resuelto
- [ ] T073 [P] Crear `docs/decisiones/0009-fotos-de-productos.md`: subida a través de la API, normalización a WebP con Pillow, bucket público con rutas UUIDv7, respaldo con `rclone` y criterio de ADR-0002 para pasar a Supabase Pro; agregarlo al índice de `docs/decisiones/README.md` (R9)
- [ ] T074 [P] Actualizar `docs/guia-de-estilos.md` §9 con los componentes nuevos (`DecimalInput`, `StatusChip`, `Tabs`, buscador con filtros, galería de fotos, tarjetas del inicio)
- [ ] T075 [P] Actualizar `CHANGELOG.md` en "Sin publicar" con la etapa 1.1b (RF-01 a RF-12, RN-08, RN-09, RN-13, RN-18, RN-19) y `docs/plan-de-fases.md` con su estado
- [ ] T076 Ejecutar `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest` (con `DATABASE_URL`), la migración subir–bajar–subir, `pnpm typecheck` y `pnpm build`, y corregir lo que falle
- [ ] T077 Recorrer los escenarios manuales 1–11 de `quickstart.md` en local, en PC y con ancho de teléfono de 360 px, y anotar cualquier desviación como tarea nueva
- [ ] T078 Ejecutar `/security-review` y `/code-review` sobre la rama `002-productos-inventario`, corregir los hallazgos confirmados y repetir T076. Requisito para integrar a `main` (constitución, "Flujo de trabajo")
- [ ] T079 **Después de integrar a `main` (dueño y asistente):** con el despliegue terminado, subir una foto desde el teléfono, medir la búsqueda en producción (SC-001), comprobar que el respaldo de la noche incluye `fotos/` y restaurarlo en local junto con la base (plan de fases, definición de terminado). Registrar los resultados en `CHANGELOG.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (fase 1)**: sin dependencias.
- **Foundational (fase 2)**: depende de Setup; bloquea todas las historias. T009 → T010 → T011 → T012 en secuencia; T013, T014 y T019 después de T009.
- **US1 (fase 3)**: depende de la fase 2. Es el MVP: sin productos no hay nada que ajustar, buscar, valorar ni contar desde la app.
- **US2 (fase 4)**: depende de la fase 2; sus pruebas crean productos con las fábricas de `conftest.py`. Las pantallas usan la ficha de US1 (T029).
- **US3 (fase 5)**: depende de la fase 2; amplía `list_products` de US1 (T024) y la lista de productos (T029).
- **US4 (fase 6)**: depende de la fase 2; la pestaña usa la ficha de US1 (T029).
- **US5 (fase 7)**: depende de la fase 2 (`post_movement`); la sección de pendientes amplía la pantalla de US2 (T038).
- **US6 (fase 8)**: depende de la fase 2; las lecturas de configuración ya existen desde US1 (T026).
- **Polish (fase 9)**: depende de las historias que se entreguen. T068 (manual) debe estar hecho antes de integrar a `main`, o el despliegue de la API fallará al no encontrar el secreto. T078 (revisión) va justo antes de integrar y T079 (validación en producción) después.

### User Story Dependencies

- **US1 (P1)**: solo la fase 2.
- **US2 (P1)**: la fase 2 (API); US1 para la pestaña del kardex.
- **US3 (P2)**: la fase 2 y US1 (`list_products` y la lista de productos).
- **US4 (P2)**: la fase 2 y US1 (ficha).
- **US5 (P2)**: la fase 2; US2 solo para la sección de pendientes.
- **US6 (P3)**: la fase 2; US1 para las lecturas ya creadas.
- Las filas de `MATRIX` y `LEAK_CASES` de cada historia dependen de T014 y de la matriz existente.

### Within Each User Story

- Pruebas primero (deben fallar) → servicios → endpoints → frontend → tipos generados.
- Cada historia termina con su checkpoint antes de pasar a la siguiente prioridad.

### Parallel Opportunities

- Fase 1: T002 y T003 en paralelo después de T001.
- Fase 2: T005–T008 y T015–T017 en paralelo; T009 → T010 → T011 → T012 en secuencia.
- Dentro de cada historia, las pruebas marcadas [P] en paralelo; en US2, las pantallas T036–T039 en paralelo.
- Con la fase 2 terminada, el backend de US2, US5 y US6 puede avanzar en paralelo con US1 (archivos distintos), coordinando las filas de `MATRIX` y `LEAK_CASES`.
- Fase 9: la documentación T070–T075 en paralelo.

---

## Parallel Example: User Story 1

```bash
# Pruebas de US1 juntas:
Task: "Pruebas de SKU en backend/tests/test_sku.py"
Task: "Pruebas de productos en backend/tests/test_products.py"
Task: "Pruebas de fotos en backend/tests/test_photos.py"
```

## Parallel Example: User Story 2

```bash
# Pantallas de US2 juntas (después de T035):
Task: "Pestaña Kardex en frontend/src/components/products/kardex-table.tsx"
Task: "Ajuste en frontend/src/app/inventario/ajuste/page.tsx"
Task: "Pendientes en frontend/src/app/pendientes/page.tsx"
Task: "Mis solicitudes en frontend/src/app/inventario/mis-solicitudes/page.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Fase 1 (Setup) y fase 2 (Foundational): tablas, triggers, datos iniciales y movimientos.
2. Fase 3 (US1): productos con SKU, atributos y fotos.
3. **Parar y validar**: escenarios 1, 2 y 4 de `quickstart.md`.
4. Seguir con US2: con US1 y US2 el inventario ya es trazable (RN-08, RN-19).

### Incremental Delivery

1. Setup + Foundational → base lista.
2. US1 → catálogo interno de productos.
3. US2 → ajustes con aprobación y kardex (criterio de terminado: el stock solo cambia por movimientos).
4. US3 → búsqueda en menos de 1 segundo y stock bajo (criterio de terminado).
5. US4 → precios, costo inicial y publicación (criterio de terminado: nadie salvo el Admin ve costos).
6. US5 → conteo físico a ciegas, para cargar el inventario inicial.
7. US6 → configuración por el Admin.
8. Polish → fotos en producción, respaldo, documentación, ADR-0009, revisión (T078), integración a `main` y validación en producción (T079).

---

## Notes

- [P] = archivos distintos y sin dependencias pendientes.
- Cada commit referencia los RF/RN/FR que toca, en español.
- Las pruebas que necesitan Postgres llevan la marca `db` y se saltan sin `DATABASE_URL`.
- Ningún código fuera de `post_movement` cambia el stock; ningún código fuera de `domain/units.py` valida decimales de cantidades.
- Los esquemas de respuesta por rol se eligen con el rol leído de la base, nunca con el del token (ADR-0008).
