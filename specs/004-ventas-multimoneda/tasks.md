---

description: "Tareas de la etapa 1.3: ventas multimoneda, pagos mixtos, descuentos y apertura de caja"
---

# Tasks: Ventas multimoneda, pagos mixtos, descuentos y apertura de caja (etapa 1.3)

**Input**: documentos de diseño en `specs/004-ventas-multimoneda/`

**Prerequisites**: plan.md, spec.md, research.md (R1–R17), data-model.md, contracts/api.md, quickstart.md

**Tests**: se incluyen, porque los exigen tanto la constitución como la especificación:

- **Constitución, principio VII**: conversión y redondeo USD↔Bs, pagos mixtos y vuelto, cm→m y validación de unidades, kardex y reversos, permisos por rol y sincronización sin duplicados.
- **Especificación**: SC-003 a SC-010.

Cada prueba nombra en su docstring el RF/RN del PRD y el FR/SC de la especificación que verifica. Las pruebas de cada historia se escriben primero y deben fallar antes de implementar.

**Organization**: las tareas se agrupan por historia de usuario de spec.md (US1–US7), y cada historia se puede probar por separado. Las fases siguen la prioridad:

- P1: US1, US2 y US3;
- P2: US5, US4 y US6;
- P3: US7.

US5 va antes que US4 porque es la más pequeña y completa la venta básica.

**Trazabilidad con el PRD** (constitución, "Flujo de trabajo" y principio VII):

| FR de la especificación | RF/RN/RNF del PRD |
|---|---|
| FR-001 a FR-004 | RN-11 (ADR-0003) |
| FR-005 a FR-009 | RF-29, RF-30, RN-16, RF-18 |
| FR-010 a FR-019 | RF-18, RF-20, RF-21, RF-26, RF-28, RN-01, RN-02, RN-05, RN-11, RN-13, RN-18 |
| FR-020 a FR-029 | RF-22, RN-07 |
| FR-030 a FR-032 | RN-10 |
| FR-033 a FR-039 | RF-23, RF-24, RF-25, RN-04, RN-06 |
| FR-040 | ADR-0004, principio VII |
| FR-041 a FR-044 | RF-27, RN-12 |
| FR-045 a FR-051 | matriz de permisos, RF-42, RF-46, RNF-02, RNF-05, RNF-07 |

Los commits y las docstrings de las pruebas citan el RF/RN del PRD y el FR de la especificación, por ejemplo `RN-06/FR-035`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede hacer en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia a la que pertenece (US1…US7)
- Rutas relativas a la raíz del repositorio

## Path Conventions

- Backend: `backend/app/`, `backend/tests/`, `backend/migrations/`
- App interna: `frontend/src/`
- Compartido: `packages/shared/` (casos en `packages/shared/test-vectors/`)
- Comandos del backend desde `backend/` (`uv run …`); los de Node desde la raíz (`pnpm …`)
- Decimales en JSON siempre como cadenas (ADR-0004); en Python siempre `Decimal`; redondeo solo en `domain/money.py`, `domain/costing.py`, `domain/sale_math.py` y `packages/shared/src/money.ts`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: dependencias nuevas, ejecutor de pruebas de TypeScript y casos compartidos (R1, R2).

- [X] T001 Agregar `decimal.js` a `packages/shared/package.json` (dependencia) y `dexie` a `frontend/package.json` (dependencia), con versiones exactas publicadas hace al menos dos semanas; `pnpm install` y comprobar que `pnpm-lock.yaml` cambia solo por ellas (R1, R4)
- [X] T002 Agregar a `packages/shared/package.json` el script `"test": "node --test src/**/*.test.ts"`; a la raíz `package.json` el script `"test": "pnpm -r --if-present test"`; y a `.github/workflows/ci.yml`, en el trabajo `frontend`, el paso `pnpm test` antes de `pnpm typecheck` (R2)
- [X] T003 Crear `packages/shared/test-vectors/money.json` con la estructura `{"quantities": [...], "sales": [...], "payments": [...]}` y estos casos de la spec y de research R1:
  - **Cantidades**: `30` cm → `0.30`; `0,305` m → error "admite como máximo 2 decimales"; `30,5` cm → error; `1.5` en unidad → error "solo admite cantidades enteras"; `0` → error.
  - **Venta de la US2**: 2 × `3.25` + `0.30` × `4.00` a tasa `36.50` → subtotales `6.50` y `1.20`, total `7.70`, Bs `281.05`.
  - **Descuentos**: línea `20.00` con `10 %` → descuento `2.00`, neto `18.00`; descuento total de `5.00` sobre netos `10.00`, `10.00` y `10.00` → cada parte se redondea a `1.67` y el residuo `-0.01` va a la primera de mayor neto, así que el reparto es `1.66`, `1.67` y `1.67`, con la suma exacta; descuento del `100 %` → `0.00`.
  - **Pagos**: venta de `50.00` con `20.00` en `cash_usd`, `730.00` en `mobile_payment` (→ `20.00`) y `10.00` en `zelle` → saldo `0.00`.
  - **Saldo exacto en Bs**: saldo `12.34` a tasa `36.50` → sugerido `450.41`, que cubre `12.34`.
  - **Vuelto**: excedente `2.30` → `83.95` en `cash_ves`; vuelto menor que el excedente → sobrepago `0.30`; vuelto mayor → error.
  - **Bordes de redondeo**: `x,xx5` en Bs (`1.01` × `36.50` = `36.865` → `36.87`) y en el reparto.
  - Cada caso con entradas y resultados esperados como cadenas (R1, FR-040, SC-003)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: cálculo compartido, tablas y triggers, identidad del equipo, cola de salida en el servidor y en el navegador, y la base de pruebas que necesitan todas las historias.

**⚠️ CRITICAL**: ninguna historia empieza antes de terminar esta fase.

- [X] T004 [P] Agregar a `backend/app/domain/money.py` `ves_to_usd(amount_ves, rate) -> Decimal` (`round_usd(amount_ves / rate)`, RN-06) y `usd_to_ves(amount_usd, rate) -> Decimal` (`round_usd(amount_usd * rate)`, RN-02); actualizar el docstring del módulo (ADR-0004)
- [X] T005 [P] Crear `backend/app/domain/sale_math.py` con las dataclasses inmutables `LineInput` (`id`, `unit_price_usd`, `quantity`, `discount_type`, `discount_value`), `MoneyInput` (`method`, `currency`, `amount`) y `SaleInput` (`rate`, `lines`, `discount_type`, `discount_value`, `payments`, `change`), y la función pura `compute_sale(sale: SaleInput) -> SaleResult`, siguiendo la tabla de ADR-0004 y research R1:
  - Por línea: `line_subtotal_usd = round_usd(precio × cantidad)`; descuento propio en monto (> 0 y ≤ subtotal) o en porcentaje (`round_usd(subtotal × % ÷ 100)`, % > 0 y ≤ 100).
  - Venta: `subtotal_usd` = Σ netos de línea; descuento total sobre esa suma; reparto proporcional al neto de cada línea con `round_usd`, residuo a la línea de mayor neto (la primera si hay empate) y suma exacta; `total_usd`; `total_ves = usd_to_ves(total, tasa)`.
  - Pagos: `amount_usd` de cada uno (VES → `ves_to_usd`; USD y USDT → 1:1); `paid_usd`, `balance_usd`, `balance_ves = usd_to_ves(balance)` y `excess_usd`.
  - Vuelto: `change_usd`, que debe ser ≤ excedente (si no, `ValueError` con mensaje en español), y `overpaid_usd = excess − change`.
  - Validaciones: los límites de R16 (100 líneas, 10 pagos, 5 vueltos) lanzan `ValueError`.
  - Sin acceso a la base de datos (RF-21, RF-22, RF-25, RN-02, RN-04, RN-06)
