---

description: "Tareas de la etapa 1.4: egresos, cierre y cuadre de caja"
---

# Tasks: Caja: egresos, cierre y cuadre (etapa 1.4)

**Input**: documentos de diseño en `specs/005-cierre-caja/`

**Prerequisites**: plan.md, spec.md, research.md (R1–R14), data-model.md, contracts/api.md, quickstart.md

**Tests**: se incluyen, porque los exigen tanto la constitución como la especificación:

- **Constitución, principio VII**: cuadre de caja, idempotencia de la cola, inmutabilidad de los cierres y permisos por rol.
- **Especificación**: SC-002 a SC-008 y la tabla de pruebas del quickstart.

Cada prueba nombra en su docstring el RF/RN del PRD y el FR/SC de la especificación que verifica. Las pruebas de cada historia se escriben primero y deben fallar antes de implementar.

**Organization**: las tareas se agrupan por historia de usuario de spec.md (US1–US5), y cada historia se puede probar por separado. Las fases siguen la prioridad:

- P1: US1 (cierre) y US2 (egresos);
- P2: US3 (anulación con la caja cerrada) y US4 (consulta);
- P3: US5 (cierre del Admin desde otro equipo y operaciones posteriores al cierre).

**Trazabilidad con el PRD** (constitución, "Flujo de trabajo" y principio VII):

| FR de la especificación | RF/RN/RNF del PRD |
|---|---|
| FR-001 a FR-004 | RF-32, RF-33, RN-12 (ADR-0003) |
| FR-005 a FR-017 | RF-30, RF-31, RF-33, RN-12, RN-16 (ADR-0003, ADR-0004) |
| FR-018 y FR-019 | RF-31, RF-33 (principio III) |
| FR-020 a FR-023 | RF-27 (PRD v0.11), RF-33 |
| FR-024 a FR-028 | RF-46, RNF-02, RNF-05, RNF-07 (matriz de permisos) |

Los commits y las docstrings de las pruebas citan el RF/RN del PRD y el FR de la especificación, por ejemplo `RF-31/FR-006`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede hacer en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia a la que pertenece (US1…US5)
- Rutas relativas a la raíz del repositorio

## Path Conventions

- Backend: `backend/app/`, `backend/tests/`, `backend/migrations/`
- App interna: `frontend/src/`
- Compartido: `packages/shared/` (casos en `packages/shared/test-vectors/`)
- Comandos del backend desde `backend/` (`uv run …`); los de Node desde la raíz (`pnpm …`)
- Decimales en JSON siempre como cadenas (ADR-0004); en Python siempre `Decimal`. El cuadre solo suma y resta montos de 2 decimales en la moneda de cada método: no redondea ni convierte monedas
- Códigos de los métodos, en el orden del catálogo (`sort_order` de `payment_method`): `cash_ves` (VES), `mobile_payment` (VES), `pos_card` (VES), `cash_usd` (USD), `zelle` (USD), `binance_usdt` (USDT)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: casos compartidos del cuadre (R1). La etapa no trae dependencias, servicios ni variables de entorno nuevas.

- [X] T001 Crear `packages/shared/test-vectors/cash.json` con la estructura `{"methods": [...], "reconciliations": [...], "errors": [...]}`:
  - **`methods`**: los seis métodos del catálogo en orden, `{code, currency}`.
  - **Entrada de cada caso de `reconciliations`**: `name`, `opening_float_ves`, `opening_float_usd`, `movements: [{method, currency, kind, amount}]` (`kind` ∈ `sale_payment`, `change`, `void_refund`, `void_change`), `outflows: [{method, amount, voided}]` y `counted`. `counted` es `null` o un objeto `{método: monto}`; un método que falta en ese objeto se toma como `"0.00"`.
  - **Salida de cada caso**: `rows`, una fila por método en el orden del catálogo, con `method`, `currency`, `opening`, `collected`, `change_given`, `refunded`, `change_recovered`, `outflows`, `expected`, `counted` y `difference` (`counted` y `difference` en `null` si `counted` es `null`).
  - **Casos** (todos los montos como cadenas):
    1. Escenario 1 de la US1: fondo `500.00` Bs y `20.00` USD; `sale_payment` `cash_usd` `50.00`, `change` `cash_usd` `2.30`, `sale_payment` `mobile_payment` `730.00`; contado `cash_usd` `66.70` y el esperado en los demás. Esperado: `cash_ves` `500.00`, `mobile_payment` `730.00`, `cash_usd` `67.70` (diferencia `-1.00`) y `0.00` en los demás.
    2. Vuelto electrónico: `sale_payment` `mobile_payment` `730.00` y `change` `mobile_payment` `83.95` → `mobile_payment` `646.05`.
    3. Anulación en la misma caja: fondo `20.00` USD; `sale_payment` `cash_usd` `50.00`, `change` `cash_usd` `2.30`, `void_refund` `cash_usd` `50.00` y `void_change` `cash_usd` `2.30` → `cash_usd` `20.00`.
    4. Devolución de una venta de otra caja con esperado negativo: fondo `10.00` USD; `void_refund` `cash_usd` `15.00` y `void_refund` `zelle` `20.00` → `cash_usd` `-5.00` y `zelle` `-20.00`.
    5. Egresos y egreso anulado: fondo `500.00` Bs y `20.00` USD; egresos `cash_usd` `5.00` (vigente), `cash_usd` `3.00` (`voided: true`), `cash_ves` `120.50` (vigente) y `mobile_payment` `300.00` (vigente, sin cobros por ese método) → `cash_usd` `15.00`, `cash_ves` `379.50` y `mobile_payment` `-300.00`.
    6. Caja sin movimientos: fondo `500.00` Bs y `20.00` USD → el esperado es el fondo en los dos métodos en efectivo y `0.00` en los demás.
    7. Contado en blanco: el caso 6 con `counted` = `{"cash_usd": "20.00"}` → `cash_ves` contado `0.00` y diferencia `-500.00`; los demás métodos, contado `0.00` y diferencia `0.00`.
    8. USDT en su propia fila: `sale_payment` `binance_usdt` `25.00` → `binance_usdt` `25.00`, con moneda `USDT`.
  - **`errors`**: un `kind` desconocido, un método fuera del catálogo (en un movimiento y en un egreso) y un contado negativo. Cada uno con el mensaje en español que deben dar los dos módulos.
  - (R1, FR-006, FR-007, SC-002, SC-003)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: cuadre compartido, tablas y triggers, base de pruebas, alertas y auditoría, y el detalle de la caja, que usan todas las historias.

**⚠️ CRITICAL**: ninguna historia empieza antes de terminar esta fase.

- [X] T002 [P] Crear `backend/app/domain/cash_math.py`:
  - Dataclasses inmutables `MethodInfo` (`code`, `currency`), `CashMovement` (`method`, `currency`, `kind`, `amount`), `OutflowInput` (`method`, `amount`, `voided`) y `ReconciliationRow` (campos de salida de T001).
  - Función pura `compute_reconciliation(methods, opening_float_ves, opening_float_usd, movements, outflows, counted: dict[str, Decimal] | None) -> list[ReconciliationRow]`, con la fórmula de research R1: `expected = opening (solo cash_ves y cash_usd) + collected − change_given − refunded + change_recovered − outflows`. Los egresos con `voided` no restan.
  - `ValueError`, con los mensajes de `errors` de T001, para un `kind` desconocido, un método fuera de `methods` (en movimientos o egresos) y un contado negativo. Los egresos pueden ser de cualquier método.
  - Constante `CASH_METHODS = ("cash_ves", "cash_usd")`, los dos métodos con fondo inicial.
  - Sin acceso a la base de datos (RF-31/FR-006)
