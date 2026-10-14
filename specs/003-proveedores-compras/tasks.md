---

description: "Tareas de la etapa 1.2: proveedores, compras con gastos y tasa BCV"
---

# Tasks: Proveedores, compras con gastos y tasa BCV (etapa 1.2)

**Input**: documentos de diseño en `specs/003-proveedores-compras/`

**Prerequisites**: plan.md, spec.md, research.md (R1–R13), data-model.md, contracts/api.md, quickstart.md

**Tests**: se incluyen. La constitución los exige (principio VII: costo promedio ponderado, kardex y reversos, permisos por rol) y la especificación también (SC-001, SC-002, SC-005, SC-006, SC-009, SC-010). Cada prueba nombra en su docstring el RF/RN del PRD y el FR/SC de la especificación que verifica. Las pruebas de cada historia se escriben primero y deben fallar antes de implementar.

**Organization**: tareas agrupadas por historia de usuario de spec.md (US1–US7), cada una probable por separado. Las fases siguen la prioridad: P1 (US1, US2), P2 (US6, US3, US7, US4) y P3 (US5). US6 va antes que US3 porque las compras en Bs necesitan la tasa.

**Trazabilidad con el PRD** (constitución, "Flujo de trabajo" y principio VII):

| FR de la especificación | RF/RN/RNF del PRD |
|---|---|
| FR-001 a FR-003 | RF-13 |
| FR-004 a FR-008 | RF-14, RF-15, RN-01, RN-05 |
| FR-009 a FR-015 | RF-16, RN-09, RN-05, matriz de permisos |
| FR-016 a FR-019 | RN-14 |
| FR-020 y FR-021 | RF-08, RF-09 |
| FR-022 a FR-024 | RNF-05, RF-46, RNF-02, RNF-07 |
| FR-025 a FR-028 | RF-17, RN-03, RN-15, RN-05 |
| FR-029 a FR-033 | RF-14, RN-20, RN-09 |

Los commits y las docstrings de las pruebas citan el RF/RN del PRD y el FR de la especificación, por ejemplo `RN-20/FR-031`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede hacer en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia a la que pertenece (US1…US7)
- Rutas relativas a la raíz del repositorio

## Path Conventions

- Backend: `backend/app/`, `backend/tests/`, `backend/migrations/`
- App interna: `frontend/src/`
- Compartido: `packages/shared/src/`
- Comandos del backend desde `backend/` (`uv run …`); los de Node desde la raíz (`pnpm …`)
- Decimales en JSON siempre como cadenas (ADR-0004); en Python siempre `Decimal`; redondeo solo en `domain/money.py` y `domain/costing.py`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: no hay dependencias, variables ni secretos nuevos (plan, Technical Context). Solo se prepara la carpeta de casos compartidos.

- [ ] T001 Crear `backend/tests/cases/costing_cases.json` con la estructura `{"weighted_average": [...], "undo_purchase": [...], "charges": [...], "allocation": [...], "landed": [...]}` y los casos de la spec: promedio 10 m a 2 + 30 m a 3 → `2.750000`; stock −2 a 10 + 5 a 12 → `12.000000`; stock 0 con costo 4 + compra a 5 → `5.000000`; stock 5 sin costo + compra a 7 → `7.000000`; deshacer 40 m a 2,75 − 30 a 3 → `2.000000`; deshacer con `stock - quantity <= 0` → `null`; gastos 10 % de `1000.00` → `100.00`, `250.00` USD → `250.00`, `3650.00` Bs a `36.5` → `100.00`; reparto de `450.00` sobre `600.00` y `400.00` → `270.00` y `180.00`; reparto de `100.00` sobre tres líneas de `100.00` → `33.34`, `33.33`, `33.33`; costo final `10.000000 + 270.00 ÷ 60` → `14.500000`; Bs `100.00 ÷ 36.50` → `2.739726` (R1, SC-001, SC-010)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: dominio de costos, tablas, triggers, tasa aplicable, kardex con costo y base de pruebas que necesitan todas las historias.

**⚠️ CRITICAL**: ninguna historia empieza antes de terminar esta fase.