- [X] T006 [P] Crear `backend/tests/test_sale_math.py` (sin marca `db`). Recorre todos los casos de `packages/shared/test-vectors/money.json`: cantidades con `domain/units.py` (metros `cm ÷ 100`) y ventas y pagos con `domain/sale_math.py`. Además comprueba, con 200 ventas aleatorias de semilla fija, que la suma del reparto es exactamente el descuento total, y con 200 saldos y tasas entre `1.01` y `1000`, que `ves_to_usd(usd_to_ves(saldo))` devuelve el saldo (RN-02, RN-06/FR-013, FR-021, FR-036, FR-040, SC-003)
- [X] T007 [P] Crear `packages/shared/src/money.ts`, con `Decimal` de `decimal.js` configurado con `rounding: Decimal.ROUND_HALF_UP` y precisión suficiente:
  - `validateQuantity(text, unitDecimals, enteredUnit: "m" | "cm" | "unit")`, que convierte cm→m y devuelve la cantidad como cadena o el mismo mensaje de error en español que `domain/units.py`;
  - `computeSale(input)`, con la misma entrada y salida que `compute_sale` en cadenas;
  - `suggestedVes(balanceUsd, rate)`.
  Solo sintaxis de TypeScript borrable (sin `enum` ni `namespace`). Exportarlo desde `packages/shared/src/index.ts` (R1, R2)
- [X] T008 [P] Crear `packages/shared/src/money.test.ts` con `node:test` y `node:assert`: lee `../test-vectors/money.json` y recorre todos los casos contra `money.ts`. Comprobar que `pnpm test` pasa (FR-040, SC-003)
- [X] T009 [P] Crear `packages/shared/src/uuid.ts` con `uuidv7(): string` (RFC 9562: 48 bits de milisegundos, versión 7, variante 10 y el resto de `crypto.getRandomValues`) y un caso en `packages/shared/src/uuid.test.ts` que verifica el formato y el orden creciente de 1.000 ids; exportarlo desde `index.ts` (R4)
- [X] T010 [P] Crear `backend/app/domain/series.py` con `series_for(n: int) -> str` (1 → `A`, 26 → `Z`, 27 → `AA`, 702 → `ZZ`, 703 → `AAA`; más de 3 letras → `ValueError`). Crear también `backend/app/domain/customer_document.py` con `normalize_document(text) -> str`: con `V` o `E` sin guiones es siempre cédula `^[VE]-\d{6,8}$` (acepta `v12345678`, `V 12.345.678`); `V123456789` → `ValueError` "Para un RIF de persona natural escribe los guiones, por ejemplo V-12345678-9"; escrito con guiones y dígito verificador (`V-12345678-9`), o con `J`, `G`, `P` o `C`, es RIF con `normalize_rif`. Pruebas de ambos en `backend/tests/test_series_domain.py` y `backend/tests/test_customer_document.py` (R3, R11)
- [X] T011 Agregar a `backend/app/db/models.py` los modelos `Device`, `CashSession`, `Customer`, `PaymentMethod`, `Sale`, `SaleItem`, `Payment`, `SaleVoid`, `DiscountAuthorization` y `OutboxOperation`, exactamente como en data-model.md, con estas reglas literales:
  - **`device`**: `name` "1–60 caracteres"; `series` "`^[A-Z]{1,3}$`, única"; `last_sequence_number` "≥ 0"; `token_hash` único; `revoked_at`/`revoked_by` "Se fijan juntos".
  - **`cash_session`**: `opening_float_ves` y `opening_float_usd` "≥ 0"; `status` "`open`"; `outbox_operation_id` único.
  - **`customer`**: `name` "2–100 caracteres"; `document_id` "Cédula `^[VE]-\d{6,8}$` o RIF `^[JGVEPC]-\d{8}-\d$`; índice único"; `phone` "Hasta 30 caracteres".
  - **`payment_method`**: `code` como clave; `currency` "`VES`, `USD`, `USDT`".
  - **`sale`**:
    - único `(series, sequence_number)`, `number` único y `sequence_number` ≥ 1;
    - `discount_type` "`amount`" o "`percent`", junto con `discount_value` y `discount_usd`;
    - `discount_authorization_method` "`pin`, `request`, `admin_self`", solo con descuento;
    - `discount_authorization_id` único;
    - `total_usd` ≥ 0;
    - `outbox_operation_id` único.
  - **`sale_item`**:
    - único `(sale_id, line_number)` y `quantity` "> 0";
    - `entered_unit` "`m`, `cm` o `unit`";
    - `item_discount_authorization_id` único;
    - `line_total_usd` "≥ 0".
  - **`payment`**: `kind` "`sale_payment`, `change`, `void_refund`, `void_change`"; `amount` "> 0"; `reference` "1–60 caracteres"; `sale_void_id` "Solo en `void_refund` y `void_change`".
  - **`sale_void`**: `sale_id` único; `reason` "5–500 caracteres".
  - **`discount_authorization`**: `method` "`pin` o `request`"; `status` "`pending`, `approved` o `rejected`"; `decided_by`/`decided_at` juntos con `approved` o `rejected`; `discount_value` ≤ `requested_value`; `rejection_reason` "hasta 200 caracteres".
  - **`outbox_operation`**: `operation_type` "`cash_session.open`, `sale.create`"; `status` "`processed` o `rejected`"; `schema_version` 1.
  - **FK nuevas**: `UserSession.device_id`, `StockMovement.device_id` y `AuditLog.device_id` → `device.id`, y se quitan los comentarios "Sin FK hasta la etapa 1.3".
- [X] T012 Crear la migración `backend/migrations/versions/0006_ventas_y_caja.py` (revisión `0006`, anterior `0005`) con las diez tablas y los `CHECK` de T011. Incluye además:
  - **Índices**: único parcial `cash_session (device_id) WHERE status = 'open'`; `sale (business_date DESC)`, `sale (seller_id, business_date)`, `sale (customer_id)` y `sale_item (product_id)`; `discount_authorization (status, requested_at) WHERE status = 'pending'`.
  - **Datos iniciales**: los seis métodos de pago de data-model.md con su `sort_order`, e `INSERT INTO sequence_counter VALUES ('device_series', 1)`.
  - **Tipos de alerta**: amplía `ck_alert_type_valid` con `negative_stock`, `price_mismatch`, `total_mismatch`, `rate_mismatch`, `discount_review` e `inactive_user_sync`.
  - **FK de `device_id`**: en `user_session`, `stock_movement` y `audit_log`.
  - **Triggers de research R9**:
    - solo inserción (`reject_change()` de `0004`) en `sale`, `sale_item`, `payment`, `sale_void` y `outbox_operation`;
    - `DELETE` rechazado en `device`, `cash_session`, `customer`, `discount_authorization` y `payment_method`;
    - `device`: solo fijar `revoked_at`/`revoked_by` una vez y aumentar `last_sequence_number`;
    - `cash_session`: solo `status` puede cambiar;
    - `discount_authorization`: solo `pending` → `approved` (con `decided_by`/`decided_at`; `discount_value` y `discount_usd` pueden bajar, nunca subir; el trigger solo lo admite, el cálculo lo hace el servicio) o `rejected`;
    - `payment`: rechaza la fila si el método exige referencia y `reference` es nula.
  - **`downgrade`**: lo quita todo y restaura el `CHECK` de alertas.
  - Comprobar `alembic upgrade head`, `downgrade 0005` y `upgrade head` contra el Postgres local (FR-044, SC-010)
- [X] T013 Ampliar `backend/tests/conftest.py`:
  - Agregar a `TABLES` las tablas nuevas, en orden de dependencias: `payment`, `sale_void`, `sale_item`, `sale`, `discount_authorization`, `cash_session`, `customer`, `outbox_operation` y `device`.
  - Agregar `payment_method` y `sequence_counter` a `SEEDED_TABLES`, para que cada prueba empiece con los métodos y `device_series = 1`.
  - Fábricas:
    - `make_device(name="Mostrador", revoked=False) -> tuple[Device, str]`: inserta con el ORM y devuelve el token en claro;
    - `device_headers(headers, token)`: agrega `X-Device-Token`;
    - `open_cash_session(headers, token, float_ves="0.00", float_usd="0.00") -> dict`: por la API `POST /sync/operations`;
    - `make_sale(headers, token, cash_session_id, items=[(product, quantity, entered_unit)], payments=[(method, amount, reference)], change=[], discount=None, customer=None, sequence_number=None, seller_id=None, rate=None) -> dict`: arma un `SaleInput` válido con precios del producto y totales de `compute_sale`, y lo envía por `POST /sync/operations`.
  - Las fábricas por la API funcionan desde que existen los endpoints (T018, T031)