- [X] T003 [P] Crear `backend/tests/test_cash_math.py` (sin marca `db`). Recorre todos los casos de `packages/shared/test-vectors/cash.json` contra `compute_reconciliation`, y los de `errors` comprobando el mensaje (RF-31/FR-006, FR-007, SC-002, SC-003)
- [X] T004 [P] Crear `packages/shared/src/cash.ts` con `computeReconciliation(input)`. Usa la misma entrada y salida que `compute_reconciliation`, en cadenas, con `Decimal` de `decimal.js`, y lanza los mismos mensajes de error. Exporta también `CASH_METHODS`. Solo sintaxis de TypeScript borrable (sin `enum` ni `namespace`). Exportarlo desde `packages/shared/src/index.ts` (R1, FR-007)
- [X] T005 [P] Crear `packages/shared/src/cash.test.ts` con `node:test` y `node:assert`: lee `../test-vectors/cash.json` y recorre todos los casos y errores contra `cash.ts`. Comprobar que `pnpm test` pasa (FR-007, SC-003)
- [X] T006 Ampliar `backend/app/db/models.py` como en data-model.md, con estas reglas literales:
  - **`CashSession`**: columnas nuevas `closed_at`, `closed_by` (→ `app_user`), `closed_from_device_id` (→ `device`), `closed_outside_device`, `closing_note`, `closing_operation_id` (→ `outbox_operation`, único) y `closed_recorded_at` ("Hora del servidor en la transacción del cierre"), todas nulas.
    - `status`: "`open` \| `closed`".
    - `closing_note`: "5–500 caracteres".
    - Actualizar el docstring, que hoy dice "El cierre llega en la etapa 1.4".
  - **`CashOutflow`** (id del equipo):
    - `payment_method_code` (→ `payment_method`): "Cualquier método del catálogo".
    - `currency`: "`VES`, `USD` o `USDT`, la del método".
    - `reference`: nula, "1–60 caracteres; obligatoria si el método la exige (RF-24)".
    - `amount`: "> 0, en la moneda del método" (`numeric(16, 2)`).
    - `reason`: "5–200 caracteres".
    - `outbox_operation_id`: único.
    - `voided_at`, `voided_by` y `void_reason`: "nulos; las tres juntas; motivo 5–200".
    - Resto de columnas: `cash_session_id`, `device_id`, `created_by` y `occurred_at`.
  - **`CashCount`** (id del servidor):
    - `cash_session_id`, `payment_method_code` y `currency`.
    - `expected_amount`: "puede ser negativo".
    - `device_expected_amount`: nulo.
    - `counted_amount`: "≥ 0".
    - `difference`: "`counted_amount − expected_amount`".
    - Único `(cash_session_id, payment_method_code)`.
  - (R2, R3)
- [X] T007 Crear la migración `backend/migrations/versions/0007_cierre_de_caja.py` (revisión `0007`, anterior `0006`):
  - **`cash_session`**:
    - las columnas de T006;
    - `ck_cash_session_status_valid` ampliado a `status IN ('open', 'closed')`;
    - `ck_cash_session_closing`: si `status = 'closed'`, `closed_at`, `closed_recorded_at`, `closed_by` y `closed_outside_device` no son nulos; si `status = 'open'`, todas las columnas de cierre son nulas;
    - `ck_cash_session_note_length`;
    - índice `ix_cash_session_business_date (business_date DESC, opened_at DESC)`;
    - FK de `closing_operation_id` diferida, como la de `outbox_operation_id`.
  - **Tablas `cash_outflow` y `cash_count`**:
    - `cash_outflow`: `ck_cash_outflow_currency_valid` (`VES`, `USD` o `USDT`), `ck_cash_outflow_amount_positive`, `ck_cash_outflow_reason_length`, `ck_cash_outflow_reference_length` (nula o 1–60) y `ck_cash_outflow_void`, más el índice `ix_cash_outflow_cash_session (cash_session_id)`;
    - `cash_count`: `ux_cash_count_method`, `ck_cash_count_counted_non_negative` y `ck_cash_count_difference`.
  - **Triggers** (patrón de `0006`: `reject_change()` y guards con `to_jsonb`):
    - `cash_session_guard`, que reemplaza al de la 1.3. Los datos de apertura (`id`, `device_id`, `business_date`, `opened_by`, `opened_at`, los fondos y `outbox_operation_id`) nunca cambian. La única transición es `open → closed`, que fija a la vez todas las columnas de cierre. Una caja `closed` no admite ningún `UPDATE`. Se mantiene `cash_session_no_delete`.
    - `cash_session_counts_complete`: trigger de restricción `AFTER UPDATE`, `DEFERRABLE INITIALLY DEFERRED`; una caja que pasó a `closed` tiene exactamente una fila de `cash_count` por cada método de `payment_method`.
    - `cash_count_immutable`: `BEFORE UPDATE OR DELETE`, con `reject_change()`.
    - `cash_count_session_closed`: `BEFORE INSERT`; rechaza la fila si su caja no está `closed`.
    - `cash_outflow_reference`: `BEFORE INSERT`, con la función `payment_reference_check()` de `0006` (método que exige referencia y `reference` nula → error).
    - `cash_outflow_guard`: `BEFORE UPDATE OR DELETE`. No se borra; solo cambian `voided_at`, `voided_by` y `void_reason`, una vez (de nulas a completas), y solo si la caja del egreso está `open`.
  - **Alertas**: amplía `ck_alert_type_valid` con `cash_difference`, `expected_mismatch` y `post_close_operation`.
  - **`downgrade`**: lo quita todo y restaura el guard de la 1.3 y el `CHECK` de alertas.
  - Comprobar `alembic upgrade head`, `downgrade 0006` y `upgrade head` contra el Postgres local (FR-015, SC-005)
- [X] T008 Ampliar `backend/tests/conftest.py`:
  - Agregar `cash_count` y `cash_outflow` a `TABLES`, antes de `cash_session`.
  - Fábrica `register_outflow(headers, token, cash_session_id, method="cash_usd", amount="5.00", reason="Compra de botellones de agua", *, op_id=None) -> Response`: envía `cash_outflow.create` por la cola con un id nuevo y devuelve la respuesta sin verificar el estado.
  - Fábrica `close_cash_session(headers, token, cash_session_id, *, counted: dict[str, str] | None = None, note=None, op_id=None) -> Response`. Pide `GET /cash-sessions/{id}`, toma el `expected` de cada fila como `device_expected` y usa como `counted` el esperado, salvo los métodos de `counted`. Luego envía `cash_session.close`.
  - (R3, R4)