- [ ] T002 [P] Agregar a `backend/app/domain/money.py` los helpers con `ROUND_HALF_UP` explícito: `round_usd(value) -> Decimal` (2 decimales), `round_cost(value) -> Decimal` (6 decimales), `ves_to_usd_cost(amount_ves, rate) -> Decimal` (`round_cost(amount_ves / rate)`), `validate_ves(value)` (`> 0`, hasta 2 decimales, sin redondear), `validate_rate(value)` (`> 0`, hasta 8 decimales) y `validate_percent(value)` (`> 0` y `<= 100`, hasta 2 decimales); actualizar el docstring del módulo (ADR-0004)
- [ ] T003 [P] Crear `backend/app/domain/costing.py` con `ChargeInput` (`charge_type`, `percent`, `amount`, `currency`) y las funciones puras de research R1: `charge_amount_usd(charge, merchandise_total_usd, rate)`; `allocate_by_value(line_totals: list[Decimal], charges_total: Decimal) -> list[Decimal]` (a 2 decimales; residuo a la línea de mayor valor, la primera si hay empate; si `charges_total` es 0, todo 0); `landed_unit_cost(unit_cost_usd, allocated, quantity)`; `weighted_average(stock, cost: Decimal | None, quantity, unit_cost)` (devuelve `unit_cost` si `stock <= 0` o `cost is None`); `undo_purchase(stock, cost, quantity, unit_cost) -> Decimal | None` (`None` si `stock - quantity <= 0` o el resultado es negativo). Sin acceso a la base de datos (RN-09, RN-14, RN-20)
- [ ] T004 [P] Crear `backend/tests/test_costing_domain.py` (sin marca `db`) que recorre todos los casos de `backend/tests/cases/costing_cases.json` contra `domain/costing.py` y `domain/money.py`, y además comprueba con 200 repartos aleatorios (semilla fija) que `sum(allocate_by_value(...)) == charges_total` (RN-09/FR-011, FR-015, FR-018, RN-20/FR-030, FR-031, SC-001, SC-010)
- [ ] T005 [P] Crear `backend/app/domain/rif.py` con `normalize_rif(text) -> str` (quita espacios y guiones, mayúsculas, exige `^[JGVEPC]\d{2,10}$`, separa el último dígito como verificador, rellena el número con ceros hasta 8 dígitos y devuelve `X-NNNNNNNN-N`; más de 8 dígitos de número → `ValueError`) y sus pruebas en `backend/tests/test_rif_domain.py`: `j123456789` → `J-12345678-9`, `V-1234567-8` → `V-01234567-8`, `J 12345678 9` → `J-12345678-9`, `X-12345678-9` y `J-123` → error (RF-13/FR-002, R5)
- [ ] T006 Agregar a `backend/app/db/models.py` los modelos `Supplier`, `ExchangeRate`, `ChargeTemplate`, `Purchase`, `PurchaseItem`, `PurchaseCharge`, `PurchaseVoid`, `Alert` y `SequenceCounter` exactamente como en data-model.md, con estas reglas literales: `supplier.name` "1–120 caracteres, obligatorio", `rif` "Normalizado `^[JGVEPC]-\d{8}-\d$`" con índice único, `phone` "Hasta 30 caracteres", `notes` "Hasta 1.000 caracteres"; `exchange_rate.rate_type` "`BCV`", único `(rate_type, business_date)`; `charge_template.name` "1–80 caracteres; único entre activas (`lower(name)`)", `charge_type` "`percent` \| `fixed`", `currency` "obligatorio si `fixed`, nulo si `percent`"; `purchase.status` "`draft` \| `confirmed` \| `voided`", `currency` "`USD` \| `VES`", `supplier_invoice_number` "Hasta 50 caracteres", `notes` "Hasta 1.000 caracteres", `exchange_rate_date` "nula si y solo si `exchange_rate` es nula", `confirmed_by`/`confirmed_at` "Obligatorios si `status <> 'draft'`", `number` único; `purchase_item.quantity` "`> 0`", `unit_cost_usd` "`> 0`", `allocated_charges_usd` "`>= 0`", único `(purchase_id, product_id)`; `purchase_charge.description` "1–120 caracteres", `percent` "obligatorio si y solo si `percent`", `amount` y `currency` "obligatorio si y solo si `fixed`", `allocation_method` "`value`"; `purchase_void.purchase_id` "Único", `reason` "5–500 caracteres"; `alert.type` "`purchase_void_cost`", `resolved_at`/`resolved_by` "Juntos"; `sequence_counter.next_number` "`>= 1`"
- [ ] T007 Crear la migración `backend/migrations/versions/0005_proveedores_y_compras.py` (revisión `0005`, anterior `0004`) con las nueve tablas y sus `CHECK` de T006; índices `purchase (status, purchase_date DESC)`, `purchase (supplier_id, purchase_date DESC)`, `purchase (supplier_id, lower(supplier_invoice_number))`, `purchase_item (product_id)`, `exchange_rate (rate_type, business_date DESC)`, índice único parcial `charge_template (lower(name)) WHERE is_active` e índice parcial `alert (created_at DESC) WHERE resolved_at IS NULL`; triggers de research R2: `purchase_guard` (en `draft` se edita y se borra; `confirmed → voided` solo cambia `status`; al pasar a `confirmed` exige `number`, `confirmed_by`, `confirmed_at`; todo lo demás se rechaza), `purchase_child_guard` en `purchase_item` y `purchase_charge` (`INSERT`, `UPDATE` y `DELETE` solo con la compra madre en `draft`), `purchase_void` de solo inserción con el `reject_change()` de `0004`, rechazo de `DELETE` en `supplier`, `charge_template` y `exchange_rate`, `exchange_rate` sin cambiar `rate_type` ni `business_date`, y `alert` que solo admite pasar `resolved_at`/`resolved_by` de nulos a valores; dato inicial `INSERT INTO sequence_counter VALUES ('purchase', 1)`. `downgrade` lo quita todo. Comprobar `alembic upgrade head`, `downgrade 0004` y `upgrade head` contra el Postgres local (FR-016, SC-002)
- [ ] T008 Ampliar `backend/tests/conftest.py`: agregar las tablas nuevas a `TABLES` en orden de dependencias (`alert`, `purchase_void`, `purchase_charge`, `purchase_item`, `purchase`, `charge_template`, `exchange_rate`, `supplier`), y `sequence_counter` a `SEEDED_TABLES` para que cada prueba empiece con `next_number = 1`; fábricas `make_supplier(name="Proveedor", rif=None, is_active=True)`, `make_rate(business_date, rate)`, `make_charge_template(name, charge_type, default_value=None, currency=None)` y `make_purchase(supplier, items=[(product, quantity, unit_cost)], charges=[], currency="USD", purchase_date=None, confirm=False, actor=None)` que usan los servicios (no SQL directo)
- [ ] T009 Ampliar `post_movement` en `backend/app/services/inventory.py` con los parámetros opcionales `cost_before_usd: Decimal | None = None` y `cost_after_usd: Decimal | None = None`, que se guardan en el movimiento, y una prueba en `backend/tests/test_stock_movements.py` que los verifica (R3)
- [ ] T010 Crear `backend/app/services/exchange_rates.py` con `applicable_rate(db, on_date) -> tuple[Decimal, date] | None` (última tasa `BCV` con `business_date <= on_date`) y `require_rate(db, on_date)` que lanza 409 `exchange_rate_missing` con la fecha. La carga y la corrección llegan en US6 (FR-012, R6)
- [ ] T011 [P] Crear `backend/app/services/alerts.py` con `create_alert(db, *, type, entity_type, entity_id, details)` (sin confirmar la transacción), `list_alerts(db, *, status, page, page_size)` y `resolve_alert(db, *, actor, alert_id)` (409 `invalid_state` si ya está resuelta; audita `alert.resolved`) (R8)
- [ ] T012 Adaptar `forbidden_keys` en `backend/tests/test_no_cost_leak.py` para la excepción de la constitución 1.2.0: para el Almacén, las claves de costo de factura de una compra (`unit_cost_ves`, `unit_cost_usd`, `line_total_usd`, `line_total_ves`, `allocated_charges_usd`, `landed_unit_cost_usd`) se permiten **solo** dentro de los objetos `items` de una compra; siguen prohibidas en cualquier parte `avg_cost_usd`, `cost_before_usd`, `cost_after_usd`, `cost_changes` y todo lo que contenga `margin`; para el Vendedor sigue prohibido todo lo que contenga `cost`. Agregar a `test_detector_de_claves_prohibidas` un caso que lo demuestre (principio IV, R7, FR-022)
- [ ] T013 [P] Agregar a `packages/shared/src/format.ts` `formatVes(value: string): string` (`Bs 1.234,56`), `formatRate(value: string): string` (hasta 8 decimales sin ceros sobrantes, coma decimal) y `formatPercent(value: string): string` (`10 %`, `12,5 %`), exportadas desde `packages/shared/src/index.ts` (RNF-07/FR-024, R11)
- [ ] T014 [P] Agregar a `packages/shared/src/audit-actions.ts` el grupo "Compras y tasas" con las acciones de research R12 y sus etiquetas en español (`supplier.created` "Proveedor creado", `purchase.confirmed` "Compra confirmada", `purchase.voided` "Compra anulada", `product.cost_updated` "Costo actualizado por compra", `exchange_rate.created` "Tasa BCV cargada", `exchange_rate.corrected` "Tasa BCV corregida", `charge_template.created`/`updated`, `alert.resolved`), y verificar que el filtro de `frontend/src/app/auditoria/page.tsx` lo muestra (FR-023)
- [ ] T015 [P] Agregar a `NAV_ITEMS` en `frontend/src/components/app-shell.tsx`: `Compras` (`/compras/`, ícono `ShoppingCart`, Admin y Almacén), `Proveedores` (`/proveedores/`, ícono `Truck`, Admin y Almacén) y `Tasa BCV` (`/tasas/`, ícono `Landmark`, solo Admin) (R11)