- [X] T014 Crear `backend/app/services/devices.py`:
  - `register_device(db, *, actor, name) -> tuple[Device, str]`: toma y avanza la fila `device_series` con `FOR UPDATE`, genera la serie con `series_for`, crea un token de 32 bytes con `secrets.token_urlsafe` y guarda `sha256` en hex; audita `device.registered`.
  - `revoke_device(db, *, actor, device_id)`: 409 `invalid_state` si ya estaba revocado; audita `device.revoked`.
  - `list_devices(db)`.
  - `device_from_token(db, token) -> Device`: 403 `device_required` si falta o no existe; devuelve el equipo aunque esté revocado.
  - `ensure_active(device, *, at: datetime | None = None)`: 403 `device_revoked` si está revocado y `at` es nulo o posterior a `revoked_at` (FR-002).
  - (R3, FR-001 a FR-004)
- [X] T015 Agregar a `backend/app/api/deps.py` la dependencia `CurrentDevice`, que lee `X-Device-Token`, llama a `device_from_token` y devuelve el `Device` (aunque esté revocado), y `ActiveDevice`, que además llama a `ensure_active(device)` para `/devices/current` y las autorizaciones de descuento. Se combina con `require_roles(...)` en los endpoints de mostrador; la prueba de declaraciones de rutas (`test_route_declarations.py`) debe seguir pasando (R3)
- [X] T016 Crear `backend/app/services/sync.py` con `process_operation(db, *, device, user, operation: OutboxOperationIn) -> tuple[int, dict]`:
  1. Bloquea la clave con `pg_advisory_xact_lock(hashtext(id::text))`, así dos envíos simultáneos del mismo id se serializan.
  2. Busca la fila de `outbox_operation` con ese id; si existe, devuelve su `http_status` y su `result` o `error` sin volver a procesar.
  3. Si no existe, llama a `ensure_active(device, at=operation.created_at)`: una operación creada después de revocar el equipo es un rechazo 403 `device_revoked`, guardado como los demás rechazos; una anterior se procesa (FR-002). Luego despacha por `operation_type` a un registro de manejadores (`HANDLERS: dict[str, Callable]`, vacío en esta tarea). Tipo desconocido → 409 `operation_type_unknown`.
  4. Inserta la fila con su resultado: `processed`/200, o `rejected` con `http_status` y `error` para cualquier `ApiError` 403 `device_revoked`, 409 o 422 (los cambios del manejador se deshacen con un punto de guardado antes de guardar el rechazo). Los demás errores se propagan sin guardar nada (son transitorios).
  5. Todo ocurre en la transacción de la petición; la fila y lo que crea el manejador se confirman juntos (R4, FR-018).
  - (R4, FR-017)
- [X] T017 [P] Ampliar `backend/app/services/alerts.py`: actualizar el docstring con los tipos de R6 y agregar `create_sale_alert(db, *, type, sale, details)`, que fija `entity_type = 'sale'` e incluye `sale_number` en `details` (R6)
- [X] T018 Crear `backend/app/api/sync.py` con `POST /sync/operations` (`require_roles(ADMIN, SELLER)` + `CurrentDevice`). Entrada `OutboxOperationIn` con `extra="forbid"`: `id` UUID, `operation_type`, `schema_version == 1`, `created_at` con zona horaria y `payload` dict. Llama a `process_operation`, confirma la transacción y responde con el `http_status` y el cuerpo guardados (los rechazos con el formato de error común). Registrar el router en `backend/app/main.py` (R4)
- [X] T019 [P] Crear `backend/tests/test_sync_idempotency.py` (marca `db`) con un manejador de prueba registrado en `HANDLERS` mediante un fixture:
  - reenvío del mismo id → mismo código y cuerpo, y el manejador se ejecuta una sola vez;
  - 10 envíos simultáneos del mismo id con hilos y sesiones separadas → una sola ejecución (SC-004);
  - un rechazo 422 guardado se repite igual;
  - un error inesperado no guarda la fila y el reintento vuelve a ejecutar;
  - tipo desconocido → 409 `operation_type_unknown`;
  - sin `X-Device-Token` → 403 `device_required`;
  - equipo revocado: una operación con `created_at` anterior a la revocación se procesa, y una posterior → 403 `device_revoked`, guardado y repetido al reenviar (FR-002);
  - Almacén → 403.
  - (ADR-0003/FR-017, SC-004)
- [X] T020 [P] Crear `frontend/src/lib/device/device-store.ts` con Dexie (base `sht-mostrador`, versión 1, tablas `device` y `outbox`):
  - `getDevice()`, `saveDevice({id, name, series, token, nextSequence})`, `clearDevice()`;
  - `takeSequenceNumber()`: lee y aumenta `nextSequence` en una transacción de Dexie;
  - `syncSequence(serverLast)`: fija `nextSequence = max(local, serverLast + 1)`;
  - llamar a `navigator.storage.persist()` la primera vez que se guarda el equipo (R3, R5, ADR-0003).
- [X] T021 Crear `frontend/src/lib/outbox/outbox.ts`:
  - `enqueue(type, payload) -> {id}`: id con `uuidv7()`, estado `pending` y hora del equipo; devuelve el id.
  - `flush()`: envía en orden por `createdAt`, de a una, a `POST /sync/operations` con el cliente de `lib/api/client.ts` y la cabecera `X-Device-Token`.
    - 200 → `sent`, con el resultado;
    - 409 o 422 → `rejected`, con `code` y mensaje, y sigue con la siguiente;
    - red, 5xx o 401 → se detiene y reintenta después.
  - Disparadores de `flush()`: al encolar, en `online`, al montar la app y con un temporizador de 30 s con espera creciente hasta 5 min si falla.
  - `waitFor(id, timeoutMs)`: espera el resultado de una operación para la pantalla.
  - `usePendingCount()`: hook de React que cuenta `pending` y `rejected`.
  - (R4, FR-017)
- [X] T022 [P] Agregar a `packages/shared/src/audit-actions.ts` el grupo "Ventas y caja" con las acciones de research R15 y sus etiquetas: `device.registered` "Equipo registrado", `device.revoked` "Equipo revocado", `cash_session.opened` "Caja abierta", `sale.discounted` "Venta con descuento", `discount_authorization.requested` "Descuento solicitado", `discount_authorization.approved` "Descuento aprobado", `discount_authorization.rejected` "Descuento rechazado" y `sale.voided` "Venta anulada" (FR-050)
- [X] T023 [P] Agregar a `NAV_ITEMS` en `frontend/src/components/app-shell.tsx`: `Vender` (`/vender/`, ícono `ShoppingBag`, Admin y Vendedor), `Ventas` (`/ventas/`, ícono `ReceiptText`, Admin y Vendedor), `Caja` (`/caja/`, ícono `Wallet`, Admin y Vendedor) y, en Configuración, `Equipos` (`/configuracion/equipos/`, solo Admin). Agregar también:
  - en la barra, el indicador "Ventas pendientes de envío: N" con `usePendingCount()`, visible solo si N > 0, que enlaza a un panel con las operaciones pendientes y rechazadas y su motivo;
  - un aviso de confirmación al cerrar sesión con operaciones pendientes (R14, ADR-0003)

**Checkpoint**: base lista. Pasan `uv run pytest` (dominio de la venta, series, documentos e idempotencia) y `pnpm test` (los mismos casos de dinero), y la migración sube y baja.

---

## Phase 3: User Story 1 - Equipo de mostrador y apertura de caja (Priority: P1) 🎯 MVP

**Goal**: el Admin registra el equipo con su serie y el Vendedor abre caja con fondo, con aviso de tasa faltante.

**Independent Test**: registrar dos equipos (`A`, `B`), revocar uno y registrar otro (`C`); abrir caja en `A` con 500,00 Bs y 20,00 USD; una segunda apertura se rechaza; sin tasa del día, aviso con la fecha de la última.

### Tests for User Story 1 ⚠️

> Escribir primero y comprobar que fallan.

- [X] T024 [P] [US1] Pruebas en `backend/tests/test_devices.py` (marca `db`):
  - `POST /devices` como Admin → serie `A` y `token` en la respuesta, que no aparece en `GET /devices`;
  - el segundo equipo recibe `B`; tras revocar `B`, el siguiente recibe `C`;
  - revocar dos veces → 409 `invalid_state`;
  - `GET /devices/current` con el token → equipo, caja abierta (o nula) y `last_sequence_number`;
  - token inválido → 403 `device_required`; equipo revocado → 403 `device_revoked`;
  - auditoría `device.registered` y `device.revoked`;
  - nombre vacío o de más de 60 caracteres → 422.
  - (RN-11/FR-001 a FR-004)