- [X] T009 [P] Agregar a `backend/app/services/alerts.py` `create_cash_session_alert(db, *, type, session, details)`, con `entity_type = 'cash_session'` y `details` que siempre incluye el equipo, quién abrió y quién cerró. En `backend/app/api/alerts.py`, sumar a `AlertOut` `cash_session: {id, device_name} | None` y llenarlo en `alerts_out` para esas alertas (R11)
- [X] T010 [P] Agregar a `packages/shared/src/audit-actions.ts`, en el grupo "Ventas y caja", `cash_outflow.created` ("Egreso de caja"), `cash_outflow.voided` ("Egreso anulado") y `cash_session.closed` ("Caja cerrada") (R12)
- [X] T011 [P] Agregar a `backend/app/api/deps.py` `OptionalDevice` (`Device | None`). Sin cabecera `X-Device-Token`, devuelve `None`. Con cabecera, el equipo del token aunque esté revocado, o el mismo 401/403 de `device_from_token` si el token no es válido. Como los demás, no declara acceso y va junto con `require_roles` (R6, R8, R9)
- [X] T012 Crear `backend/app/api/cash_schemas.py` con los esquemas de contracts/api.md:
  - `CashOutflowOut` (con `void: {reason, voided_by, voided_at} | null`);
  - `ReconciliationRow`;
  - `CashSessionSummary` (con `has_differences` y `opened_on_previous_day`);
  - `CashMovementOut` (`sale: {id, number}`, `kind`, `method`, `currency`, `amount`, `reference`, `occurred_at`, `after_close`);
  - `CashSessionDetail`, que extiende el resumen con `opening_float_ves`, `opening_float_usd`, `closed_from_device`, `closing_note`, `reconciliation`, `movements`, `outflows`, `voided_after_close` y `post_close_operations` (las dos últimas listas vacías hasta US3 y US5).
  Decimales como cadenas. Sin costos ni márgenes: el mismo esquema sirve para todos los roles (R9)
- [X] T013 Agregar a `backend/app/services/cash_sessions.py`:
  - `payment_methods(db) -> list[MethodInfo]`, en el orden de `sort_order`.
  - `reconcile(db, session, *, counted=None) -> list[ReconciliationRow]`: lee los `payment` y los `cash_outflow` de la caja (por `cash_session_id`) y llama a `compute_reconciliation`. Para una caja `closed`, `expected`, `device_expected`, `counted` y `difference` salen de `cash_count`, sin recalcular.
  - `expected_for(db, session, method) -> Decimal`: esperado actual de un método (el tope del egreso lo usa solo en efectivo).
  - `visible_session(db, *, actor, session_id, device) -> CashSession`. El Admin ve cualquier caja. El Vendedor ve la caja abierta del equipo de la cabecera o una que él cerró hoy (`business_date(closed_at)` = hoy, hora de Caracas). Si no, 404 `not_found`.
  - `session_detail(db, session) -> CashSessionDetail`: `movements` ordenados por `occurred_at` y `outflows`.
  Crear `backend/app/api/cash_sessions.py` con `GET /cash-sessions/{id}` (`require_roles(ADMIN, SELLER)`, `OptionalDevice`) y registrar el router en `backend/app/main.py`. Actualizar el docstring del módulo del servicio (R1, R9, FR-006, FR-025)
- [X] T014 [P] Crear `frontend/src/lib/cash.ts`:
  - `getCashSession(id)`;
  - `reconcile(detail, counted?)`, que llama a `computeReconciliation` de `@sht/shared` con los movimientos y egresos del detalle y los métodos de `paymentMethod` de `lib/sales.ts`;
  - `formatMethodAmount(amount, currency)`, con `formatMoney` (`1.234,56` y símbolo `Bs`, `USD` o `USDT`).
  En `frontend/src/lib/outbox/outbox.ts`, agregar `attentionForCashSession(cashSessionId)`: las operaciones pendientes o rechazadas sin descartar cuyo `payload.cash_session_id` es esa caja (FR-007, FR-014)
- [X] T015 [P] Crear `frontend/src/components/cash/reconciliation-table.tsx`. Una fila por método con fondo, cobrado, vuelto, devuelto, vuelto recuperado, egresos y esperado. En modo de cierre, además un campo de contado o verificado y la diferencia, con `+` verde o `−` rojo según los tokens de `theme.css`. En PC es tabla y a menos de 640 px, una tarjeta por método. Etiqueta "Contado" en efectivo y "Verificado" en los electrónicos (R13, FR-008, FR-028)
- [X] T016 Ejecutar `pnpm api:types` y comprobar `pnpm typecheck`

**Checkpoint**: el cuadre da lo mismo en las dos suites, la migración sube y baja, y `GET /cash-sessions/{id}` devuelve el esperado de una caja abierta.

---

## Phase 3: User Story 1 - Cierre de caja con cuadre por método de pago (Priority: P1) 🎯 MVP

**Goal**: el vendedor cierra la caja de su equipo viendo el esperado por método, escribe lo contado o verificado y el cierre queda guardado, inmutable y con alertas si hay diferencias.

**Independent Test**: con fondo de 500,00 Bs y 20,00 USD, vender en Efectivo USD con vuelto y por Pago móvil; cerrar con 1,00 USD de menos en Efectivo USD y ver la diferencia −1,00, la observación obligatoria y la alerta; intentar vender después y ver que pide abrir caja.

### Tests for User Story 1 ⚠️

> Escribir primero y comprobar que fallan antes de implementar.

- [X] T017 [P] [US1] Crear `backend/tests/test_cash_close.py` (marca `db`), con `close_cash_session` de T008:
  - **Esperado**: el del escenario 1 de la US1 en `GET /cash-sessions/{id}` y en el cierre.
  - **Cierre guardado**: estado `closed`, `closed_by`, `closed_at` (= `created_at` de la operación), `closed_recorded_at` (hora del servidor), `closed_from_device_id`, `closed_outside_device = false`; seis filas de `cash_count` con `expected_amount`, `device_expected_amount`, `counted_amount` y `difference`.
  - **Observación**: diferencia sin observación → 422; observación de 4 o de 501 caracteres → 422; sin diferencias, sin observación → 200.
  - **Conteos**: falta un método, un método repetido, un contado negativo o con 3 decimales → 422; `66.7` (un decimal) se acepta.
  - **Observación según lo que vio el equipo**: sin diferencias contra `device_expected` y sin observación, el cierre se guarda aunque el esperado del servidor dé otra diferencia, con `expected_mismatch` (FR-010, FR-012).
  - **Alertas**: `cash_difference` con la diferencia por método; ninguna sin diferencias; `expected_mismatch` cuando el `device_expected` enviado difiere del esperado del servidor (el cierre se guarda con el del servidor, conserva el del equipo y las diferencias se calculan contra el del servidor); la respuesta trae `alerts_created`.
  - **Rechazos**: segundo cierre de la misma caja con otra operación → 409 `cash_session_closed`; caja de otro equipo → 409 `cash_session_unavailable`.
  - **Idempotencia**: 10 reenvíos de la misma operación dejan un cierre, seis conteos y una alerta (SC-004).
  - **Después del cierre**: el equipo puede abrir otra caja enseguida; una `sale.create` creada después del cierre para la caja cerrada → 409 `cash_session_closed`; dos vendedores en el mismo equipo (uno abre y otro cierra) quedan registrados (RN-16).
  - **Almacén**: la operación se rechaza con 403.
  - (RF-30, RF-31, RF-33, RN-16/FR-005 a FR-017, SC-004, SC-008)