**Checkpoint**: base lista. `uv run pytest` pasa (dominio de costos, RIF, movimientos con costo) y la migración sube y baja.

---

## Phase 3: User Story 1 - Proveedores (Priority: P1) 🎯 MVP

**Goal**: Admin y Almacén registran, editan, desactivan y reactivan proveedores con RIF normalizado y único.

**Independent Test**: como Almacén, crear dos proveedores, intentar un tercero con el RIF de uno (rechazado con el nombre), desactivar uno y comprobar que no se ofrece al crear compras.

### Tests for User Story 1 ⚠️

> Escribir primero y comprobar que fallan.

- [ ] T016 [P] [US1] Pruebas en `backend/tests/test_suppliers.py` (marca `db`): alta por Almacén con RIF `j123456789` → guardado `J-12345678-9`; RIF repetido (en otro formato) → 409 `rif_in_use` con `supplier_name`; sin RIF → 201 y dos proveedores sin RIF conviven; RIF inválido → 422; nombre vacío o de más de 120 caracteres → 422; `PATCH` de nombre, teléfono y notas; desactivar y reactivar; `GET /suppliers?q=` busca por nombre y por RIF; `GET /suppliers?is_active=true` excluye los inactivos; auditoría `supplier.created` y `supplier.updated` con antes y después (RF-13/FR-001 a FR-003)
- [ ] T017 [US1] Agregar a `MATRIX` de `backend/tests/test_permissions_matrix.py` las filas de `GET/POST /suppliers` y `GET/PATCH /suppliers/{id}` (Admin y Almacén; Vendedor ❌) según `contracts/api.md`, con el marcador `{supplier_id}` creado en `actor_headers`

### Implementation for User Story 1

- [ ] T018 [US1] Crear `backend/app/services/suppliers.py`: `create_supplier`, `update_supplier`, `get_supplier`, `list_suppliers(db, *, q, is_active, page, page_size)` (orden por nombre; `q` compara con el nombre sin acentos y con el RIF normalizado si parece un RIF), con `normalize_rif`, 409 `rif_in_use` (incluye `supplier_name`) y auditoría con antes y después (FR-001 a FR-003, R5, R12)
- [ ] T019 [US1] Crear `backend/app/api/suppliers.py` con `GET /suppliers`, `POST /suppliers`, `GET /suppliers/{id}` y `PATCH /suppliers/{id}` (`require_roles(ADMIN, WAREHOUSE)`; entradas con `extra="forbid"`; esquema `Supplier` del contrato) y registrar el router en `backend/app/main.py`
- [ ] T020 [US1] Crear `frontend/src/app/proveedores/page.tsx` (lista paginada con búsqueda, chip de inactivo, botón "Nuevo proveedor"; alta y edición en un `Dialog` con nombre, RIF, teléfono y notas; muestra el error `rif_in_use` con el nombre del otro proveedor; activar y desactivar), dentro de `RequireAuth` y `AppShell`
- [ ] T021 [US1] Ejecutar `pnpm api:types` y tipar las llamadas de proveedores con `packages/shared/src/api/schema.d.ts`

**Checkpoint**: US1 funciona sola: proveedores con RIF único, activos e inactivos.

---

## Phase 4: User Story 2 - Compra en USD: borrador, confirmación y costo promedio (Priority: P1)

**Goal**: compras en USD en borrador que se editan, descartan y confirman; al confirmar, entradas en el kardex con costo antes y después, costo promedio ponderado, costo inicial bloqueado, número sin huecos e inmutabilidad en la base.

**Independent Test**: producto con stock 10 m y costo 2,00; confirmar una compra de 30 m a 3,00 → stock 40 m, costo 2,750000 y kardex con la entrada y su referencia.

### Tests for User Story 2 ⚠️

