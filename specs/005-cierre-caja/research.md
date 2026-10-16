# Research: Caja: egresos, cierre y cuadre (etapa 1.4)

Decisiones de diseño de la etapa. Parte de lo que dejó la 1.3: `cash_session` con
apertura, `payment` con su caja por fila (`sale_payment`, `change`, `void_refund`,
`void_change`), la cola de salida idempotente (`POST /sync/operations`, R4 de la 1.3) y
la fórmula del esperado anotada en R10 de la 1.3 y en `docs/modelo-de-datos.md` §3.7.
No quedan `NEEDS CLARIFICATION`: las dos decisiones de negocio abiertas se respondieron en
`/speckit-clarify` (egresos sin autorización, sin ingresos de caja).

## R1. Esperado por método en un módulo puro, igual en Python y TypeScript (FR-006, FR-007, SC-002, SC-003; ADR-0004)

**Decisión**:

- `backend/app/domain/cash_math.py` (`compute_reconciliation`) y
  `packages/shared/src/cash.ts` (`computeReconciliation`), sin acceso a la base ni a la
  red.
- Entrada: fondo inicial en Bs y USD, la lista de movimientos de dinero de la caja
  (`{method, currency, kind, amount}`, con `kind` ∈ `sale_payment`, `change`,
  `void_refund`, `void_change`), los egresos (`{method, amount, voided}`; los anulados no restan) y, si los hay,
  los montos contados por método.
- Salida: una fila por cada uno de los seis métodos, en el orden del catálogo, con
  `opening`, `collected`, `change_given`, `refunded`, `change_recovered`, `outflows`,
  `expected` y, si hay contado, `counted` y `difference = counted − expected`.
- `expected = opening (solo cash_ves y cash_usd) + collected − change_given − refunded +
  change_recovered − outflows`. Todo en la moneda del método, con 2 decimales y sin
  convertir entre monedas. USDT se cuadra en USDT (equivale 1:1 a USD, RN-04, pero se
  muestra en su propia fila).
- El esperado puede ser negativo (por ejemplo, una devolución en efectivo de una venta
  de una caja cerrada, R8): el módulo no lo recorta, lo muestra.
- Casos compartidos en `packages/shared/test-vectors/cash.json`; los ejecutan
  `backend/tests/test_cash_math.py` y `packages/shared/src/cash.test.ts`
  (`node --test`, R2 de la 1.3). Incluye el escenario 1 de la US1, vuelto en un método
  electrónico, anulación en la misma caja, devolución recibida de otra caja, egreso
  anulado, caja sin movimientos, contado en blanco tomado como 0,00 y esperado negativo.

**Razón**: es la regla crítica de la etapa (principio VII). Con un único archivo de casos,
una divergencia entre el equipo y el servidor rompe la CI. La 1.5 calcula el esperado sin
conexión con el mismo módulo.

**Alternativas**: calcularlo solo en el servidor y mostrarlo en el equipo (no sirve para
la 1.5 y contradice FR-007); una vista SQL (duplica la regla en un tercer lenguaje).

## R2. Esquema de la caja cerrada y su inmutabilidad (FR-011, FR-015, SC-005; RF-33, RN-12)

**Decisión**:

- `cash_session` suma `closed_at`, `closed_by`, `closed_from_device_id` (nulo si el Admin
  cierra desde un navegador que no es equipo), `closed_outside_device` (true si no se
  cerró desde el equipo de la caja), `closing_note`, `closing_operation_id` (operación
  de la cola, nula en el cierre del Admin desde otro lugar) y `closed_recorded_at` (hora
  del servidor en la transacción del cierre; en el cierre del Admin es igual a
  `closed_at`). `closed_at` es la hora del equipo y decide si se acepta una operación
  tardía (R7); `closed_recorded_at` es la del servidor y marca qué llegó después del
  cierre, sin mezclar relojes. El CHECK de `status` admite
  `open` y `closed`, y un CHECK exige que las columnas de cierre estén completas si y solo
  si `status = 'closed'`.
- El trigger `cash_session_guard` se amplía: los datos de apertura nunca cambian; la
  única transición es `open → closed`, una vez; una fila cerrada no admite ningún cambio.