- [X] T018 [P] [US1] Crear `backend/tests/test_cash_immutability.py` (marca `db`), con SQL directo (`db.execute(text(...))`), y comprobar que fallan:
  - `UPDATE` de cualquier columna de una caja `closed` (incluida `status` a `open`) y `DELETE`;
  - `UPDATE` de los datos de apertura de una caja abierta;
  - `UPDATE` y `DELETE` de `cash_count`;
  - `INSERT` de `cash_count` en una caja abierta;
  - pasar una caja a `closed` sin sus seis conteos, que falla al confirmar.
  (RF-33, RN-12/FR-015, SC-005)
- [X] T019 [P] [US1] Agregar a `MATRIX` en `backend/tests/test_permissions_matrix.py` las filas de `POST /sync/operations` `cash_session.close` (Admin y Vendedor con equipo; Almacén ❌) y `GET /cash-sessions/{id}` (Admin, Vendedor; Almacén ❌). Agregar a `LEAK_CASES` en `backend/tests/test_no_cost_leak.py` `GET /cash-sessions/{id}` y la respuesta de `cash_session.close` para el Vendedor (SC-007)

### Implementation for User Story 1

- [X] T020 [US1] Agregar a `backend/app/services/cash_sessions.py` `close_cash_session(db, *, session_id, actor, counts, note, closed_at, device, operation_id, outside_device) -> tuple[CashSession, list[str]]`, en una transacción (research R4):
  1. Bloquea el equipo (si lo hay) y la caja (`with_for_update`).
  2. Con `outside_device = false`, exige que la caja sea del equipo (409 `cash_session_unavailable`). Siempre exige que esté abierta (409 `cash_session_closed`).
  3. Valida que vengan los seis métodos del catálogo, sin repetir, con contado ≥ 0 y como máximo 2 decimales (422 `validation_error` con el campo).
  4. Recalcula con `reconcile`. La observación (5–500 caracteres) es obligatoria si algún `counted − device_expected` es distinto de cero, o siempre con `outside_device = true` (422). Una diferencia que solo aparece con el esperado del servidor no la exige: la cubre `expected_mismatch`.
  5. Pasa la caja a `closed` con todas las columnas de cierre (`closed_recorded_at = utcnow()`) y luego inserta los seis `cash_count`, con la diferencia contra el esperado del servidor.
  6. Crea `cash_difference` y `expected_mismatch` con `create_cash_session_alert`.
  7. Audita `cash_session.closed` con esperado, contado y diferencia por método, la observación, `outside_device` y `closed_from_device_id`.
  Devuelve la caja y los tipos de alerta creados (RF-31/FR-010 a FR-013, FR-016)
- [X] T021 [US1] En `backend/app/api/sync.py`, agregar `CashSessionCloseInput` (`cash_session_id` y `counts: [{method, device_expected, counted}]`, máximo 6; `note: str | None`, máximo 500, con espacios recortados) y `handle_cash_session_close`, que llama a `close_cash_session` con `closed_at = operation.created_at`, `operation_id = operation.id` y `outside_device = false`. Devuelve `CashSessionDetail` más `alerts_created`. Registrarlo en `sync_service.HANDLERS` y sumar el esquema a `responses` de `post_operation` (FR-013)
- [X] T022 [US1] En `backend/app/services/sales.py`, cambiar `_cash_session` para que una caja del equipo ya `closed` responda 409 `cash_session_closed` ("La caja de la venta ya está cerrada: abre una caja nueva"); la caja inexistente o ajena sigue con `cash_session_unavailable`. Actualizar el docstring de `void_sale`, que hoy dice que las cajas no se cierran (FR-015, FR-017)
- [X] T023 [US1] Ampliar `OpenCashSessionRef` en `backend/app/api/sale_schemas.py` (`GET /devices/current`) con `opening_float_ves`, `opening_float_usd` y `opened_on_previous_day` (la fecha de negocio de la apertura no es la de hoy, hora de Caracas) (R5)
- [X] T024 [US1] Ejecutar `pnpm api:types`. En `frontend/src/lib/cash.ts`, agregar `enqueueClose(sessionId, rows, counted, note)`, que encola `cash_session.close` con `device_expected` = el `expected` calculado en el equipo y espera el resultado con `waitFor`, como la apertura. En `frontend/src/lib/outbox/outbox.ts`, `waitsForOwner` también devuelve true para `cash_session.close` de otro usuario (R4)
- [X] T025 [US1] Crear `frontend/src/app/caja/cierre/page.tsx`, siguiendo los pasos de research R4:
  1. Con `attentionForCashSession`, no deja cerrar si hay operaciones de la caja pendientes o rechazadas sin descartar. Las lista con un enlace a Pendientes. Si una espera a otro usuario (`waitsForOwner`), indica quién debe ingresar en el equipo para enviarla.
  2. Pide el detalle de nuevo y muestra `reconciliation-table` en modo de cierre, con la diferencia en vivo. Un campo en blanco cuenta como 0,00 y un contado negativo no se acepta.
  3. Para cada método electrónico, despliega sus cobros, vueltos y devoluciones con referencia y número de venta (FR-009).
  4. Con alguna diferencia, pide la observación (5–500 caracteres).
  5. Al confirmar, llama a `enqueueClose` y vuelve a `/caja/` con el resumen del cierre.
  (RF-31/FR-008 a FR-010, FR-014, FR-028)
- [X] T026 [US1] Ampliar `frontend/src/app/caja/page.tsx`:
  - con la caja abierta: el esperado actual por método (`reconciliation-table` en modo consulta), la fecha de apertura, un aviso si `opened_on_previous_day` y el botón "Cerrar caja" hacia `/caja/cierre/`;
  - tras cerrar: el resumen del cierre (esperado, contado, diferencia y observación) y el formulario de apertura de la 1.3.
  (FR-017, R5, R13)
- [X] T027 [P] [US1] En `frontend/src/app/vender/page.tsx`, mostrar el aviso "La caja está abierta desde el dd/mm/aaaa" si `opened_on_previous_day`. Con la caja cerrada, pedir abrir una nueva, como hoy sin caja (RF-30, R5)
- [X] T028 [P] [US1] En `frontend/src/app/pendientes/page.tsx`, mostrar las alertas `cash_difference`, `expected_mismatch` y `post_close_operation`, cada una con su texto en español, el equipo, quién cerró, los montos por método con `formatMethodAmount` y un enlace a `/cajas/detalle/?id=` (R11, FR-016)

**Checkpoint**: escenarios 1, 3 y 4 de `quickstart.md`; `test_cash_close.py` y `test_cash_immutability.py` pasan.

---

## Phase 4: User Story 2 - Egresos de caja (Priority: P1)

**Goal**: el vendedor registra egresos desde cualquier método, con motivo y referencia si no es efectivo; restan del esperado, quedan auditados y solo el Admin los anula con la caja abierta.