- [ ] T022 [P] [US2] Pruebas de borrador en `backend/tests/test_purchases_draft.py` (marca `db`): crear compra en USD con 2 líneas → 201 en `draft`, `number` nulo, totales de línea `90.00` y `25.00`, `merchandise_total_usd` `115.00`, `charges_total_usd` `0.00`, `landed_unit_cost_usd` igual al costo unitario; el stock no cambia; `PUT` reemplaza líneas (cambiar cantidad, quitar y agregar) y recalcula; `PUT` con `updated_at` viejo → 200 con `warnings: ["stale_data"]`; mismo producto dos veces → 422; cantidad `1.5` en unidad o `0.305` en metro → 422; costo `0` o con 7 decimales → 422; producto inactivo → 422; proveedor inactivo → 409 `inactive_supplier`; fecha futura (hora de Caracas) → 422; más de 500 líneas → 422; mismo proveedor y factura que otra compra no anulada → `warnings` con `duplicate_invoice`; `DELETE` de un borrador → 204 sin movimientos; `PUT` o `DELETE` de una compra confirmada → 409 `invalid_state` (RF-14/FR-004 a FR-007)
- [ ] T023 [P] [US2] Pruebas de confirmación en `backend/tests/test_purchases_confirm.py` (marca `db`): el caso de la independent test (stock 40 m, costo `2.750000`, movimiento `purchase` con `reference_type = 'purchase_item'`, `cost_before_usd` `2.000000` y `cost_after_usd` `2.750000`); stock −2 a 10 + 5 a 12 → costo `12.000000`; stock 0 con costo inicial 4 → `5.000000` y `cost_locked = true` (`PUT …/initial-cost` → 409 `cost_locked`); producto con stock 5 y sin costo → costo de la compra (FR-015); números `C-000001`, `C-000002` consecutivos y un borrador descartado no deja hueco; confirmar dos veces → 409 `invalid_state` y el stock sube una sola vez; un producto desactivado después de crear el borrador → 409 `inactive_products` con su SKU; respuesta del Admin con `cost_changes` y del Almacén sin ella; auditoría `purchase.confirmed` y `product.cost_updated` por producto (RF-16/FR-008 a FR-015, RN-09)
- [ ] T024 [P] [US2] Pruebas de concurrencia en `backend/tests/test_purchases_concurrency.py` (marca `db`): 20 hilos confirman 20 borradores del mismo producto con costos distintos; el stock final es la suma, el costo coincide con aplicar `weighted_average` en el orden de los números asignados, y los números van de `C-000001` a `C-000020` sin repetirse. Otra prueba: dos compras con los mismos dos productos en orden inverso se confirman a la vez sin bloqueo cruzado (FR-014, SC-006, R3)
- [ ] T025 [P] [US2] Pruebas de inmutabilidad en `backend/tests/test_purchase_immutability.py` (marca `db`, SQL directo con la sesión de la API): sobre una compra confirmada, `UPDATE purchase SET total_usd = …`, `UPDATE purchase_item SET quantity = 1`, `DELETE FROM purchase_item`, `INSERT INTO purchase_item …` y `DELETE FROM purchase` fallan con el mensaje del trigger; sobre un borrador, los mismos cambios funcionan; pasar de `draft` a `confirmed` sin `number` falla (FR-016, SC-002, R2)
- [ ] T026 [US2] Agregar a `MATRIX` de `backend/tests/test_permissions_matrix.py` las filas de `GET/POST /purchases`, `GET/PUT/DELETE /purchases/{id}` y `POST /purchases/{id}/confirm` (Admin y Almacén), y a `LEAK_CASES` de `backend/tests/test_no_cost_leak.py` las respuestas de lista, detalle, crear, guardar y confirmar para el Almacén, y `GET /products/{product_id}/movements` después de una compra confirmada (SC-005)

### Implementation for User Story 2

- [ ] T027 [US2] Crear `backend/app/api/purchase_schemas.py` con `PurchaseInput`, `PurchaseItemInput`, `PurchaseChargeInput` (`extra="forbid"`, decimales como cadena), `Purchase`, `PurchaseItemOut`, `PurchaseChargeOut`, `PurchaseSummary`, `PurchaseVoidOut`, `CostChange` y `purchase_out(purchase, *, role, cost_changes=None)`, que agrega `cost_changes` solo para el Admin; ningún esquema tiene `avg_cost_usd`, `cost_before_usd` ni `cost_after_usd` (R7, contracts/api.md)
- [ ] T028 [US2] Crear `backend/app/services/purchases.py` con la parte de borrador: `create_purchase` y `save_purchase` (validan proveedor activo, fecha no futura, productos activos y sin repetir, cantidades con `validate_quantity` según la unidad, costos con `validate_cost` en USD o `validate_ves` en Bs, hasta 500 líneas y 20 gastos; borran y reinsertan líneas y gastos con `line_number` por orden; recalculan todo con `_recalculate(db, purchase)`, que usa `domain/costing` y la tasa de `applicable_rate` (obligatoria con `require_rate` si la compra es en Bs o tiene gastos en Bs); calculan `warnings`: `stale_data`, `duplicate_invoice` y `charges_over_100_percent`), `discard_purchase` (borra gastos, líneas y compra, en ese orden, R2), `get_purchase` y `list_purchases(db, *, supplier_id, date_from, date_to, status, product_id, q, page, page_size)` (FR-004 a FR-007, R4)
- [ ] T029 [US2] Agregar a `backend/app/services/purchases.py` `confirm_purchase(db, *, actor, purchase_id) -> (Purchase, list[CostChange])` según research R3: compra con `FOR UPDATE` (409 `invalid_state` si no es `draft`); revalidar proveedor (409 `inactive_supplier`) y productos (409 `inactive_products` con `skus`); `_recalculate`; bloquear productos ordenados por `product_id`; por línea, `weighted_average` con `landed_unit_cost_usd`, `post_movement(type="purchase", reference_type="purchase_item", cost_before_usd, cost_after_usd)`, actualizar `avg_cost_usd` y `cost_locked = True`, y auditar `product.cost_updated`; tomar el número de `sequence_counter` con `FOR UPDATE` y formato `C-{n:06d}`; `status = 'confirmed'`, `confirmed_by`, `confirmed_at`; auditar `purchase.confirmed` (FR-008 a FR-015)
- [ ] T030 [US2] Crear `backend/app/api/purchases.py` con `GET /purchases`, `POST /purchases`, `GET /purchases/{id}`, `PUT /purchases/{id}`, `DELETE /purchases/{id}` y `POST /purchases/{id}/confirm` (`require_roles(ADMIN, WAREHOUSE)`; respuesta con `purchase_out` según el rol leído de la base) y registrar el router en `backend/app/main.py`
- [ ] T031 [US2] Crear en `frontend/src/components/purchases/` `purchase-lines.tsx` (tabla de líneas con el buscador de productos de `components/products`, cantidad con `DecimalInput` según la unidad, costo unitario, total de línea calculado en el navegador como cantidad × costo, columnas "Gasto asignado" y "Costo final" con los valores del servidor; en teléfono, tarjetas en lugar de tabla) y `purchase-totals.tsx` (mercancía, gastos y total en USD, y en Bs si aplica)
- [ ] T032 [US2] Crear `frontend/src/app/compras/editar/page.tsx` (`?id=`; sin `id` crea el borrador al primer guardado): cabecera con proveedor (solo activos), fecha, moneda, factura del proveedor y notas; `purchase-lines`; botones "Guardar y calcular", "Confirmar" (con diálogo de confirmación que recuerda que la compra no se podrá cambiar) y "Descartar"; muestra `warnings` y errores por campo; al confirmar va a `/compras/detalle/?id=`
- [ ] T033 [US2] Crear `frontend/src/app/compras/page.tsx` (lista paginada con número o "Borrador", fecha, proveedor, moneda, total y chip de estado; botón "Nueva compra") y `frontend/src/app/compras/detalle/page.tsx` (`?id=`, solo lectura con líneas, gastos, tasa, totales y quién registró y confirmó; los borradores redirigen a editar); ampliar los chips de `frontend/src/components/ui/status-chip.tsx` con `draft`, `confirmed` y `voided`
- [ ] T034 [US2] Ejecutar `pnpm api:types` y tipar las llamadas de compras