- `cash_count` (una fila por método al cerrar) es de solo inserción, con único
  `(cash_session_id, payment_method_code)`. Un trigger de restricción diferido
  (`DEFERRABLE INITIALLY DEFERRED`) sobre `cash_session` verifica al confirmar que una
  caja cerrada tiene exactamente una fila por cada método del catálogo, y otro sobre
  `cash_count` rechaza filas de una caja abierta. Así, después del cierre no caben filas
  nuevas ni cambios.

**Razón**: el principio II exige que el cierre sea inmutable también ante cambios
directos en la base. Los triggers siguen el patrón de la 1.3 (`reject_change`, guards
con `to_jsonb`).

**Alternativas**: una tabla `cash_closing` aparte (otra fila 1:1 sin ventaja: el cierre es
un estado de la caja, como ya prevé el modelo de datos); guardar los conteos en jsonb
(pierde las restricciones por columna y la consulta por diferencias).

## R3. Egresos (FR-001 a FR-004; RF-32)

**Decisión**:

- Tabla `cash_outflow` con id generado en el equipo. Columnas: `cash_session_id`,
  `device_id`, `payment_method_code` (cualquier método del catálogo), `currency` (la del
  método), `amount > 0`, `reason` (5–200), `reference` (1–60; obligatoria si el método la
  exige, con el mismo trigger `payment_reference_check()` de los pagos, RF-24), `created_by`, `occurred_at`, `outbox_operation_id`
  (único, diferida como en la venta) y la anulación: `voided_at`, `voided_by`,
  `void_reason` (5–200).
- Llega por la cola: operación `cash_outflow.create` con `{id, cash_session_id, method,
  amount, reason, reference}`. El servidor bloquea la caja y rechaza (permanente, se guarda en la
  cola):
  - 409 `cash_session_unavailable` si la caja no existe o no es del equipo, y 409
    `cash_session_closed` si está cerrada (salvo el caso de R7);
  - 422 si el método no existe, el monto no es positivo, el motivo no cumple o falta la
    referencia en un método que la exige;
  - solo en efectivo (`payment_method.is_cash`), 409 `insufficient_cash` si el monto
    supera el esperado actual de ese método, calculado con R1 dentro de la misma
    transacción. Trae `available` y `currency`. Los demás métodos no tienen tope: el
    banco o Binance pueden tener dinero de otros días (Clarifications).
- Queda a nombre del usuario de la sesión que la envía, como la venta (R17 de la 1.3).
  La cola del equipo la trata igual: espera a su dueño (`waitsForOwner`).
- Sin autorización del Admin (Clarifications). Audita `cash_outflow.created`.
- **Anulación**: `POST /cash-outflows/{id}/void` (solo Admin, con conexión, motivo
  5–200). Solo si la caja sigue abierta (409 `cash_session_closed`) y si el egreso no
  estaba anulado (409 `invalid_state`). Un trigger permite actualizar solo las tres
  columnas de anulación, una vez, y solo con la caja abierta. Audita
  `cash_outflow.voided`.

**Razón**: el egreso es una operación de mostrador que la 1.5 hará sin conexión; por eso
viaja por la cola desde ya, igual que la apertura. La anulación es del Admin con conexión
y no necesita la cola, como la anulación de una venta.

**Alternativas**: reutilizar `payment` con un `kind` nuevo (obliga a un `sale_id` y mezcla
dinero de ventas con gastos); borrar el egreso erróneo (prohibido por RN-12).

## R4. Cierre desde el equipo de la caja (FR-005, FR-008 a FR-014, FR-016, FR-017; RF-31)

**Decisión**:

- La pantalla Caja muestra la caja abierta con el esperado por método. Lo calcula el
  equipo con R1 sobre los movimientos que devuelve `GET /cash-sessions/{id}` (R9).
- **Cerrar caja** (`/caja/cierre/`):
  1. Revisa la cola local. No deja cerrar si hay operaciones de esa caja pendientes de
     envío o rechazadas sin descartar; las lista con un enlace al panel de pendientes
     (FR-014).
  2. Pide de nuevo el detalle al servidor, calcula el esperado y muestra por método el
     esperado, un campo de contado (efectivo) o verificado (electrónicos) y la
     diferencia en vivo. Un campo en blanco se toma como 0,00. Para los métodos
     electrónicos despliega la lista de cobros, vueltos y devoluciones con su referencia
     y venta (FR-009).
  3. Si alguna diferencia es distinta de cero, exige una observación de 5 a 500
     caracteres (FR-010).
  4. Encola `cash_session.close` con `{cash_session_id, counts: [{method,
     device_expected, counted}], note}` y espera el resultado, como la apertura.