**Independent Test**: con 20,00 USD de fondo, registrar un egreso de 5,00 USD en efectivo con motivo y ver el esperado en 15,00; registrar uno de 300,00 Bs por Pago móvil con referencia y ver que resta de ese método; un egreso sin motivo, sin referencia en Pago móvil o en efectivo mayor que el disponible se rechaza; el Admin lo anula y el esperado vuelve a 20,00.

### Tests for User Story 2 ⚠️

- [X] T029 [P] [US2] Crear `backend/tests/test_cash_outflows.py` (marca `db`), con `register_outflow` de T008:
  - **Registro**: egreso en `cash_usd` y en `cash_ves` (sin referencia) y en `mobile_payment` y `binance_usdt` (con referencia, moneda `VES` y `USDT`) por Admin y por Vendedor, a nombre del usuario de la sesión, con `occurred_at` = `created_at` de la operación; resta del esperado en `GET /cash-sessions/{id}`.
  - **Rechazos permanentes**:
    - 422: método inexistente, `mobile_payment` sin referencia, referencia de 61 caracteres, monto `0.00`, negativo o con 3 decimales, motivo de 4 o de 201 caracteres;
    - 409 `cash_session_unavailable`: caja de otro equipo;
    - 409 `cash_session_closed`: caja cerrada y egreso creado después del cierre;
    - 409 `insufficient_cash`: monto en efectivo mayor que el esperado del método, con `available` y `currency` en la respuesta;
    - sin tope en los demás: un egreso por `zelle` sin cobros en ese método se acepta y deja su esperado negativo;
    - 403: Almacén.
  - **Idempotencia**: 10 reenvíos dejan un egreso (SC-004).
  - **Anulación**: `POST /cash-outflows/{id}/void` del Admin con motivo deja el egreso con `void` y deja de restar del esperado. Se rechaza con 409 `invalid_state` si ya estaba anulado, con 409 `cash_session_closed` si la caja está cerrada, con 422 si el motivo tiene menos de 5 caracteres y con 403 si lo intenta el Vendedor.
  - **Auditoría**: `cash_outflow.created` y `cash_outflow.voided`.
  - (RF-32, RF-33, RF-46/FR-001 a FR-004, SC-004)
- [X] T030 [P] [US2] Ampliar `backend/tests/test_cash_immutability.py` con `cash_outflow`. Deben fallar con SQL directo:
  - `DELETE`;
  - `UPDATE` de `amount`, `reason`, `reference` o `payment_method_code`;
  - `INSERT` de un egreso por `mobile_payment` sin referencia;
  - una segunda anulación;
  - anular con la caja cerrada.
  Con la caja abierta, fijar las tres columnas de anulación sí funciona (RN-12/FR-003, FR-015, SC-005)
- [X] T031 [P] [US2] Agregar a `MATRIX` las filas de `POST /sync/operations` `cash_outflow.create` (Admin y Vendedor; Almacén ❌) y `POST /cash-outflows/{id}/void` (solo Admin). Agregar a `LEAK_CASES` la respuesta de `cash_outflow.create` para el Vendedor (SC-007)

### Implementation for User Story 2

- [X] T032 [US2] Crear `backend/app/services/cash_outflows.py` con `register_outflow(db, *, device, user, operation_id, outflow_id, cash_session_id, method, amount, reason, occurred_at) -> CashOutflow` (research R3):
  1. Bloquea el equipo y la caja.
  2. Exige que la caja sea del equipo (409 `cash_session_unavailable`) y que esté abierta (409 `cash_session_closed`; la excepción de R7 llega en US5).
  3. Valida el método en el catálogo (422) y la referencia si el método la exige (`requires_reference`, 422 en `payload.reference`, como en los cobros).
  4. Solo si el método es en efectivo (`payment_method.is_cash`), valida el monto con `expected_for` (409 `insufficient_cash`, con `available` y `currency`).
  5. Inserta con la moneda del método y audita `cash_outflow.created` con método, monto, motivo y referencia.
  Docstring del módulo con RF-32 (PRD v0.12) y las decisiones de Clarifications (cualquier método, tope solo en efectivo, sin autorización del Admin) (RF-32/FR-001, FR-002)
- [X] T033 [US2] Agregar a `backend/app/services/cash_outflows.py` `void_outflow(db, *, actor, outflow_id, reason) -> CashOutflow`. Bloquea el egreso y su caja; responde 404 si no existe, 409 `invalid_state` si ya estaba anulado y 409 `cash_session_closed` si la caja está cerrada. Fija las tres columnas de anulación y audita `cash_outflow.voided` con el motivo (RF-33/FR-003)
- [X] T034 [US2] En `backend/app/api/sync.py`, agregar `CashOutflowCreateInput` (`id`, `cash_session_id`, `method`, `amount`, `reason` de 5 a 200 caracteres, recortado, y `reference: str | None` de hasta 60 caracteres, recortada) y `handle_cash_outflow_create`, con `amount_field` según la moneda del método. Devuelve `CashOutflowOut`. Registrarlo en `HANDLERS` y en `responses`. Crear `backend/app/api/cash_outflows.py` con `POST /cash-outflows/{id}/void` (`require_roles(ADMIN)`, cuerpo `{reason}` de 5 a 200 caracteres) y registrar el router en `main.py` (FR-003, FR-004)
- [X] T035 [US2] Ejecutar `pnpm api:types`. En `frontend/src/lib/cash.ts`, agregar `enqueueOutflow(sessionId, method, amount, reason, reference)` (id `uuidv7`) y `voidOutflow(id, reason)`. En `outbox.ts`, `waitsForOwner` también devuelve true para `cash_outflow.create` de otro usuario (R3)
- [X] T036 [US2] Crear `frontend/src/components/cash/outflow-dialog.tsx`. Pide método (los seis del catálogo), monto en la moneda del método, motivo (5–200 caracteres, con contador) y, si el método exige referencia, la referencia (obligatoria, hasta 60 caracteres). En efectivo, muestra el disponible calculado con `reconcile` y no deja confirmar si el monto lo supera; en los demás métodos no hay tope. Si el servidor rechaza con `insufficient_cash`, muestra el disponible que devuelve. Crear `frontend/src/components/cash/outflow-list.tsx`: hora, método, monto, motivo, referencia y quién. Los anulados se ven tachados, con el motivo y quién anuló. Para el Admin con la caja abierta, botón "Anular" que pide el motivo (FR-001 a FR-003, FR-028)
- [X] T037 [US2] En `frontend/src/app/caja/page.tsx`, agregar el botón "Registrar egreso" con `outflow-dialog` y la lista de egresos con `outflow-list`. Refrescar el esperado al registrar o anular (RF-32, R13)

**Checkpoint**: escenario 2 de `quickstart.md`; un cierre con egresos cuadra (`test_cash_close.py` sigue pasando).

---

## Phase 5: User Story 3 - Anulación de una venta con la caja ya cerrada (Priority: P2)

**Goal**: el Admin anula una venta cuya caja ya está cerrada; la devolución va a la caja abierta del equipo desde el que anula y el cierre original no cambia.