- [X] T025 [P] [US1] Pruebas en `backend/tests/test_cash_sessions.py` (marca `db`):
  - apertura por `POST /sync/operations` (`cash_session.open`) con `500.00` Bs y `20.00` USD → caja `open` del equipo con `opened_by`, `business_date` de Caracas y auditoría `cash_session.opened`;
  - segunda apertura con otro id → 409 `cash_session_open` con `opened_by` y `opened_at`;
  - fondo negativo o con más de 2 decimales → 422;
  - fondo cero → permitido;
  - sin ninguna tasa cargada → 409 `exchange_rate_missing`;
  - Almacén → 403;
  - otro equipo puede abrir su propia caja;
  - `UPDATE` directo del fondo → error del trigger.
  - (RF-29, RF-30, RN-16/FR-005 a FR-008)
- [X] T026 [US1] Agregar a `MATRIX` de `backend/tests/test_permissions_matrix.py` las filas de `POST /devices`, `GET /devices`, `POST /devices/{id}/revoke`, `GET /devices/current` y `POST /sync/operations` según `contracts/api.md`, con los marcadores `{device_id}` y la cabecera del equipo creados en `actor_headers`

### Implementation for User Story 1

- [X] T027 [US1] Crear `backend/app/api/devices.py` con `POST /devices`, `GET /devices` y `POST /devices/{id}/revoke` (`require_roles(ADMIN)`), y `GET /devices/current` (`require_roles(ADMIN, SELLER)` + `ActiveDevice`). Esquema `Device` del contrato en `backend/app/api/sale_schemas.py`. Registrar el router en `backend/app/main.py`
- [X] T028 [US1] Crear `backend/app/services/cash_sessions.py` con el manejador `open_cash_session(db, *, device, user, operation)`:
  - valida el fondo con `validate_usd` (≥ 0, 2 decimales);
  - exige `applicable_rate(db, hoy)` (409 `exchange_rate_missing` si es nula);
  - inserta con el id del contenido y captura la violación del índice único parcial como 409 `cash_session_open`, con quién y desde cuándo;
  - audita `cash_session.opened`.
  Registrarlo en `HANDLERS["cash_session.open"]` de `services/sync.py` (R7, FR-005 a FR-008)
- [X] T029 [US1] Abrir `GET /exchange-rates/applicable` al Vendedor en `backend/app/api/exchange_rates.py`, cambiando la dependencia a Admin, Vendedor y Almacén, y actualizar su fila en `MATRIX` (R13)
- [X] T030 [US1] Crear `frontend/src/app/caja/page.tsx`:
  - **Sin equipo en IndexedDB**: si el usuario es Admin, formulario "Registrar este equipo" (nombre); guarda id, serie, nombre y token con `saveDevice`. Si no es Admin, mensaje "Este equipo no está registrado; pídeselo al administrador".
  - **Con equipo**: llama a `GET /devices/current` y `syncSequence`, y muestra la serie y la caja abierta (quién y desde cuándo).
  - **Sin caja abierta**: formulario de apertura (fondo en Bs y USD con `DecimalInput`) y la tasa aplicable de hoy. Si es de otro día, aviso "No hay tasa BCV de hoy; se usará la del dd/mm/aaaa"; sin tasa, botón deshabilitado con explicación.
  - **Apertura**: se encola `cash_session.open` y se espera el resultado con `waitFor`.
  - **Equipo revocado** (403 `device_revoked`): ofrece borrar el equipo local y registrarlo de nuevo (Admin).
  - (FR-001 a FR-008, RF-18)
- [X] T031 [US1] Crear `frontend/src/app/configuracion/equipos/page.tsx` (Admin): lista de equipos con serie, nombre, quién y cuándo se registró, caja abierta y estado, y acción "Revocar" con confirmación (FR-002)
- [X] T032 [US1] Ejecutar `pnpm api:types` y tipar las llamadas de equipos y caja con `packages/shared/src/api/schema.d.ts`

**Checkpoint**: US1 funciona sola: equipos con serie y caja abierta en el equipo.

---

## Phase 4: User Story 2 - Venta con un solo pago (Priority: P1)

**Goal**: buscar, agregar líneas por metro (m o cm) o unidad, ver totales en USD y Bs, anotar el cliente, cobrar con un pago y registrar la venta con número, kardex y tasa, sin duplicarla.

**Independent Test**: la venta de la User Story 2 (2 conexiones a 3,25 y 30 cm a 4,00/m, tasa 36,50) da 7,70 USD y 281,05 Bs; se cobra en Efectivo USD, queda `A-000001` con dos salidas de kardex, y reenviarla no la duplica.

### Tests for User Story 2 ⚠️

- [X] T033 [P] [US2] Pruebas en `backend/tests/test_sales_create.py` (marca `db`):
  - **Registro**: la venta de la User Story 2 registrada con `make_sale` → `number` `A-000001`, `subtotal_usd`, `total_usd` `7.70` y `total_ves` `281.05`; `exchange_rate` y su fecha iguales a las enviadas aunque exista una tasa más reciente (RN-05); el vendedor, la caja y el equipo.
  - **Kardex**: dos movimientos `sale` con `quantity_delta` `-2` y `-0.30`, `reference_type = 'sale_item'`, `device_id` y el stock descontado.
  - **Costo**: `unit_cost_usd` igual al costo promedio del producto.
  - **Validaciones**: `1.5` en una unidad → 422; `0.305` m → 422; cantidad 0 → 422; venta sin líneas → 422; producto inexistente → 422; caja de otro equipo → 409 `cash_session_unavailable`; `seller_id` distinto del usuario de la sesión → 422 en `seller_id` (R17).
  - **Numeración**: el mismo `sequence_number` con otro id de operación → 409 `sequence_conflict`; `device.last_sequence_number` avanza.
  - **Cliente**: nuevo con documento `j-40123456-7` → creado normalizado; otra venta con el mismo documento y otro id → se liga al existente sin duplicar; `customer_id` existente → se usa; venta sin cliente → permitida.
  - **Pago**: uno solo que cubre → `paid_usd` correcto; pago que no cubre → 422 (FR-037).
  - **Atomicidad**: un fallo a mitad de la transacción (forzado con un `monkeypatch` que hace fallar el último movimiento) no deja venta, pagos, movimientos ni fila en `outbox_operation`.
  - (RF-20, RF-21, RF-26, RF-28, RN-02, RN-05, RN-11/FR-010 a FR-019, FR-033, FR-037)
- [X] T034 [P] [US2] Pruebas en `backend/tests/test_sales_numbering.py` (marca `db`): dos equipos que envían 50 ventas cada uno desde hilos paralelos, con correlativos propios, no repiten ningún número ni dejan una venta sin registrar (RN-11/SC-005)
- [X] T035 [P] [US2] Pruebas en `backend/tests/test_sale_immutability.py` (marca `db`): `UPDATE` y `DELETE` por SQL directo sobre `sale`, `sale_item`, `payment` y `outbox_operation` fallan; `DELETE` en `customer` y `device` falla; un pago con método que exige referencia y `reference` nula insertado por SQL falla (RN-12/FR-044, SC-010)
- [X] T036 [P] [US2] Prueba en `backend/tests/test_sales_performance.py` (marca `db`): una venta de 20 líneas con 3 pagos se registra en menos de 1 s, medido alrededor de `POST /sync/operations` (R16). SC-002 (búsqueda en < 1 s) ya lo cubre `test_search_performance.py` de la 1.1b, porque la venta reutiliza `GET /products`
- [X] T037 [US2] Agregar a `LEAK_CASES` de `backend/tests/test_no_cost_leak.py` la respuesta de `POST /sync/operations` (`sale.create`) para el Vendedor y a `MATRIX` las filas de `GET /customers`. El Vendedor no recibe ninguna clave con `cost` ni `margin` (principio IV/SC-006)

### Implementation for User Story 2