**Checkpoint**: US1 + US2 dan el MVP: proveedores y compras en USD con costo promedio, kardex y compras inmutables (criterio de terminado de la etapa, parte 1).

---

## Phase 5: User Story 6 - Carga de la tasa BCV (Priority: P2)

**Goal**: el Admin carga y corrige la tasa BCV por fecha, con histórico y auditoría; las compras confirmadas no cambian.

**Independent Test**: como Admin, cargar la tasa de hoy, corregirla y ver el histórico y la auditoría; Almacén y Vendedor no pueden cargarla.

### Tests for User Story 6 ⚠️

- [ ] T035 [P] [US6] Pruebas en `backend/tests/test_exchange_rates.py` (marca `db`): cargar `36.50` para hoy → 201 y auditoría `exchange_rate.created`; repetir la fecha → 409 `rate_exists`; fecha futura (hora de Caracas) → 422; `0`, negativo o 9 decimales → 422; `PUT /exchange-rates/{fecha}` corrige a `36.55`, guarda `updated_by` y audita 36,50 → 36,55; corregir una fecha sin tasa → 404; histórico de la más reciente a la más antigua; `GET /exchange-rates/applicable?date=` con tasas del 10/10 y del 13/10 devuelve la del 10/10 para el 11/10 y 404 para el 09/10 (RF-17/FR-025 a FR-027, RN-15)
- [ ] T036 [US6] Agregar a `MATRIX` las filas de `/exchange-rates` (solo Admin) y de `/exchange-rates/applicable` (Admin y Almacén)

### Implementation for User Story 6

- [ ] T037 [US6] Agregar a `backend/app/services/exchange_rates.py` `create_rate`, `correct_rate` y `list_rates` con `validate_rate`, el rechazo de fechas futuras con `domain/business_time.py` y la auditoría de R12; crear `backend/app/api/exchange_rates.py` con los cuatro endpoints del contrato y registrarlo en `backend/app/main.py` (FR-025 a FR-027)
- [ ] T038 [US6] Crear `frontend/src/app/tasas/page.tsx` (solo Admin): formulario "Tasa de hoy" con fecha (hoy por defecto) y valor; si ya existe, el botón pasa a "Corregir" y pide confirmación mostrando el valor anterior; histórico paginado con fecha, valor (`formatRate`), quién la cargó y la última corrección; tarjeta en `frontend/src/app/page.tsx` (Admin) que avisa si no hay tasa de hoy
- [ ] T039 [US6] Ejecutar `pnpm api:types` y tipar las llamadas de tasas

**Checkpoint**: la tasa está disponible para las compras en Bs y para la 1.3.

---

## Phase 6: User Story 3 - Compra en Bs con su tasa (Priority: P2)

**Goal**: compras en Bs que toman la tasa aplicable a su fecha, convierten cada costo a USD con 6 decimales y conservan la tasa al confirmarse aunque luego se corrija.

**Independent Test**: compra en Bs con tasa 40,00 de 10 unidades a 100,00 Bs → costo 2,500000 USD, total 1.000,00 Bs y 25,00 USD; al confirmarla, el promedio usa 2,500000.

### Tests for User Story 3 ⚠️

- [ ] T040 [P] [US3] Pruebas de compras en Bs en `backend/tests/test_purchases_draft.py` y `backend/tests/test_purchases_confirm.py` (marca `db`): 100,00 Bs con tasa 36,50 → `unit_cost_usd` `2.739726`, `line_total_ves` y `merchandise_total_ves` en Bs; costo en Bs con 3 decimales → 422; compra del 11/10 usa la tasa del 10/10 y la respuesta trae `exchange_rate_date`; sin tasa en o antes de la fecha → 409 `exchange_rate_missing`; un borrador refleja la tasa corregida al guardarse y al confirmarse; al confirmar, el promedio usa el costo en USD; una compra en USD sin tasa disponible se guarda con `exchange_rate` nulo (RF-15/FR-012, FR-013)
- [ ] T041 [P] [US3] Prueba en `backend/tests/test_purchase_immutability.py`: corregir la tasa de la fecha de una compra en Bs confirmada no cambia ni un céntimo de la compra ni de sus líneas (RN-05/FR-028, SC-009)

### Implementation for User Story 3