**Independent Test**: cerrar la caja con `A-000001` cobrada en Efectivo USD; abrir caja nueva en el mismo equipo, anular `A-000001` como Admin y ver el stock de vuelta, el cierre anterior idéntico y la devolución en el esperado de la caja nueva.

### Tests for User Story 3 ⚠️

- [X] T038 [P] [US3] Crear `backend/tests/test_sale_void_closed_session.py` (marca `db`):
  - **Caja de la venta abierta**: la devolución va a esa caja, con y sin `X-Device-Token`, y aunque la cabecera sea de otro equipo (igual que en la 1.3).
  - **Caja de la venta cerrada, Admin en un equipo vigente con caja abierta**: los `void_refund` y `void_change` llevan el `cash_session_id` de esa caja; el stock vuelve; los `cash_count` de la caja original no cambian; el esperado de la caja abierta refleja la devolución, aunque quede negativo.
  - **Rechazos con 409 `cash_session_required`**: sin cabecera, con un equipo revocado o con un equipo sin caja abierta. En los tres casos la venta queda sin anular.
  - **Consultas**: el detalle de la venta trae `void.refund_cash_session` con la caja y el equipo; el detalle de la caja original lista la venta en `voided_after_close` con sus montos intactos.
  - **Auditoría**: `sale.voided` lleva `refund_cash_session_id` y `refund_device_id`.
  - (RF-27, RF-33/FR-020 a FR-023, SC-006)

### Implementation for User Story 3

- [X] T039 [US3] Cambiar `void_sale` en `backend/app/services/sales.py` para recibir `device: Device | None` y decidir la caja de la devolución (research R8). Si la caja de la venta está `open`, la devolución va a esa caja. Si está `closed`, exige `device` vigente con caja abierta (la bloquea); si no, 409 `cash_session_required`: "La caja de esta venta ya está cerrada: anúlala desde un equipo registrado con la caja abierta". Los espejos se crean con el `cash_session_id` de la caja elegida. `sale.voided` suma `refund_cash_session_id` y `refund_device_id` en `after`. Docstring con RF-27 y PRD v0.11 (FR-020 a FR-022)
- [X] T040 [US3] En `backend/app/api/sales.py`, `POST /sales/{id}/void` recibe `OptionalDevice` y lo pasa a `void_sale`. En `backend/app/api/sale_schemas.py`, el `void` de `SaleAdmin` y `SaleSeller` suma `refund_cash_session: {id, device: {id, name}}`, deducido de los `void_refund`/`void_change` de la venta (FR-023)
- [X] T041 [US3] En `backend/app/services/cash_sessions.py` (`session_detail`), llenar `voided_after_close`: las ventas de esta caja cuyo `sale_void.voided_at` es posterior a `closed_recorded_at` (las dos son horas del servidor), con la caja y el equipo que recibieron la devolución (FR-023)
- [X] T042 [US3] Ejecutar `pnpm api:types`. En `frontend/src/components/sales/void-sale-dialog.tsx`, antes de confirmar, decir en qué caja se registrará la devolución: la de la venta si está abierta, o la abierta del equipo actual (de `GET /devices/current`). Si la caja de la venta está cerrada y el navegador no es un equipo con caja abierta, explicar que debe anular desde un equipo registrado con la caja abierta y no dejar confirmar. Advertir, sin impedirlo, si el efectivo esperado de la caja que recibe no alcanza para la devolución (R8)
- [X] T043 [P] [US3] En `frontend/src/app/ventas/detalle/page.tsx`, mostrar en la anulación la caja y el equipo que recibieron la devolución, con enlace a `/cajas/detalle/?id=` para el Admin (FR-023)

**Checkpoint**: escenario 5 de `quickstart.md`; el cierre original no cambia (SC-006).

---

## Phase 6: User Story 4 - Consulta de cajas y cierres (Priority: P2)

**Goal**: el Admin consulta todas las cajas con filtros y su detalle; el Vendedor ve la caja abierta de su equipo y sus cierres de hoy.

**Independent Test**: con cajas de dos equipos y dos días, el Admin filtra y ve todas con su cuadre y las diferencias resaltadas; el Vendedor solo ve la caja abierta de su equipo y sus cierres de hoy; el Almacén recibe 403.

### Tests for User Story 4 ⚠️

- [X] T044 [P] [US4] Crear `backend/tests/test_cash_sessions_list.py` (marca `db`):
  - **Admin**:
    - filtros `from`/`to` (fecha de negocio), `device_id`, `opened_by`, `closed_by`, `status` y `with_differences`;
    - orden, del más reciente al más antiguo;
    - paginación;
    - `has_differences`, `closed_outside_device` y `opened_on_previous_day` correctos.
  - **Vendedor**:
    - solo la caja abierta del equipo de la cabecera y las cajas que él cerró hoy (hora de Caracas; una de ayer no aparece);
    - los filtros se ignoran;
    - `GET /cash-sessions/{id}` de otra caja → 404;
    - sin cabecera, solo sus cierres de hoy.
  - **Almacén**: 403 en los dos endpoints.
  - (RF-31/FR-024 a FR-026)
- [X] T045 [P] [US4] Crear `backend/tests/test_cash_performance.py` (marca `db`): `GET /cash-sessions/{id}` de una caja con 100 ventas (unos 300 movimientos) y 5 egresos en menos de 1 s, midiendo la mediana de 5 llamadas (R14)
- [X] T046 [P] [US4] Agregar a `MATRIX` la fila de `GET /cash-sessions` (Admin, Vendedor; Almacén ❌) y a `LEAK_CASES` `GET /cash-sessions` para el Vendedor (SC-007)

### Implementation for User Story 4

- [X] T047 [US4] Agregar a `backend/app/services/cash_sessions.py` `list_cash_sessions(db, *, actor, device, filters, page, page_size)`. Para el Admin, aplica los filtros de contracts/api.md; `with_differences` usa `EXISTS` sobre `cash_count` con `difference <> 0`. Para el Vendedor, la consulta se restringe a `(device_id = equipo AND status = 'open') OR (closed_by = actor AND fecha de negocio de closed_at = hoy)`. Devuelve `CashSessionSummary` con `has_differences` en una sola consulta por página (R9, FR-024, FR-025)
- [X] T048 [US4] Agregar `GET /cash-sessions` a `backend/app/api/cash_sessions.py` (`require_roles(ADMIN, SELLER)`, `OptionalDevice`, paginación común) y ejecutar `pnpm api:types` (FR-024)
- [X] T049 [US4] Crear `frontend/src/app/cajas/page.tsx` (Admin):
  - filtros de rango de fechas, equipo, quién abrió, quién cerró, estado y "con diferencias";
  - tabla con equipo, fecha de apertura y de cierre (`dd/mm/aaaa` y hora de Caracas), quién abrió y quién cerró, estado y chips "Con diferencias" (resaltado) y "Cerrada fuera del equipo";
  - cada fila enlaza a `/cajas/detalle/?id=`.
  (FR-024, FR-028)