- [X] T038 [US2] Crear en `backend/app/api/sale_schemas.py` los esquemas del contrato:
  - **Entradas**: `SaleInput`, `SaleItemInput`, `DiscountInput`, `MoneyInput` y `CustomerInput`, con `extra="forbid"` y decimales como cadenas. `customer` y `customer_id` son excluyentes.
  - **Salidas**: `SaleSeller` y `SaleAdmin` (`SaleAdmin` agrega `unit_cost_usd`, `margin_usd`, `cost_usd` y `margin_usd` de la venta), y `sale_for_role(db, sale, role)`, que elige el esquema con el rol leído de la base (ADR-0008).
- [X] T039 [US2] Crear `backend/app/services/customers.py` con `search_customers(db, q, limit=20)` (documento exacto normalizado o nombre que contiene, sin acentos) y `resolve_customer(db, *, actor, customer_input | customer_id)`, con la regla de R11: id existente → ese; documento ya registrado → ese; si no, crea. Crear también `GET /customers` en `backend/app/api/customers.py` (`require_roles(ADMIN, SELLER)`) y registrarlo en `main.py` (RF-28/FR-019)
- [X] T040 [US2] Crear `backend/app/services/sales.py` con el manejador `create_sale(db, *, device, user, operation)`. Lo registra en `HANDLERS["sale.create"]`, y en una sola transacción:
  1. Valida el contenido y bloquea la caja (`FOR UPDATE`): debe existir, ser del equipo y estar abierta (si no, 409 `cash_session_unavailable`).
  2. Valida que `seller_id` sea el usuario de la sesión que envía (422 en `seller_id` si no, R17).
  3. Bloquea los productos en orden de id (R16) y valida cada cantidad con `validate_quantity` y los decimales de su unidad (cm ya convertido en el equipo; `entered_unit` informativo).
  4. Calcula todo con `compute_sale` usando los precios enviados y la tasa enviada.
  5. Inserta la venta con `number = f"{series}-{n:06d}"`, capturando la violación de `(series, sequence_number)` como 409 `sequence_conflict`.
  6. Inserta líneas, pagos (`kind = sale_payment`) y vueltos (`kind = change`) con la caja de la venta y la tasa.
  7. Por línea: `post_movement(type='sale', quantity_delta=-cantidad, reference_type='sale_item', allow_negative=True)` con `device_id`, y guarda `unit_cost_usd` del producto.
  8. Avanza `device.last_sequence_number` si corresponde.
  9. Resuelve el cliente con `resolve_customer`.
  10. Devuelve `sale_for_role` con `alerts_created` y `warnings`.
  - Las alertas y los descuentos se agregan en US5 y US4 (R4, R5, FR-010 a FR-019)
- [X] T041 [US2] Agregar `device_id` como parámetro opcional de `post_movement` en `backend/app/services/inventory.py`, guardado en el movimiento, y una prueba en `backend/tests/test_stock_movements.py`
- [X] T042 [US2] Crear `frontend/src/lib/sales.ts`:
  - estado de la venta en curso: `saleId` de `uuidv7()`, líneas con `id` propio, cliente, pagos, vueltos y tasa con su fecha;
  - `computeSale` de `@sht/shared` para todo lo que se muestra;
  - `buildSaleInput()`, que arma el `SaleInput` con `takeSequenceNumber()`, la caja del equipo, el usuario actual como `seller_id`, la hora del equipo y `device_total_usd`;
  - `confirmSale()`, que encola `sale.create` y espera el resultado con `waitFor`. Si la red falla, la venta queda pendiente con su número y la pantalla lo indica.
- [X] T043 [US2] Crear los componentes en `frontend/src/components/sales/`:
  - `sale-product-search.tsx`: reutiliza la búsqueda de `GET /products` con `is_active=true`, solo productos con precio, y muestra precio en USD y Bs y stock actual;
  - `sale-lines.tsx`: cantidad con selector `m`/`cm` en productos por metro, enteros en unidades, error en línea con el mensaje de `validateQuantity`, subtotal y quitar línea;
  - `sale-totals.tsx`: subtotal, descuentos, total USD y Bs, y la fecha de la tasa si no es de hoy;
  - `customer-picker.tsx`: buscar por documento o nombre con `GET /customers`, o escribir uno nuevo con nombre, documento y teléfono.
  - Todos con las clases de `docs/guia-de-estilos.md`.
- [X] T044 [US2] Crear `frontend/src/app/vender/page.tsx` (Admin y Vendedor):
  - **Requisitos**: sin equipo o sin caja abierta, enlace a `/caja`.
  - **Tasa (FR-014)**: consulta la tasa aplicable al empezar la venta y cada 5 minutos. Si cambió y no hay pagos, aviso y botón "Actualizar tasa", obligatorio antes del primer pago; con pagos, la tasa queda fija.
  - **Contenido**: buscador, líneas, cliente opcional, un pago con método, monto y referencia si el método la exige, y totales.
  - **Confirmar**: habilitado solo si la venta tiene líneas y está cubierta. Al terminar, muestra el número y deja la pantalla lista para la siguiente venta.
  - **PC**: atajos de teclado (Enter agrega el primer resultado, F2 enfoca el buscador, F9 confirma).
  - **Diseño**: usable a 360 px.
  - (FR-010 a FR-019, SC-001)
- [X] T045 [US2] Ejecutar `pnpm api:types` y tipar las llamadas de la venta

**Checkpoint**: US2 funciona sola: venta con un pago, número, kardex y sin duplicados al reenviar.

---

## Phase 5: User Story 3 - Pagos mixtos y vuelto (Priority: P1)

**Goal**: varios pagos con saldo en USD y Bs, referencia obligatoria salvo en efectivo, y vuelto en uno o varios métodos, menor o igual que el excedente.

**Independent Test**: venta de 50,00 pagada con 20,00 en Efectivo USD, 730,00 Bs por Pago móvil con referencia y 10,00 por Zelle con referencia → saldo 0,00; otra de 7,70 pagada con 10,00 USD → vuelto de 83,95 Bs; vuelto menor → sobrepago visible.

### Tests for User Story 3 ⚠️

- [X] T046 [P] [US3] Pruebas en `backend/tests/test_sales_payments.py` (marca `db`):
  - **Pago mixto**: el de la User Story 3 registra tres pagos con su `amount_usd` (`730.00` Bs → `20.00`, RN-06), la tasa de la venta y `paid_usd` `50.00`; Zelle y USDT 1:1 (RN-04).
  - **Referencias**: pago móvil, punto de venta, Zelle o USDT sin referencia → 422 con `fields`; efectivo sin referencia → permitido; referencia de más de 60 caracteres → 422.
  - **Vuelto**: `83.95` en `cash_ves` para un excedente de `2.30`; vuelto en dos métodos (`1.00` USD + `47.45` Bs) → `change_usd` `2.30`; vuelto mayor que el excedente → 422; vuelto menor → `overpaid_usd` `0.30`.
  - **Saldo exacto en Bs**: pagar con el monto sugerido → cubierto.
  - **Límites**: más de 10 pagos o 5 vueltos → 422.
  - **Caja**: cada pago y vuelto guarda la caja de la venta.
  - (RF-23 a RF-25, RN-04, RN-06/FR-033 a FR-039)

### Implementation for User Story 3

- [X] T047 [US3] Completar `create_sale` en `backend/app/services/sales.py` con la validación de pagos y vueltos: método existente; `currency` del método; referencia obligatoria según `payment_method.requires_reference` (422 con `fields` antes de llegar al trigger); `amount` > 0 con 2 decimales; cobertura de lo pagado sobre el total recalculado (422 si no cubre, salvo lo que define US5 para totales distintos); vuelto ≤ excedente; `paid_usd`, `change_usd` y `overpaid_usd` en la respuesta (FR-033 a FR-039)
- [X] T048 [US3] Crear `frontend/src/components/sales/payments-panel.tsx`:
  - lista de pagos con método (los seis, en el orden de `sort_order`), monto en la moneda del método y referencia cuando el método la exige;
  - saldo pendiente en USD y Bs tras cada pago;
  - botón "Completar en Bs" con el monto de `suggestedVes`;
  - sección de vuelto con uno o varios métodos y montos, que propone el excedente en el método elegido y muestra el sobrepago si el vuelto es menor.
  Integrarlo en `frontend/src/app/vender/page.tsx` en lugar del pago único (FR-033 a FR-038, SC-001)

**Checkpoint**: US1 + US2 + US3 = venta completa con pagos mixtos (MVP de mostrador).