- [ ] T042 [US3] Completar en `backend/app/services/purchases.py` el camino en Bs de `_recalculate` si quedó pendiente en T028: `unit_cost_ves` obligatorio, `unit_cost_usd = ves_to_usd_cost(unit_cost_ves, rate)`, `line_total_ves = round_usd(quantity × unit_cost_ves)`, `merchandise_total_ves`; copiar `exchange_rate` y `exchange_rate_date`; al cambiar la moneda de un borrador, los costos se exigen de nuevo en la moneda nueva (FR-006, FR-012, FR-013)
- [ ] T043 [US3] En `frontend/src/app/compras/editar/page.tsx`: al elegir Bs, mostrar la tasa aplicable (`GET /exchange-rates/applicable`) con su fecha, y un aviso si no es del día de la compra; los costos se escriben en Bs (`DecimalInput` con 2 decimales) y se muestran también en USD tras guardar; al cambiar la moneda, pedir confirmación y vaciar los costos unitarios; si no hay tasa, explicar que el Admin debe cargarla

**Checkpoint**: compras en Bs con tasa congelada al confirmar.

---

## Phase 7: User Story 7 - Compra importada con gastos (Priority: P2)

**Goal**: gastos por porcentaje o monto fijo (USD o Bs), repartidos por valor; costo final por unidad que entra al costo promedio; gastos frecuentes del Admin.

**Independent Test**: factura de 1.000 USD (60 u. y 40 u. a 10,00) con comisión del 10 %, envío de 250 USD y entrega de 3.650 Bs a 36,50 → gastos 450,00, reparto 270,00 y 180,00, costo final 14,500000; al confirmar, el costo del producto con stock 0 pasa a 14,500000.

### Tests for User Story 7 ⚠️

- [ ] T044 [P] [US7] Pruebas de gastos en `backend/tests/test_purchases_draft.py` (marca `db`): el caso de la independent test con `amount_usd` `100.00`, `250.00` y `100.00`, `charges_total_usd` `450.00`, `allocated_charges_usd` `270.00` y `180.00` y `landed_unit_cost_usd` `14.500000`; tres líneas iguales y 100,00 de gastos → `33.34`, `33.33`, `33.33`; porcentaje `0`, `100.01` o con 3 decimales → 422; monto fijo sin moneda o con porcentaje → 422; gasto en Bs sin tasa → 409 `exchange_rate_missing`; gastos por más del 100 % de la factura → `warnings` con `charges_over_100_percent`; cambiar líneas recalcula los porcentajes y el reparto; más de 20 gastos → 422 (RN-20/FR-029 a FR-031)
- [ ] T045 [P] [US7] Pruebas en `backend/tests/test_purchases_confirm.py`: al confirmar la compra con gastos, `weighted_average` y el kardex usan `landed_unit_cost_usd`; con stock previo 10 a 12,00 y compra con costo final 14,50 por 10 u. → `13.250000`; una compra confirmada con gastos no admite cambiar gastos (en `backend/tests/test_purchase_immutability.py`: `UPDATE` y `DELETE` en `purchase_charge` fallan) (RN-20, RN-09/FR-011, FR-016)
- [ ] T046 [P] [US7] Pruebas en `backend/tests/test_charge_templates.py` (marca `db`): el Admin crea "Comisión de compra" (`percent`, `10.00`) y "Envío China–Venezuela" (`fixed`, USD, sin valor); nombre repetido entre activas → 409 `template_name_in_use`; `fixed` sin moneda o `percent` con moneda → 422; cambiar `charge_type` → 422; desactivar y reactivar; el Almacén ve solo las activas; editar la plantilla no cambia una compra que la usó; auditoría `charge_template.created` y `updated` (RF-14/FR-032)
- [ ] T047 [US7] Agregar a `MATRIX` las filas de `/charge-templates` (`GET` Admin y Almacén; `POST`/`PATCH` solo Admin) y a `LEAK_CASES` una compra con gastos (detalle y confirmación) para el Almacén (FR-033)

### Implementation for User Story 7

- [ ] T048 [US7] Completar en `backend/app/services/purchases.py` los gastos de `_recalculate` si quedaron pendientes en T028: validar cada `PurchaseChargeInput` según su tipo, `charge_amount_usd` con el total de mercancía y la tasa, `allocate_by_value` en el orden de `line_number`, `landed_unit_cost` por línea, `charges_total_usd` y `total_usd`; copiar `charge_template_id` sin leer la plantilla (FR-029 a FR-031, R1, R9)
- [ ] T049 [US7] Crear `backend/app/services/charge_templates.py` (crear, editar, listar, con nombre único entre activas sin distinguir mayúsculas y auditoría) y `backend/app/api/charge_templates.py` con `GET`, `POST` y `PATCH` del contrato; registrar el router en `backend/app/main.py` (FR-032)
- [ ] T050 [US7] Crear `frontend/src/components/purchases/purchase-charges.tsx`: sección plegable "Gastos" (abierta si la compra tiene gastos), botón "Agregar gasto frecuente" (lista de `GET /charge-templates`, que copia nombre, tipo, valor y moneda) y "Agregar gasto" a mano; cada gasto con descripción, tipo (porcentaje o monto), valor (`DecimalInput`) y moneda si es monto; muestra el monto en USD calculado por el servidor y el aviso `charges_over_100_percent`; integrarla en `frontend/src/app/compras/editar/page.tsx` y mostrar los gastos en `frontend/src/app/compras/detalle/page.tsx`
- [ ] T051 [US7] Crear `frontend/src/app/configuracion/gastos/page.tsx` (solo Admin; pestaña nueva en la navegación de Configuración): lista de gastos frecuentes con tipo, valor sugerido (`formatPercent` o monto con moneda) y estado; alta y edición en `Dialog`; activar y desactivar
- [ ] T052 [US7] Ejecutar `pnpm api:types` y tipar las llamadas de gastos frecuentes

**Checkpoint**: las importaciones registran sus gastos y el costo promedio usa el costo final.

---

## Phase 8: User Story 4 - Anulación de una compra (Priority: P2)

**Goal**: el Admin anula una compra confirmada con motivo, tras ver la vista previa; reversos en el kardex, costo deshecho con el costo final y alerta si el resultado no es válido.

**Independent Test**: anular una compra que llevó un producto de 10 m a 2,00 a 40 m a 2,75 → stock 10 m, costo 2,000000 y reverso con motivo en el kardex.

### Tests for User Story 4 ⚠️