- [X] T050 [US4] Crear `frontend/src/app/cajas/detalle/page.tsx` (`?id=`):
  - datos de la caja;
  - `reconciliation-table` (con contado y diferencia si está cerrada) y la observación;
  - los movimientos por método, con la referencia de los electrónicos y enlace a `/ventas/detalle/?id=`;
  - los egresos con `outflow-list` (el Admin anula si la caja está abierta);
  - las ventas anuladas después del cierre, con la caja que recibió la devolución.
  El Vendedor llega aquí desde Caja para ver un cierre suyo de hoy (FR-024, FR-025)
- [X] T051 [P] [US4] En `frontend/src/components/app-shell.tsx`, agregar "Cajas" (`/cajas/`, solo Admin) junto a "Caja", con un ícono de lucide-react (FR-024)

**Checkpoint**: escenario 6 de `quickstart.md`.

---

## Phase 7: User Story 5 - Cierre de una caja por el Admin desde otro equipo (Priority: P3)

**Goal**: el Admin cierra desde su sesión una caja huérfana (equipo dañado o revocado); las operaciones creadas en el equipo antes de ese cierre se registran igual, con alerta.

**Independent Test**: revocar un equipo con caja abierta; como Admin, cerrarla desde otro navegador con observación y ver que queda cerrada fuera del equipo; enviar después una venta de esa caja creada antes del cierre y ver que se registra con la alerta "Operación posterior al cierre".

### Tests for User Story 5 ⚠️

- [X] T052 [P] [US5] Crear `backend/tests/test_cash_close_admin.py` (marca `db`):
  - **Cierre del Admin**: `POST /cash-sessions/{id}/close` con los seis contados y observación cierra una caja de otro equipo vigente y la de un equipo revocado. Queda con `closed_outside_device = true`, `closed_from_device_id` (el equipo de la cabecera, o nulo sin cabecera), `device_expected_amount` nulo y `closing_operation_id` nulo.
  - **Rechazos**:
    - 422: sin observación o con conteos incompletos;
    - 409 `cash_session_closed`: caja ya cerrada (y repetir la petición no crea otro cierre);
    - 403: el Vendedor y el Almacén.
  - **Alertas y auditoría**: `cash_difference` si hay diferencias; `cash_session.closed` con `outside_device`.
  - **Operaciones posteriores al cierre**: una `sale.create` y un `cash_outflow.create` de esa caja, creados antes de `closed_at`, se registran en su caja, sin cambiar los `cash_count`, con la alerta `post_close_operation` (tipo, número de venta o id del egreso, monto y moneda). El egreso tardío no se valida contra el efectivo disponible. Los creados después de `closed_at` → 409 `cash_session_closed`.
  - **Detalle**: muestra esas operaciones en `post_close_operations` y sus movimientos con `after_close = true`, sin cambiar el `reconciliation` guardado.
  - **Reloj del equipo atrasado**: una venta normal enviada antes del cierre, con `occurred_at` varios minutos atrás, no aparece como posterior al cierre (se compara `synced_at` con `closed_recorded_at`).
  - (RF-31, RF-33/FR-018, FR-019, SC-008)
- [X] T053 [P] [US5] Agregar a `MATRIX` la fila de `POST /cash-sessions/{id}/close` (solo Admin) (SC-007)

### Implementation for User Story 5

- [X] T054 [US5] Agregar `POST /cash-sessions/{id}/close` a `backend/app/api/cash_sessions.py` (`require_roles(ADMIN)`, `OptionalDevice`, cuerpo `{counts: [{method, counted}], note}` con `note` de 5 a 500 caracteres). Llama a `close_cash_session` con `outside_device = true`, `closed_at = utcnow()` (igual a `closed_recorded_at`), `operation_id = None`, `device` de la cabecera y `device_expected` nulo. En `close_cash_session` (T020), con `outside_device = true`, no se exige que la caja sea del equipo ni se crea `expected_mismatch`; `closed_from_device_id` es el equipo de la cabecera o nulo. Devuelve `CashSessionDetail` (R6, FR-018)
- [X] T055 [US5] Aceptar operaciones posteriores al cierre (research R7):
  - En `backend/app/services/sales.py`, `_cash_session` recibe `occurred_at`. Una caja `closed` del mismo equipo se acepta si `occurred_at < closed_at`, y `create_sale` crea entonces `post_close_operation` con `create_cash_session_alert`. Si no, 409 `cash_session_closed`.
  - En `backend/app/services/cash_outflows.py`, la misma regla con el `created_at` de la operación, sin validar el disponible.
  (FR-019)
- [X] T056 [US5] En `backend/app/services/cash_sessions.py`, `session_detail` llena `post_close_operations`. Son las ventas de la caja con `synced_at > closed_recorded_at` y los egresos cuya operación de cola tiene `received_at > closed_recorded_at`: solo horas del servidor. Sus movimientos llevan `after_close = true`. `reconcile` de una caja cerrada sigue leyendo `cash_count` y calcula los componentes sin esos movimientos (contracts/api.md, `ReconciliationRow`) (FR-019)
- [X] T057 [US5] Ejecutar `pnpm api:types`. En `frontend/src/app/cajas/detalle/page.tsx`, agregar el botón "Cerrar esta caja" (Admin, caja abierta de otro equipo o de un equipo revocado). Abre `reconciliation-table` en modo de cierre con la observación siempre obligatoria y llama a `POST /cash-sessions/{id}/close`. Mostrar aparte las operaciones posteriores al cierre y el chip "Cerrada fuera del equipo". Si el Admin abre el detalle de la caja de su propio equipo, enlazar a `/caja/cierre/` en lugar del botón (R6, R13)

**Checkpoint**: escenario 7 de `quickstart.md`; todas las historias funcionan por separado y juntas.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: documentación (RNF-09), validación final y revisión.

- [X] T058 [P] Actualizar `docs/modelo-de-datos.md` con los cambios listados en data-model.md ("Cambios a `docs/modelo-de-datos.md`"): §1.4, §3.1, §3.7 y §3.8
- [X] T059 [P] Actualizar `docs/arquitectura.md`:
  - el flujo del cierre por la cola, con el recálculo y las alertas;
  - los servicios `cash_sessions` y `cash_outflows` y `domain/cash_math.py`, en la estructura del backend;
  - `lib/cash.ts` y `components/cash/` en el frontend;
  - la matriz por endpoint;
  - el glosario: `cash_outflow`, `cash_count`, `post_close_operation`, `expected_mismatch`.