- **Servidor** (`close_cash_session`, en una transacción):
  1. Bloquea el equipo y la caja.
  2. Exige que la caja sea del equipo y esté abierta: 409 `cash_session_unavailable` o
     409 `cash_session_closed`.
  3. Valida los seis métodos (422 si falta o se repite alguno, o si un contado es
     negativo o tiene más de 2 decimales).
  4. Recalcula el esperado con R1 y exige la observación según las diferencias que vio
     el equipo (422 si falta). Si con el esperado del servidor aparece otra diferencia,
     el cierre se guarda igual y la avisa `expected_mismatch` (FR-010, FR-012).
  5. Guarda `cash_count` con el esperado del servidor, el del equipo y la diferencia
     contra el del servidor; pasa la caja a `closed` con quién, cuándo
     (`created_at` de la operación), desde qué equipo y la observación.
  6. Crea las alertas: `cash_difference` si alguna diferencia (del servidor) es distinta
     de cero, y `expected_mismatch` si el esperado del servidor difiere del del equipo en
     algún método (FR-012, FR-016).
  7. Audita `cash_session.closed` con el resumen por método.
- La caja cerrada libera el índice único parcial: el equipo puede abrir otra enseguida
  (FR-017).

**Razón**: el cierre es la operación que más depende de la verdad del servidor, pero la
1.5 lo hará sin conexión. Con la cola, la idempotencia de la 1.3 y el recálculo, un
reenvío no cierra dos veces y una operación que el equipo no conocía queda registrada en
la alerta, sin perder el cierre.

**Alternativas**: un endpoint directo `POST /cash-sessions/{id}/close` para el Vendedor
(habría que rehacerlo en la 1.5); rechazar el cierre si los esperados difieren (dejaría
la caja abierta por algo que el vendedor no puede resolver).

## R5. Caja abierta de un día anterior y venta a medio hacer (Edge Cases)

**Decisión**:

- La caja no se cierra sola. La pantalla Caja y la de venta muestran un aviso si la
  fecha de negocio de la apertura no es la de hoy (hora de Caracas). El cierre guarda su
  propia hora y el detalle muestra las dos fechas.
- El borrador de la venta vive solo en la memoria de la pantalla de venta (1.3): al ir a
  Caja para cerrar ya no existe. No hace falta un aviso adicional. Una solicitud de
  descuento pendiente queda sin uso porque su venta nunca se registra; el Admin la ve
  como hoy y puede rechazarla.

**Razón**: no agrega estado nuevo y mantiene el comportamiento conocido de la 1.3.

## R6. Cierre por el Admin desde otro equipo (FR-018, US5)

**Decisión**:

- `POST /cash-sessions/{id}/close` (solo Admin, con conexión). Cuerpo: `{counts:
  [{method, counted}], note}`, con la observación siempre obligatoria (5–500). Usa el
  mismo servicio que R4 con `outside_device = true`, `closed_from_device_id` = el equipo
  de la cabecera `X-Device-Token` si la trae, y sin esperado del equipo (la columna queda
  nula). Sirve para cajas de equipos vigentes o revocados.
- Repetir la petición sobre una caja ya cerrada responde 409 `cash_session_closed`; no
  hace falta clave de idempotencia.
- El Vendedor no tiene acceso a este endpoint (403).
- Si el Admin quiere cerrar la caja de su propio equipo, la pantalla usa el flujo normal
  de R4.

**Razón**: el caso es raro y con conexión, como la anulación de una venta; un endpoint
directo es lo más simple. El flujo de R4 no sirve porque la operación de cola debe venir
del equipo de la caja.

## R7. Operaciones que llegan con la caja ya cerrada (FR-019)

**Decisión**:

- Una venta o un egreso para una caja cerrada se acepta si la operación se creó en el
  equipo antes del cierre (`occurred_at` de la venta o `created_at` de la operación
  menor que `closed_at`). Se registra en su caja, no cambia `cash_count` y genera la
  alerta `post_close_operation` con la caja, la operación y su monto.