---

## Phase 6: User Story 5 - Venta sin stock suficiente (Priority: P2)

**Goal**: advertencia antes de confirmar y alertas para el Admin cuando la venta deja stock negativo o llega con precio o total distinto.

**Independent Test**: con stock 2, vender 3 → advertencia, venta confirmada, stock −1 y alerta de stock negativo en Pendientes.

### Tests for User Story 5 ⚠️

- [X] T049 [P] [US5] Pruebas en `backend/tests/test_sales_alerts.py` (marca `db`):
  - **Stock negativo**: con stock `2` vender `3` → venta registrada, stock `-1`, una alerta `negative_stock` con producto, cantidad y stock resultante, y `warnings` en la respuesta.
  - **Una alerta por tipo**: dos productos negativos en la misma venta → una sola alerta con ambos.
  - **Precio distinto**: precio enviado distinto del vigente → venta registrada con el precio enviado, `server_price_usd` y una alerta `price_mismatch`.
  - **Total distinto**: `device_total_usd` distinto del recalculado → alerta `total_mismatch` con ambos totales; si además los pagos no cubren el total recalculado, la venta se registra igual con esa alerta y el saldo.
  - **Tasa distinta**: `exchange_rate` distinta de la tasa cargada para `exchange_rate_date` (por ejemplo, la tasa se corrigió después) → venta registrada con la tasa enviada y una alerta `rate_mismatch` con ambas tasas; fecha sin tasa cargada → la misma alerta; tasa igual → sin alerta.
  - **Vendedor desactivado**: `inactive_user_sync` no ocurre en la 1.3 (R17); se prueba solo la función de detección con un usuario inactivo insertado en el fixture, para que quede lista para la 1.5.
  - **Pendientes**: `GET /alerts` las lista con `sale: {id, number}`.
  - (RN-10/FR-030 a FR-032, SC-009)

### Implementation for User Story 5

- [X] T050 [US5] Agregar a `create_sale` en `backend/app/services/sales.py` la detección de R6, con `create_sale_alert` y una alerta por tipo y venta: stock negativo tras los movimientos; precio de cada línea comparado con el precio vigente del producto; total del equipo comparado con el del servidor; tasa enviada comparada con `exchange_rate` de `exchange_rate_date` (`rate_mismatch` si difiere o no existe); vendedor inactivo. Con un total distinto que deja los pagos sin cubrir, la venta se registra con alerta en lugar de 422 (FR-032). Ajustar el 422 de cobertura de T047: aplica solo cuando el total del equipo coincide con el del servidor (R4, R6)
- [X] T051 [US5] Ampliar `backend/app/api/alerts.py` y su esquema para incluir `sale: {id, number}` en las alertas de venta, y `frontend/src/app/pendientes/page.tsx` para mostrar los tipos nuevos con su texto en español ("Stock negativo por venta", "Precio distinto al vigente", "Total distinto", "Tasa distinta a la cargada", "Descuento para revisar", "Vendedor desactivado") y un enlace a `/ventas/detalle?id=`
- [X] T052 [US5] En `frontend/src/components/sales/sale-lines.tsx`, si la cantidad de una línea (sumando otras líneas del mismo producto) supera el stock de la búsqueda, mostrar la advertencia "Stock disponible: N; la venta quedará con stock negativo" sin bloquear (FR-030)

**Checkpoint**: US5 funciona: venta sin stock con aviso y alertas.

---

## Phase 7: User Story 4 - Descuentos autorizados (Priority: P2)

**Goal**: descuentos por ítem o total, en monto o porcentaje. El Admin los aplica directamente; el Vendedor necesita PIN o una solicitud aprobada, tal cual o con un valor menor. Sin autorización válida, la venta va a revisión.

**Independent Test**: como Vendedor, 10 % a una línea de 20,00 autorizado con PIN → 18,00 con el Admin como autorizante; 5,00 sobre el total por solicitud aprobada desde otro navegador; solicitud de 10 % aprobada con 5 %; venta sin autorización marcada para revisión.

### Tests for User Story 4 ⚠️

- [X] T053 [P] [US4] Pruebas en `backend/tests/test_discounts.py` (marca `db`):
  - **Por PIN**: `POST /discount-authorizations` con PIN correcto → `approved` con `decided_by` el Admin; PIN incorrecto → 403 `pin_invalid`; 5 fallos → 423 `pin_locked`.
  - **Por solicitud**: `pending`, que el Vendedor consulta (solo las suyas; ajena → 404) y el Admin lista en `?status=pending`.
  - **Aprobar o rechazar**: aprobar tal cual; aprobar con `5.00` sobre un pedido de `10.00` → `discount_value` `5.00`, `requested_value` `10.00` y `discount_usd` recalculado; valor mayor que el pedido o ≤ 0 → 422; rechazar con motivo; decidir dos veces → 409 `invalid_state`.
  - **Venta con autorización**: la venta con `authorization_id` que coincide en venta, línea, tipo, valor aprobado y base → `item_discount_authorized_by` y método `pin` o `request`.
  - **Uso único y vínculo**: la misma autorización en otra venta → no coincide, venta en revisión; la autorización ya usada → la segunda venta va a revisión.
  - **Admin vendiendo**: descuento sin autorización → `admin_self`.
  - **Sin autorización válida**: Vendedor sin autorización o con un valor distinto del aprobado → venta registrada con `needs_review`, alerta `discount_review` y el descuento tal como vino.
  - **Revisión (FR-029)**: resolver la alerta deja la venta igual.
  - **Límites**: descuento en monto mayor que la base → 422; porcentaje > 100 → 422; 100 % → línea en `0.00`.
  - **Reparto**: el descuento total se reparte con el residuo correcto.
  - **Auditoría**: `sale.discounted` con el detalle, y `discount_authorization.requested`, `approved` y `rejected`.
  - (RF-22, RN-07/FR-020 a FR-029)
- [X] T054 [US4] Agregar a `MATRIX` las filas de `POST /discount-authorizations`, `GET /discount-authorizations/{id}`, `GET /discount-authorizations`, `POST …/approve` y `POST …/reject` según el contrato

### Implementation for User Story 4

- [X] T055 [US4] Crear `backend/app/services/discounts.py`:
  - `request_authorization(db, *, device, user, data)`:
    - calcula `discount_usd` con `sale_math` sobre `base_usd`;
    - con `method = "pin"`, valida con `pin.verify_admin_pin` y crea `approved` con `decided_by` el Admin;
    - con `"request"`, crea `pending`;
    - audita `discount_authorization.requested`.
  - `get_authorization(db, *, user, id)`: el Vendedor solo ve las suyas (404).
  - `list_pending(db)`.
  - `approve(db, *, actor, id, discount_value=None)`: el valor debe ser del mismo tipo, > 0 y ≤ `requested_value`; recalcula `discount_usd`; audita con el valor pedido y el aprobado.
  - `reject(db, *, actor, id, reason=None)`: audita.
  - `match_authorization(db, *, sale_id, sale_item_id, discount_type, discount_value, base_usd) -> DiscountAuthorization | None`: solo `approved` sin usar.
  - (R8, FR-023 a FR-027)
- [X] T056 [US4] Crear `backend/app/api/discount_authorizations.py` con los cinco endpoints del contrato (`POST` con `ActiveDevice`: un equipo revocado → 403 `device_revoked`) y registrarlo en `main.py`; sumar `pending_discount_requests` a `GET /inventory/summary` para el Admin en `backend/app/services/inventory.py`
- [X] T057 [US4] Completar `create_sale` en `backend/app/services/sales.py` con los descuentos:
  - pasa los descuentos de ítem y total a `compute_sale`;
  - si el vendedor es Admin, aplica `admin_self`;
  - si es Vendedor, usa `match_authorization` y liga la autorización (la unicidad la garantiza la base);
  - sin coincidencia, `needs_review = True` y alerta `discount_review`;
  - audita `sale.discounted` con el detalle de cada descuento, el autorizante y el método.
  - (FR-020 a FR-028)