- [ ] T053 [P] [US4] Pruebas en `backend/tests/test_purchase_void.py` (marca `db`): el caso de la independent test con movimiento `purchase_void`, `cost_before_usd` `2.750000` y `cost_after_usd` `2.000000`, compra en `voided`, `purchase_void` con motivo, y auditoría `purchase.voided` y `product.cost_updated`; con ventas o ajustes que dejan el stock por debajo de lo comprado → stock negativo permitido, costo conservado y alerta `purchase_void_cost` con `details` completos; una compra con gastos se deshace con `landed_unit_cost_usd`; `void-preview` devuelve por producto el stock y el costo resultantes y `keeps_cost`, sin escribir nada; motivo vacío o de 4 caracteres → 422; anular un borrador o una compra ya anulada → 409 `invalid_state`; `cost_locked` sigue en `true` (RN-14/FR-017 a FR-019)
- [ ] T054 [P] [US4] Pruebas en `backend/tests/test_alerts.py` (marca `db`): `GET /alerts` devuelve las abiertas por defecto y `?status=resolved` las resueltas; `resolve` marca `resolved_at`/`resolved_by` y audita `alert.resolved`; resolver dos veces → 409 `invalid_state`; `UPDATE alert SET details = …` directo falla (trigger); `GET /inventory/summary` del Admin cuenta `open_alerts` (FR-018, R8)
- [ ] T055 [US4] Agregar a `MATRIX` las filas de `void-preview`, `void`, `GET /alerts` y `resolve` (solo Admin) y a `backend/tests/test_purchase_immutability.py` que `UPDATE` y `DELETE` sobre `purchase_void` y cualquier cambio a una compra `voided` fallan

### Implementation for User Story 4

- [ ] T056 [US4] Agregar a `backend/app/services/purchases.py` `void_preview` y `void_purchase` según research R10: compra `confirmed` con `FOR UPDATE`; productos bloqueados en orden; por línea, `post_movement(type="purchase_void", quantity_delta=-quantity, allow_negative=True, reference_type="purchase_item", cost_before_usd, cost_after_usd)` y `undo_purchase` con `landed_unit_cost_usd`; si devuelve `None`, conservar el costo y `create_alert(type="purchase_void_cost", …)`; insertar `purchase_void`, pasar a `voided` y auditar. La vista previa usa el mismo cálculo sin escribir (FR-017 a FR-019)
- [ ] T057 [US4] Agregar `GET /purchases/{id}/void-preview` y `POST /purchases/{id}/void` a `backend/app/api/purchases.py` (solo Admin), y crear `backend/app/api/alerts.py` con `GET /alerts` y `POST /alerts/{id}/resolve` (solo Admin), registrado en `backend/app/main.py`; ampliar `GET /inventory/summary` en `backend/app/services/inventory.py` con `open_alerts` (Admin) y `draft_purchases` (Admin y Almacén)
- [ ] T058 [US4] Crear `frontend/src/components/purchases/void-dialog.tsx` (pide el motivo, muestra la vista previa por producto con stock y costo antes y después, destaca los que quedan en cero o negativo o conservan el costo, y exige confirmar) y agregar el botón "Anular" (solo Admin) en `frontend/src/app/compras/detalle/page.tsx`, que después muestra el motivo, quién anuló y cuándo
- [ ] T059 [US4] Ampliar `frontend/src/app/pendientes/page.tsx` con la sección "Alertas" (producto, compra enlazada, stock y costos de `details`, y botón "Marcar revisada") y la tarjeta del inicio de Admin en `frontend/src/app/page.tsx` con las alertas abiertas y los borradores de compra; tarjeta de borradores también para el Almacén
- [ ] T060 [US4] Ejecutar `pnpm api:types` y tipar las llamadas de anulación y alertas

**Checkpoint**: criterio de terminado de la etapa: las pruebas del costo promedio, incluida la anulación, pasan con los casos compartidos.

---

## Phase 9: User Story 5 - Consulta de compras (Priority: P3)

**Goal**: listar compras con filtros y enlazar el kardex con su compra.

**Independent Test**: con 3 compras de dos proveedores, filtrar por uno y por un rango de fechas; desde el kardex de un producto, abrir la compra enlazada.

### Tests for User Story 5 ⚠️

- [ ] T061 [P] [US5] Pruebas en `backend/tests/test_purchases_draft.py` (o un archivo `backend/tests/test_purchases_list.py`, marca `db`): filtros `supplier_id`, `from`/`to`, `status` (`draft`, `confirmed`, `voided`), `product_id` y `q` (número o factura del proveedor), combinados; orden más reciente primero; paginación con `page_size` máximo 100; los movimientos de compra de `GET /products/{id}/movements` traen `purchase: {id, number}` (RF-08/FR-020, FR-021)

### Implementation for User Story 5

- [ ] T062 [US5] Completar los filtros de `list_purchases` en `backend/app/services/purchases.py` si quedaron pendientes en T028, y agregar `purchase: {id, number}` al esquema del movimiento en `backend/app/api/product_schemas.py` cuando `reference_type = 'purchase_item'` (un solo `JOIN`, sin consultas por fila)
- [ ] T063 [US5] Agregar a `frontend/src/app/compras/page.tsx` los filtros (proveedor, rango de fechas, estado, producto con el buscador y búsqueda por número o factura) y, en la tabla de kardex de `frontend/src/components/products/`, el enlace a `/compras/detalle/?id=` en los movimientos de compra y de anulación

**Checkpoint**: todas las historias funcionan por separado.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: documentación (RNF-09), validación final y revisión.