- Si se creó después del cierre, se rechaza (permanente) con 409 `cash_session_closed`.
  Ese caso no ocurre si el equipo funciona bien, porque tras el cierre la pantalla pide
  abrir caja (RF-30).
- El egreso tardío no se valida contra el efectivo disponible: la caja ya está cerrada y
  el dinero ya salió.
- El detalle de la caja muestra aparte las operaciones posteriores al cierre: las que el
  servidor registró después de `closed_recorded_at` (`sale.synced_at` de la venta o
  `received_at` de la operación de cola del egreso). Así se comparan solo horas del
  servidor y un reloj atrasado en el equipo no marca como tardía una venta normal.

**Razón**: el principio III prohíbe perder una venta. En la práctica solo ocurre si el
Admin cierra una caja huérfana (R6) mientras el equipo tenía operaciones en su cola.
Comparar horas de distintos relojes es aproximado, pero el caso es excepcional y queda
alertado.

## R8. Anulación de una venta con la caja ya cerrada (FR-020 a FR-023; RF-27, PRD v0.11)

**Decisión**:

- `POST /sales/{id}/void` acepta la cabecera opcional `X-Device-Token`.
- Si la caja de la venta está abierta, la devolución va a esa caja, sin importar desde
  dónde anule el Admin (igual que en la 1.3).
- Si está cerrada, el Admin debe estar en un equipo registrado, vigente y con caja
  abierta. La devolución se registra en esa caja. Si no se cumple, 409
  `cash_session_required` con un mensaje que indica abrir caja en un equipo registrado.
- Los espejos (`void_refund`, `void_change`) se crean con el `cash_session_id` de la caja
  que recibe la devolución. `payment` ya guarda la caja por fila, así que no hace falta
  ninguna columna nueva.
- La caja cerrada no cambia: su `cash_count` es inmutable (R2). Su detalle lista las
  ventas anuladas después del cierre, con la caja que recibió la devolución.
- La caja que recibe la devolución la incluye en su esperado como cualquier movimiento.
  Si no tiene efectivo suficiente, la pantalla de anulación lo advierte sin impedirlo:
  el dinero ya se entregó al cliente.
- La auditoría `sale.voided` suma `refund_cash_session_id` y `refund_device_id`.
- El diálogo de anulación avisa antes de confirmar en qué caja se registrará la
  devolución. Si la caja de la venta está cerrada y el navegador no es un equipo con caja
  abierta, explica qué hacer.

**Razón**: es la regla del PRD v0.11. Reutiliza el espejo de pagos de la 1.3; solo cambia
la caja de destino.

**Alternativas**: devolver en la caja de la venta y "reabrir" el cierre (prohibido por
RF-33); exigir que el Admin elija la caja (más pasos sin ganancia: físicamente el dinero
sale de donde está).

## R9. Consulta de cajas y esquemas (FR-024, FR-025, US4)

**Decisión**:

- `GET /cash-sessions` paginado, más recientes primero:
  - Admin: filtros `from`, `to` (fecha de negocio de la apertura), `device_id`,
    `opened_by`, `closed_by`, `status` y `with_differences`.
  - Vendedor: solo la caja abierta del equipo de la cabecera (si la manda) y las cajas
    que él cerró hoy (hora de Caracas). Los demás filtros se ignoran.
  - Resumen: equipo, fechas, quién abrió y quién cerró, estado, si se cerró fuera del
    equipo y `has_differences`.
- `GET /cash-sessions/{id}` → `CashSessionDetail`: datos de la caja, `movements` (todos
  los pagos de la caja con venta, número, tipo, método, monto y referencia), `outflows`
  (con anulación), `reconciliation` (las filas de R1, calculadas en el servidor; si está
  cerrada, las de `cash_count` con el esperado del equipo), `voided_after_close`
  (ventas de esta caja con `sale_void.voided_at` posterior a `closed_recorded_at`, con
  la caja de la devolución) y
  `post_close_operations`. Para el Vendedor solo es visible la caja abierta de su equipo
  o una que él cerró hoy; si no, 404.
- La caja no contiene costos ni márgenes; no hay esquema por rol. `test_no_cost_leak.py`
  suma estos endpoints igual.