- [X] T058 [US4] Crear `frontend/src/components/sales/discount-dialog.tsx`:
  - elige línea o total, tipo (monto o %) y valor, y muestra el resultado con `computeSale`;
  - **Admin**: lo aplica directamente;
  - **Vendedor, por PIN**: pide usuario y PIN del Admin, llama a `POST /discount-authorizations` con `method: "pin"` y aplica con el `authorization_id`;
  - **Vendedor, por solicitud**: la crea y consulta su estado cada 3 s; al aprobarse aplica el valor aprobado e indica si fue menor; si se rechaza, muestra el motivo;
  - si la línea, la base o el valor cambian después, quita la autorización y pide de nuevo.
  Integrarlo en `frontend/src/app/vender/page.tsx` (FR-020 a FR-026, SC-011)
- [X] T059 [US4] Ampliar `frontend/src/app/pendientes/page.tsx` (Admin) con "Solicitudes de descuento", que se actualiza cada 15 s. Muestra quién pide, el equipo, el producto o el total, el tipo, el valor y los montos, con las acciones "Aprobar", "Aprobar con otro valor" (campo ≤ pedido) y "Rechazar" (motivo opcional). Sumar la tarjeta de solicitudes pendientes en `frontend/src/app/page.tsx` (FR-025)

**Checkpoint**: US4 funciona: descuentos con PIN, solicitud y revisión.

---

## Phase 8: User Story 6 - Anulación de una venta (Priority: P2)

**Goal**: el Admin anula con motivo; vuelven el stock y el espejo de cada pago, en una transacción y una sola vez.

**Independent Test**: anular `A-000001` con motivo; el stock vuelve exacto, el kardex muestra los reversos, las devoluciones suman lo cobrado neto del vuelto y la auditoría registra el motivo.

### Tests for User Story 6 ⚠️

- [ ] T060 [P] [US6] Pruebas en `backend/tests/test_sale_void.py` (marca `db`):
  - **Anulación**: `POST /sales/{id}/void` con motivo → `sale_void` y un movimiento `sale_void` positivo por línea enlazado a la venta; el stock vuelve exactamente al previo (SC-008).
  - **Espejo de pagos**: por cada `sale_payment`, un `void_refund` igual, y por cada `change`, un `void_change` igual, en la caja de la venta con `sale_void_id`. La suma neta de la anulación es la negativa exacta de la venta.
  - **Validaciones**: motivo corto (< 5) o largo (> 500) → 422; anular dos veces → 409 `invalid_state`; Vendedor y Almacén → 403.
  - **Auditoría y estado**: `sale.voided` con el motivo; venta con stock negativo anulada → el stock vuelve a lo previo; `GET /sales/{id}` muestra `void` y los pagos de la anulación.
  - **Inmutabilidad**: `UPDATE` y `DELETE` por SQL directo sobre `sale_void` y sobre los pagos `void_refund` y `void_change` fallan (RN-12/FR-044, SC-010).
  - (RF-27/FR-041 a FR-043, SC-008)
- [ ] T061 [US6] Agregar a `MATRIX` la fila de `POST /sales/{id}/void` (solo Admin)

### Implementation for User Story 6

- [ ] T062 [US6] Agregar a `backend/app/services/sales.py` `void_sale(db, *, actor, sale_id, reason)`, que en una transacción:
  1. Bloquea la venta y rechaza con 409 `invalid_state` si ya existe `sale_void`.
  2. Crea `sale_void`.
  3. Por cada línea registra `post_movement(type='sale_void', quantity_delta=+cantidad, reference_type='sale_item')`, con los productos en orden de id.
  4. Inserta el espejo de cada pago (`void_refund` y `void_change`) en la caja de la venta.
  5. Audita `sale.voided`.
  Agregar también `POST /sales/{id}/void` en `backend/app/api/sales.py` (`require_roles(ADMIN)`, motivo de 5 a 500 caracteres) (R10, FR-041 a FR-043)
- [ ] T063 [US6] Crear `frontend/src/components/sales/void-sale-dialog.tsx` con el motivo obligatorio, el resumen de lo que vuelve (productos y cantidades, y devoluciones por método) y la confirmación (FR-041)

**Checkpoint**: US6 funciona: anulación completa con reversos y espejo de pagos.

---

## Phase 9: User Story 7 - Consulta de ventas (Priority: P3)

**Goal**: el Admin consulta y filtra todas las ventas con costos y márgenes; el Vendedor ve solo sus ventas de hoy, sin costos; el kardex enlaza con la venta.

**Independent Test**: con ventas de dos vendedores en dos días, el Admin filtra por fecha y vendedor; cada Vendedor ve solo las suyas de hoy y recibe 404 en las demás.

### Tests for User Story 7 ⚠️

- [ ] T064 [P] [US7] Pruebas en `backend/tests/test_sales_list.py` (marca `db`):
  - **Admin**: filtra por `from`/`to` (fecha de negocio de Caracas), `q` (número), `seller_id`, `customer_id`, `device_id` y `status` (`registered`, `voided`, `needs_review`); orden más reciente primero; paginación.
  - **Vendedor**: solo recibe sus ventas cuya fecha de negocio es hoy, aunque pida otras fechas o vendedores; venta a las 23:30 de Caracas del día anterior → no aparece; `GET /sales/{id}` de una venta ajena o de ayer → 404.
  - **Almacén**: 403.
  - **Costos**: `SaleAdmin` trae `unit_cost_usd` y `margin_usd`, y sin costo del producto, `margin_usd` nulo.
  - **Kardex**: las salidas `sale` y los reversos `sale_void` traen `sale: {id, number}`.
  - (FR-045 a FR-049)
- [ ] T065 [US7] Agregar a `MATRIX` las filas de `GET /sales` y `GET /sales/{id}`, y a `LEAK_CASES` `GET /sales`, `GET /sales/{id}` y `GET /products/{id}/movements` con ventas para el Vendedor (principio IV/SC-006, SC-007)

### Implementation for User Story 7

- [ ] T066 [US7] Agregar a `backend/app/services/sales.py` `list_sales(db, *, actor, filters, page, page_size)` y `get_sale(db, *, actor, sale_id)`, con la restricción del Vendedor impuesta en la consulta (`seller_id = actor.id AND business_date = hoy`). Crear `GET /sales` y `GET /sales/{id}` en `backend/app/api/sales.py` (`require_roles(ADMIN, SELLER)`) con `sale_for_role` y registrar el router en `main.py` (R12, FR-045, FR-046, FR-049)
- [ ] T067 [US7] Ampliar `backend/app/api/product_schemas.py` y `GET /products/{id}/movements` con `MovementSaleRef` (`{id, number}`) para `reference_type = 'sale_item'`. En `frontend/src/components/products/kardex-table.tsx`, enlazar el número con `/ventas/detalle?id=` para el Admin y mostrar solo el número para el Almacén (FR-048)
- [ ] T068 [US7] Crear `frontend/src/app/ventas/page.tsx`:
  - **Admin**: filtros de fechas, número, vendedor, equipo y estado, y la tabla con número, fecha y hora, vendedor, cliente, total USD y Bs, y chips de estado ("Anulada", "Para revisar").
  - **Vendedor**: "Mis ventas de hoy", sin filtros de fecha ni vendedor.
  Crear `frontend/src/app/ventas/detalle/page.tsx` (`?id=`):
  - ítems con cantidad, precio, descuentos y autorizante; totales; tasa y su fecha; pagos, vueltos y sobrepago; cliente; anulación;
  - para el Admin, además, costo y margen por línea y total, y el botón "Anular" con `void-sale-dialog`.
  - (FR-045 a FR-049, FR-051)
- [ ] T069 [US7] Ejecutar `pnpm api:types` y tipar las llamadas de ventas, alertas y autorizaciones

**Checkpoint**: todas las historias funcionan por separado y juntas.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: documentación (RNF-09), validación final y revisión.

- [ ] T070 [P] Actualizar `docs/modelo-de-datos.md` con los cambios listados en data-model.md ("Cambios a `docs/modelo-de-datos.md`"): §3.1, §3.6, §3.7 y §3.8
- [ ] T071 [P] Actualizar `docs/arquitectura.md`:
  - flujo 3.1 con la cola real, el token del equipo y la idempotencia (R3, R4);
  - servicios `devices`, `sync`, `cash_sessions`, `sales`, `discounts` y `customers`, y `domain/sale_math.py`, en la estructura del backend;
  - `lib/device` y `lib/outbox` en el frontend;
  - la matriz por endpoint;
  - el glosario: `device`, `series`, `outbox_operation`, `cash_session`, `discount_authorization`, `overpaid`;
  - en §8 Pendientes, quitar las dos preguntas de la 1.3.