- [X] T060 [P] Actualizar ADR-0003 (tipos de operación `cash_outflow.create` y `cash_session.close`, operaciones posteriores al cierre de R7) y ADR-0004 (ruta `packages/shared/test-vectors/cash.json`; el cuadre no convierte monedas)
- [X] T061 [P] Actualizar `docs/guia-de-estilos.md` §9 con los componentes nuevos: tabla del cuadre (tabla y tarjetas), diálogo de egreso, lista de egresos con anulados tachados y chips de caja ("Con diferencias", "Cerrada fuera del equipo")
- [X] T062 [P] Actualizar `CHANGELOG.md` en "Sin publicar" con la etapa 1.4 (RF-27, RF-31 a RF-33, RN-12, RN-16) y `docs/plan-de-fases.md` con su estado
- [X] T063 Ampliar `backend/tests/test_audit.py` (marca `db`) con las acciones de research R12. Por cada una, provocarla por la API y comprobar en `audit_log` el usuario, el equipo (`device_id`), la entidad y el detalle: `cash_outflow.created`, `cash_outflow.voided` con el motivo, `cash_session.closed` por la cola y por el Admin desde otro equipo, y `sale.voided` con `refund_cash_session_id`. Comprobar también que `GET /audit` las filtra por el grupo "Ventas y caja" (RF-46/FR-027)
- [X] T064 Ejecutar `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest` (con `DATABASE_URL`), la migración subir–bajar–subir, `pnpm test`, `pnpm typecheck` y `pnpm build`, y corregir lo que falle
- [X] T065 Recorrer los escenarios manuales 1–9 de `quickstart.md` en local, en PC y con ancho de teléfono de 360 px. Medir SC-001 (cierre de un día de prueba de 30 ventas en menos de 10 minutos) y SC-002 (esperados idénticos al cálculo a mano). Anotar cualquier desviación como tarea nueva
- [X] T066 Ejecutar `/security-review` y `/code-review` sobre la rama `005-cierre-caja`, corregir los hallazgos confirmados y repetir T064. Es requisito para integrar a `main` (constitución, "Flujo de trabajo")
- [X] T067 **Después de integrar a `main` (dueño y asistente):**
  - Con el despliegue terminado, en el equipo real del mostrador: registrar un egreso, cerrar la caja del día y comprobar el cuadre y las alertas en producción.
  - Restaurar el respaldo nocturno en local (plan de fases, definición de terminado).
  - Cerrar la etapa como versión `0.5.0`: CHANGELOG, etiqueta `v0.5.0` y release en GitHub.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (fase 1)**: sin dependencias.
- **Foundational (fase 2)**: depende de Setup y bloquea todas las historias.
  - En paralelo: T002–T005, T009–T011, T014 y T015.
  - En secuencia: T006 → T007 → T008, y T012 → T013 → T016.
- **US1 (fase 3)**: depende de la fase 2.
- **US2 (fase 4)**: depende de la fase 2. Comparte `caja/page.tsx` con US1: T037 va después de T026.
- **US3 (fase 5)**: depende de US1, porque necesita una caja cerrada.
- **US4 (fase 6)**: depende de US1 (`has_differences` y los cierres de hoy del Vendedor). Usa `outflow-list` de US2 (T036).
- **US5 (fase 7)**: depende de US1 (`close_cash_session`), US2 (egreso tardío) y US4 (pantalla de detalle, T050).
- **Polish (fase 8)**: depende de las historias que se entreguen. T066 (revisión) va justo antes de integrar y T067 (validación en producción) después.

### User Story Dependencies

- **US1 (P1)**: solo la fase 2.
- **US2 (P1)**: solo la fase 2. Se puede probar sin US1, porque el esperado se ve en `GET /cash-sessions/{id}`.
- **US3 (P2)**: US1.
- **US4 (P2)**: US1 (y US2 para la lista de egresos).
- **US5 (P3)**: US1, US2 y US4.
- Las filas de `MATRIX` y `LEAK_CASES` de cada historia dependen de T008 y de la matriz existente.

### Within Each User Story

- Pruebas primero (deben fallar) → servicios → endpoints → tipos generados → frontend.
- Varias historias amplían el mismo archivo, así que esas tareas van en secuencia:
  - `services/cash_sessions.py`: T013, T020, T041, T047, T054 y T056;
  - `services/sales.py`: T022, T039 y T055;
  - `api/sync.py`: T021 y T034;
  - `frontend/src/app/caja/page.tsx`: T026 y T037;
  - `frontend/src/app/cajas/detalle/page.tsx`: T050 y T057.
- Cada historia termina con su checkpoint antes de pasar a la siguiente prioridad.

### Parallel Opportunities

- Fase 2: el cuadre en Python (T002, T003) y en TypeScript (T004, T005), alertas (T009), auditoría (T010), `OptionalDevice` (T011) y el frontend base (T014, T015) en paralelo. La base de datos (T006–T008) va en secuencia.
- Las pruebas de cada historia marcadas [P] van en paralelo.
- Terminada la fase 2, US1 y US2 pueden avanzar en paralelo en el backend, coordinando `api/sync.py` y las filas de `MATRIX`.
- Fase 8: la documentación T058–T062 en paralelo.

---

## Parallel Example: Foundational

```bash
Task: "compute_reconciliation en backend/app/domain/cash_math.py"
Task: "Casos compartidos en backend/tests/test_cash_math.py"
Task: "computeReconciliation en packages/shared/src/cash.ts"
Task: "Casos compartidos en packages/shared/src/cash.test.ts"
Task: "create_cash_session_alert en backend/app/services/alerts.py"
Task: "Acciones de caja en packages/shared/src/audit-actions.ts"
Task: "OptionalDevice en backend/app/api/deps.py"
```

## Parallel Example: User Story 1

```bash
# Pruebas de US1 juntas:
Task: "Cierre por la cola en backend/tests/test_cash_close.py"
Task: "Inmutabilidad en backend/tests/test_cash_immutability.py"
Task: "Filas de MATRIX y LEAK_CASES del cierre"
```

---

## Implementation Strategy

### MVP First (US1 + US2)

1. Fase 1 (Setup) y fase 2 (Foundational): cuadre compartido con sus casos en las dos suites, tablas y triggers, y el detalle de la caja.
2. Fase 3 (US1): cierre por la cola con diferencias, observación y alertas.
3. Fase 4 (US2): egresos desde cualquier método, con tope en efectivo y anulación del Admin.
4. **Parar y validar**: escenarios 1 a 4 de `quickstart.md`. Con esto, el mostrador ya abre, vende, registra egresos y cierra la caja cuadrada.

### Incremental Delivery

1. Setup + Foundational → base lista.
2. US1 → cierre de caja.
3. US2 → egresos (MVP).
4. US3 → anulación con la caja cerrada.
5. US4 → consulta de cajas del Admin.
6. US5 → cierre de cajas huérfanas y operaciones posteriores al cierre.
7. Polish → documentación, revisión (T066), integración a `main`, validación en producción y versión 0.5.0 (T067).

---

## Notes

- [P] = archivos distintos y sin dependencias pendientes.
- Cada commit referencia los RF/RN/FR que toca, en español.
- Las pruebas que necesitan Postgres llevan la marca `db` y se saltan sin `DATABASE_URL`.
- **Puntos únicos del código**:
  - solo `domain/cash_math.py` y `packages/shared/src/cash.ts` calculan el esperado;
  - solo `close_cash_session` cierra una caja, tanto por la cola como en el cierre del Admin;
  - solo `post_movement` cambia el stock (la anulación lo reutiliza sin cambios);
  - solo `services/sync.py` decide la idempotencia.
- El cierre nunca convierte monedas ni usa la tasa del día: cada método se cuadra en su moneda (RN-04, RN-05).
- Ningún cierre, conteo ni egreso se edita ni se borra: los errores se corrigen con un egreso nuevo, la anulación de un egreso con la caja abierta o la observación del cierre (RF-33, RN-12).
- La caja no tiene costos ni márgenes, así que no hay esquemas por rol. Aun así, `LEAK_CASES` cubre sus endpoints (principio IV).