- `GET /devices/current` suma en `open_cash_session` el fondo, la fecha de negocio y si
  es de otro día, para el aviso de R5.

**Razón**: un solo detalle sirve a la pantalla Caja, al cierre y a la consulta del Admin.
Mandar los movimientos crudos permite que el equipo calcule con R1 (FR-007) y que la 1.5
use su copia local.

## R10. Permisos (FR-025, FR-026, SC-007; RNF-05)

| Acción | Admin | Vendedor | Almacén |
|---|:-:|:-:|:-:|
| Registrar egreso (cola, equipo con caja) | ✅ | ✅ | ❌ |
| Anular egreso | ✅ | ❌ | ❌ |
| Cerrar la caja de su equipo (cola) | ✅ | ✅ | ❌ |
| Cerrar una caja de otro equipo | ✅ | ❌ | ❌ |
| Consultar cajas | ✅ todas | Caja abierta de su equipo y sus cierres de hoy | ❌ |

`POST /sync/operations` ya excluye al Almacén. Los endpoints nuevos se declaran con
`require_roles` (prueba `test_route_declarations.py`) y se suman a la matriz.

## R11. Alertas (FR-012, FR-016, FR-019, SC-008)

**Decisión**: tres tipos nuevos con `entity_type = 'cash_session'`. `details` lleva el
equipo, quién abrió y quién cerró:

- `cash_difference`: las diferencias por método distintas de cero;
- `expected_mismatch`: por método, el esperado del equipo y el del servidor;
- `post_close_operation`: el tipo de operación, el número de venta o el id del egreso,
  el monto y su moneda.

`create_cash_session_alert` en `services/alerts.py`. El panel Pendientes y `GET /alerts`
muestran la caja con enlace a su detalle. Migración: se amplía `ck_alert_type_valid`.

## R12. Auditoría (FR-027; RF-46)

Acciones nuevas, en la misma transacción que la operación, en el grupo "Ventas y caja"
de `packages/shared/src/audit-actions.ts`:

- `cash_outflow.created`: método, monto y motivo.
- `cash_outflow.voided`: con el motivo.
- `cash_session.closed`: esperado, contado y diferencia por método, la observación,
  `outside_device` y `closed_from_device_id`.

La anulación de una venta con devolución en otra caja amplía `sale.voided` (R8).

## R13. Pantallas (FR-028; RNF-02, RNF-07)

- **Caja** (`/caja/`): estado de la caja, esperado actual por método, botón "Registrar
  egreso" (diálogo con método, monto, motivo y referencia si no es efectivo; en efectivo
  muestra el disponible), lista
  de egresos del día y botón "Cerrar caja". Tras cerrar, muestra el resumen del cierre y
  el formulario de apertura.
- **Cierre** (`/caja/cierre/`): R4. En teléfono, una tarjeta por método; en PC, una
  tabla.
- **Cajas** (`/cajas/`, Admin): lista con filtros y diferencias resaltadas. **Detalle**
  (`/cajas/detalle/?id=`): movimiento por método, pagos electrónicos con referencia y
  enlace a la venta, egresos con anulación (Admin, caja abierta), cuadre, anuladas
  después del cierre y botón "Cerrar esta caja" (Admin, caja abierta de otro equipo, R6).
- **Diálogo de anulación de venta**: R8.
- **Pendientes**: los tres tipos de alerta nuevos.
- Rutas estáticas con `?id=`, como en la 1.2 y la 1.3 (export estático). Formato con
  `formatMoney` de `@sht/shared`: `1.234,56`, `dd/mm/aaaa` y hora de Caracas.

## R14. Rendimiento y meta de 10 minutos (SC-001)

- El detalle de una caja con 100 ventas trae unos 300 movimientos en una consulta por
  tabla con índice por `cash_session_id` (ya existe `ix_payment_cash_session`; se crea
  `ix_cash_outflow_cash_session`). Objetivo: menos de 1 s.
- La meta de 10 minutos depende sobre todo de contar el efectivo. El sistema aporta
  esperados listos, la lista de referencias por método electrónico para cotejar con el
  banco y la diferencia en vivo. Se valida en el quickstart con un día de prueba de 30
  ventas.