- [ ] T072 [P] Actualizar ADR-0003 ("Pendiente de definir": descuentos sin conexión resueltos con RN-07 y PRD v0.10) y ADR-0004 (ruta `packages/shared/test-vectors/money.json`; vuelto en varios métodos y sobrepago)
- [ ] T073 [P] Actualizar `docs/guia-de-estilos.md` §9 con los componentes nuevos: pantalla de venta, panel de pagos y vuelto, diálogo de descuento y PIN, indicador de pendientes de envío y chips de estado de venta
- [ ] T074 [P] Actualizar `CHANGELOG.md` en "Sin publicar" con la etapa 1.3 (RF-18, RF-20 a RF-30, RN-01 a RN-07, RN-10, RN-11, RN-16) y `docs/plan-de-fases.md` con su estado
- [ ] T075 Ampliar `backend/tests/test_audit.py` (marca `db`) con las acciones de research R15: por cada una, provocarla por la API y comprobar en `audit_log` el usuario, el equipo (`device_id`), la entidad y el detalle (`device.registered`, `device.revoked`, `cash_session.opened`, `sale.discounted`, `discount_authorization.requested`, `discount_authorization.approved` con el valor pedido y el aprobado, `discount_authorization.rejected` y `sale.voided` con el motivo). Comprobar también que una venta sin descuento no audita nada y que `GET /audit` filtra por el grupo "Ventas y caja" (RF-46/FR-050)
- [ ] T076 Ejecutar `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest` (con `DATABASE_URL`), la migración subir–bajar–subir, `pnpm test`, `pnpm typecheck` y `pnpm build`, y corregir lo que falle
- [ ] T077 Recorrer los escenarios manuales 1–10 de `quickstart.md` en local, en PC y con ancho de teléfono de 360 px; medir SC-001 (venta típica < 1 min) y SC-011 (PIN < 15 s); anotar cualquier desviación como tarea nueva
- [ ] T078 Ejecutar `/security-review` y `/code-review` sobre la rama `004-ventas-multimoneda`, corregir los hallazgos confirmados y repetir T076. Es requisito para integrar a `main` (constitución, "Flujo de trabajo")
- [ ] T079 **Después de integrar a `main` (dueño y asistente):**
  - Con el despliegue terminado, registrar el equipo real del mostrador, abrir caja y registrar una venta de prueba con pago mixto y descuento en producción.
  - Anularla y comprobar el kardex y las alertas.
  - Restaurar el respaldo nocturno en local (plan de fases, definición de terminado).
  - Cerrar la etapa como versión `0.4.0`: CHANGELOG, etiqueta `v0.4.0` y release en GitHub.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (fase 1)**: sin dependencias.
- **Foundational (fase 2)**: depende de Setup y bloquea todas las historias.
  - En paralelo: T004–T010, T017, T020, T022 y T023.
  - En secuencia: T011 → T012 → T013.
  - Después de T012: T014 → T015 → T016 → T018. T019 va después de T018 y T021 después de T020.
- **US1 (fase 3)**: depende de la fase 2.
- **US2 (fase 4)**: depende de US1, porque necesita equipo y caja (las pruebas usan `make_device` y `open_cash_session`).
- **US3 (fase 5)**: depende de US2.
- **US5 (fase 6)**: depende de US2; las pruebas de cobertura con total distinto, de US3.
- **US4 (fase 7)**: depende de US2.
- **US6 (fase 8)**: depende de US2; el espejo de vueltos, de US3.
- **US7 (fase 9)**: depende de US2. El detalle con anulación (T068), de US6.
- **Polish (fase 10)**: depende de las historias que se entreguen. T078 (revisión) va justo antes de integrar y T079 (validación en producción) después.

### User Story Dependencies

- **US1 (P1)**: solo la fase 2.
- **US2 (P1)**: US1.
- **US3 (P1)**: US2.
- **US5 (P2)**: US2 (y US3 para los pagos que no cubren).
- **US4 (P2)**: US2.
- **US6 (P2)**: US2 (y US3 para vueltos).
- **US7 (P3)**: US2 (y US6 para mostrar la anulación).
- Las filas de `MATRIX` y `LEAK_CASES` de cada historia dependen de T013 y de la matriz existente.

### Within Each User Story

- Pruebas primero (deben fallar) → servicios → endpoints → frontend → tipos generados.
- `services/sales.py` lo amplían varias historias (T040, T047, T050, T057, T062, T066): esas tareas van en secuencia.
- `frontend/src/app/vender/page.tsx` lo amplían T044, T048 y T058, en secuencia.
- Cada historia termina con su checkpoint antes de pasar a la siguiente prioridad.

### Parallel Opportunities

- Fase 2: el dominio de Python (T004–T006, T010), el de TypeScript (T007–T009) y el frontend base (T020, T022, T023) en paralelo; la base de datos (T011–T013) en secuencia.
- Las pruebas de cada historia marcadas [P] van en paralelo.
- Una vez terminada US2, US4 (descuentos) y US7 (consulta) pueden avanzar en paralelo en el backend, coordinando `services/sales.py` y las filas de `MATRIX`.
- Fase 10: la documentación T070–T074 en paralelo.

---

## Parallel Example: Foundational

```bash
Task: "ves_to_usd y usd_to_ves en backend/app/domain/money.py"
Task: "compute_sale en backend/app/domain/sale_math.py"
Task: "Casos compartidos en backend/tests/test_sale_math.py"
Task: "computeSale en packages/shared/src/money.ts"
Task: "Casos compartidos en packages/shared/src/money.test.ts"
Task: "uuidv7 en packages/shared/src/uuid.ts"
Task: "Series y documentos en backend/app/domain/series.py y customer_document.py"
```

## Parallel Example: User Story 2

```bash
# Pruebas de US2 juntas:
Task: "Registro de la venta en backend/tests/test_sales_create.py"
Task: "Numeración entre equipos en backend/tests/test_sales_numbering.py"
Task: "Inmutabilidad en backend/tests/test_sale_immutability.py"
Task: "Rendimiento en backend/tests/test_sales_performance.py"
```

---

## Implementation Strategy

### MVP First (US1 + US2 + US3)

1. Fase 1 (Setup) y fase 2 (Foundational): cálculo compartido con sus casos en las dos suites, tablas y triggers, equipo y cola de salida.
2. Fase 3 (US1): equipo y apertura de caja.
3. Fase 4 (US2): venta con un pago, número y kardex, sin duplicados.
4. Fase 5 (US3): pagos mixtos y vuelto.
5. **Parar y validar**: escenarios 1 a 4 de `quickstart.md`. Con esto, una venta típica del mostrador ya funciona de punta a punta.

### Incremental Delivery

1. Setup + Foundational → base lista.
2. US1 → equipo y caja.
3. US2 + US3 → venta completa (MVP).
4. US5 → venta sin stock con alertas.
5. US4 → descuentos autorizados.
6. US6 → anulación.
7. US7 → consulta y enlaces desde el kardex.
8. Polish → documentación, revisión (T078), integración a `main`, validación en producción y versión 0.4.0 (T079).

---

## Notes

- [P] = archivos distintos y sin dependencias pendientes.
- Cada commit referencia los RF/RN/FR que toca, en español.
- Las pruebas que necesitan Postgres llevan la marca `db` y se saltan sin `DATABASE_URL`.
- **Puntos únicos del código**:
  - solo `post_movement` cambia el stock;
  - solo `domain/money.py`, `domain/sale_math.py` y `money.ts` redondean montos de la venta;
  - solo `services/sync.py` decide la idempotencia.
- El servidor nunca rechaza una venta por razones de negocio (stock, precio, total, tasa, descuento o vendedor desactivado): la registra y alerta (R4, R6). Solo rechaza lo estructural que el equipo nunca envía si funciona bien, incluidos los pagos que no cubren y el vuelto mayor que el excedente cuando el total del equipo coincide con el del servidor, y un vendedor distinto del usuario de la sesión (R4, R17).
- Los esquemas de respuesta por rol se eligen con el rol leído de la base, nunca con el del token (ADR-0008).
- El PIN del Admin nunca se guarda en IndexedDB, en la cola ni en la venta (R8).