- [ ] T064 [P] Actualizar `docs/modelo-de-datos.md` con los cambios listados en data-model.md ("Cambios a `docs/modelo-de-datos.md`"): §1, §3.1, §3.4 y §3.5
- [ ] T065 [P] Actualizar `docs/arquitectura.md`: servicios `purchases`, `exchange_rates`, `alerts` y `domain/costing.py` en la estructura del backend; flujo de confirmación y anulación de compras (R3, R10); tasa aplicable por fecha (R6); glosario (`sequence_counter`, `void`, `alert`, `applicable_rate`) y la matriz por endpoint
- [ ] T066 [P] Actualizar `docs/guia-de-estilos.md` §9 con los componentes nuevos (líneas de compra, sección de gastos, totales, diálogo de anulación y chips de estado de compra)
- [ ] T067 [P] Actualizar `CHANGELOG.md` en "Sin publicar" con la etapa 1.2 (RF-13 a RF-17, RN-09, RN-14, RN-15, RN-20) y `docs/plan-de-fases.md` con su estado
- [ ] T068 Ejecutar `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest` (con `DATABASE_URL`), la migración subir–bajar–subir, `pnpm typecheck` y `pnpm build`, y corregir lo que falle
- [ ] T069 Recorrer los escenarios manuales 1–10 de `quickstart.md` en local, en PC y con ancho de teléfono de 360 px; medir SC-003 (compra de 10 líneas < 5 min) y SC-011 (gastos de una importación < 1 min); anotar cualquier desviación como tarea nueva
- [ ] T070 Ejecutar `/security-review` y `/code-review` sobre la rama `003-proveedores-compras`, corregir los hallazgos confirmados y repetir T068. Requisito para integrar a `main` (constitución, "Flujo de trabajo")
- [ ] T071 **Después de integrar a `main` (dueño y asistente):** con el despliegue terminado, cargar la tasa del día, registrar y confirmar una compra real en producción y comprobar el kardex y el costo; restaurar el respaldo nocturno en local (plan de fases, definición de terminado). Cerrar la etapa como versión `0.3.0` (CHANGELOG, etiqueta `v0.3.0` y release en GitHub) y empezar la carga del inventario real (plan de fases §3)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (fase 1)**: sin dependencias.
- **Foundational (fase 2)**: depende de Setup; bloquea todas las historias. T006 → T007 → T008 en secuencia; T002–T005 y T013–T015 en paralelo; T009–T012 después de T008.
- **US1 (fase 3)**: depende de la fase 2.
- **US2 (fase 4)**: depende de la fase 2 y de US1 (las compras necesitan proveedores; las pruebas usan `make_supplier`, así que el backend de US2 puede empezar en paralelo con el de US1).
- **US6 (fase 5)**: depende de la fase 2; independiente de US1 y US2.
- **US3 (fase 6)**: depende de US2 (servicio y pantalla de compras) y de US6 (carga de tasas para la pantalla; las pruebas usan `make_rate`).
- **US7 (fase 7)**: depende de US2; los gastos en Bs, de US6.
- **US4 (fase 8)**: depende de US2; las pruebas con gastos, de US7.
- **US5 (fase 9)**: depende de US2.
- **Polish (fase 10)**: depende de las historias que se entreguen. T070 (revisión) va justo antes de integrar y T071 (validación en producción) después.

### User Story Dependencies

- **US1 (P1)**: solo la fase 2.
- **US2 (P1)**: la fase 2 y US1.
- **US6 (P2)**: solo la fase 2.
- **US3 (P2)**: US2 y US6.
- **US7 (P2)**: US2 (y US6 para gastos en Bs).
- **US4 (P2)**: US2 (y US7 para deshacer con el costo final).
- **US5 (P3)**: US2.
- Las filas de `MATRIX` y `LEAK_CASES` de cada historia dependen de T012 y de la matriz existente.

### Within Each User Story

- Pruebas primero (deben fallar) → servicios → endpoints → frontend → tipos generados.
- `services/purchases.py` lo amplían varias historias (T028, T029, T042, T048, T056, T062): esas tareas van en secuencia.
- Cada historia termina con su checkpoint antes de pasar a la siguiente prioridad.

### Parallel Opportunities

- Fase 2: T002–T005 y T013–T015 en paralelo; T011 en paralelo con T009 y T010.
- US1 y US6 completas en paralelo con el backend de US2 (archivos distintos), coordinando las filas de `MATRIX` y `LEAK_CASES`.
- Dentro de cada historia, las pruebas marcadas [P] en paralelo.
- Fase 10: la documentación T064–T067 en paralelo.

---

## Parallel Example: Foundational

```bash
Task: "Helpers de redondeo en backend/app/domain/money.py"
Task: "Funciones puras en backend/app/domain/costing.py"
Task: "Casos compartidos en backend/tests/test_costing_domain.py"
Task: "normalize_rif en backend/app/domain/rif.py"
Task: "formatVes, formatRate y formatPercent en packages/shared/src/format.ts"
```

## Parallel Example: User Story 2

```bash
# Pruebas de US2 juntas:
Task: "Borrador en backend/tests/test_purchases_draft.py"
Task: "Confirmación en backend/tests/test_purchases_confirm.py"
Task: "Concurrencia en backend/tests/test_purchases_concurrency.py"
Task: "Inmutabilidad en backend/tests/test_purchase_immutability.py"
```

---

## Implementation Strategy

### MVP First (US1 + US2)

1. Fase 1 (Setup) y fase 2 (Foundational): dominio de costos con casos compartidos, tablas, triggers y kardex con costo.
2. Fase 3 (US1): proveedores.
3. Fase 4 (US2): compras en USD con costo promedio e inmutabilidad.
4. **Parar y validar**: escenarios 1 y 3 de `quickstart.md`. Con esto ya se pueden registrar compras locales en USD.

### Incremental Delivery

1. Setup + Foundational → base lista.
2. US1 + US2 → compras en USD (MVP).
3. US6 → tasa BCV (también la usará la 1.3).
4. US3 → compras en Bs.
5. US7 → importaciones con gastos y costo final (necesario antes de cargar el inventario real).
6. US4 → anulación con alertas (criterio de terminado: pruebas del costo con anulación).
7. US5 → consulta y enlaces desde el kardex.
8. Polish → documentación, revisión (T070), integración a `main`, validación en producción y versión 0.3.0 (T071).

---

## Notes

- [P] = archivos distintos y sin dependencias pendientes.
- Cada commit referencia los RF/RN/FR que toca, en español.
- Las pruebas que necesitan Postgres llevan la marca `db` y se saltan sin `DATABASE_URL`.
- Ningún código fuera de `post_movement` cambia el stock; ningún código fuera de `services/purchases.py` cambia `avg_cost_usd` por compras; ningún código fuera de `domain/money.py` y `domain/costing.py` redondea montos.
- Los esquemas de respuesta por rol se eligen con el rol leído de la base, nunca con el del token (ADR-0008).
