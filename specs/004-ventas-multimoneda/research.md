# Research: Ventas multimoneda, pagos mixtos, descuentos y apertura de caja (etapa 1.3)

Decisiones de diseño de la etapa. Cada una referencia los requisitos de la spec que
resuelve. Las decisiones previas que se respetan sin cambios están en ADR-0003 (cola de
salida, idempotencia y numeración por equipo) y ADR-0004 (dinero y redondeo).

## R1. Cálculo de la venta en un módulo puro, igual en Python y TypeScript (FR-011, FR-013, FR-020, FR-021, FR-035 a FR-038, FR-040; ADR-0004)

**Decisión**:

- `backend/app/domain/sale_math.py` y `packages/shared/src/money.ts` implementan la
  misma función `compute_sale` / `computeSale`. Recibe la tasa, las líneas (precio
  unitario, cantidad, decimales de la unidad, descuento propio), el descuento sobre el
  total, los pagos y los vueltos. Devuelve por línea el subtotal, el descuento propio,
  la parte del descuento total y el neto, y para la venta el subtotal, el descuento
  total, el total en USD y en Bs, lo pagado en USD, el saldo en USD y en Bs, y el
  excedente.
- Fórmulas y puntos de redondeo: los de ADR-0004, sin cambios. El reparto del
  descuento total es proporcional al neto de cada línea, redondeado mitad hacia arriba,
  con el residuo en la línea de mayor neto (la primera si hay empate).
- **Pago en Bs y saldo exacto (User Story 3, escenario 6)**: el monto en Bs sugerido
  para un saldo es `round(saldo_usd × tasa)` y un pago en Bs cubre
  `round(monto_bs ÷ tasa)`. Con tasa mayor que 1 el viaje de ida y vuelta devuelve el
  mismo saldo: el error de redondeo en Bs (≤ 0,005) dividido por la tasa es menor que
  medio centavo. Un caso compartido lo fija. La venta está cubierta cuando lo pagado en
  USD es mayor o igual que el total.
- **Vuelto (FR-038)**: uno o varios vueltos, cada uno con su método. Un vuelto en USD,
  Zelle o USDT es 1:1; uno en Bs se convierte con `round(monto_bs ÷ tasa)`. La suma de
  los vueltos en USD no puede superar el excedente. Si es menor (el cliente deja el
  resto), la diferencia queda como sobrepago de la venta, visible en el detalle.
- Cantidades: `cm ÷ 100` y validación por decimales de la unidad
  (`domain/units.py` en Python, `validateQuantity` en TypeScript), con los mismos
  mensajes.
- **Casos compartidos**: `packages/shared/test-vectors/money.json`. Lo ejecutan
  `backend/tests/test_sale_math.py` y `packages/shared/src/money.test.ts`. Cubre líneas
  por metro y por unidad, ingreso en cm, cantidades rechazadas, descuentos en monto y
  porcentaje, reparto con residuo, Bs del total, pagos mixtos, saldo exacto en Bs,
  vueltos en USD y Bs, sobrepago y bordes de redondeo (x,xx5).
- TypeScript usa `decimal.js` configurado con `ROUND_HALF_UP` (dependencia ya decidida
  en ADR-0004). Los decimales viajan como cadenas.

**Razón**: el equipo calcula para mostrar y, en la 1.5, para vender sin conexión; el
servidor recalcula como autoridad. Si no dan lo mismo hay alertas de total distinto en
cada venta.

**Alternativas**: calcular solo en el servidor y que la pantalla pregunte cada vez (no
sirve sin conexión, principio III); generar código desde una sola fuente (complejidad
sin beneficio para un módulo pequeño).

**Ajuste de documentación**: ADR-0004 nombra `shared/test-vectors/money.json`; la
carpeta real es `packages/shared/test-vectors/`. Se corrige la ruta en el ADR.

## R2. Pruebas de TypeScript sin dependencias nuevas de prueba (FR-040, principio VII)

**Decisión**: las pruebas de `packages/shared` corren con el ejecutor nativo de Node 24
(`node --test`), que ejecuta TypeScript con eliminación de tipos. El paquete agrega el
script `test`, la raíz `pnpm test` y la CI un paso `pnpm test` en el trabajo del
frontend. El módulo usa solo sintaxis de TypeScript que se puede borrar sin
transformar (sin `enum` ni `namespace`).

**Razón**: no suma Vitest ni Jest para una sola suite; la CI ya usa Node 24.

**Alternativas**: Vitest (dependencia y configuración extra para el mismo resultado).

## R3. Equipo de mostrador: registro, serie y token (FR-001 a FR-004; RN-11; ADR-0003)

**Decisión**:

- Tabla `device` (ya prevista en el modelo). El Admin, con sesión en el navegador del
  mostrador, lo registra con un nombre (`POST /devices`). El servidor:
  - asigna la serie desde el contador `sequence_counter` fila `device_series`
    (1 → `A`, 26 → `Z`, 27 → `AA`…); como el contador solo avanza, una serie nunca se
    reutiliza;
  - genera un token aleatorio de 32 bytes, guarda su SHA-256 y lo devuelve una sola
    vez.
- El navegador guarda en IndexedDB el id, la serie, el nombre, el token y el contador
  local de ventas (R5). Cada operación de mostrador envía el token en la cabecera
  `X-Device-Token`. El servidor exige un equipo vigente cuyo token coincida.
- Revocar (`POST /devices/{id}/revoke`, Admin) fija `revoked_at`. Las operaciones de un
  equipo revocado se rechazan si se crearon después de la revocación; las anteriores
  se aceptan (caso borde de la spec).
- `GET /devices/current` (con la cabecera) devuelve el equipo, su caja abierta y el
  último correlativo registrado en el servidor.
- `user_session.device_id` sigue nulo en esta etapa: el equipo se identifica en cada
  petición por su token. Se usará en la 1.5 para la sesión sin conexión. La columna
  `stock_movement.device_id` recibe el equipo en las salidas por venta, y se agregan
  las FK que la 1.1 dejó pendientes ("sin FK hasta la etapa 1.3").

**Razón**: el token separa "qué equipo" de "qué usuario" (dos vendedores pueden usar el
mismo equipo, RN-16) y funciona igual sin conexión.

**Alternativas**: identificar el equipo por la sesión del usuario (se pierde al cerrar
sesión y no distingue equipos); huella del navegador (frágil).

## R4. Cola de salida e idempotencia (FR-017, FR-018, SC-004; ADR-0003)

**Decisión**:

- **En el equipo**: tabla `outbox` de IndexedDB con Dexie (dependencia nueva, ya
  decidida en ADR-0003). Cada operación tiene un id UUIDv7 generado en el equipo
  (función `uuidv7()` en `packages/shared`, sin dependencia), tipo, contenido, estado
  (`pending`, `sent`, `rejected`) y último error. Se envían en orden, una por
  petición, al crearlas, al recuperar la conexión, al abrir la app y cada 30 s con
  espera creciente si fallan.
- **Tipos en esta etapa**: `cash_session.open` y `sale.create`. Anular y autorizar
  descuentos requieren conexión y van por endpoints normales.
- **En el servidor**: `POST /sync/operations` recibe una operación. En una sola
  transacción:
  1. `INSERT … ON CONFLICT (id) DO NOTHING` en `outbox_operation`. Si la fila ya
     existía, la transacción espera al dueño de la fila (bloqueo de la clave) y
     devuelve el `result` o el `error` guardado, con el mismo código HTTP.
  2. Procesa la operación y guarda el resultado en la misma fila.
- **Respuestas**:
  - 200 con el resultado: procesada. Si era un reenvío, el resultado es el original.
  - 409 o 422 con `code`: rechazo permanente, guardado en la fila. La app marca la
    operación como `rejected`, la muestra en "Pendientes de envío" con el motivo y
    sigue con las demás.
  - Errores de red, 5xx o 401: transitorios. La operación queda `pending` y se
    reintenta.
- **El servidor no rechaza una venta por razones de negocio**: stock insuficiente,
  precio distinto, total distinto, descuento sin autorización o vendedor desactivado
  se registran con alerta (R6). Solo rechaza lo estructural: contenido inválido,
  producto o caja inexistente, caja de otro equipo o cerrada, equipo revocado antes de
  la operación, cantidad con decimales de más o correlativo ocupado por otra operación.
- Un rechazo permanente de una venta deja un hueco en la serie del equipo. El número es
  interno y sin valor fiscal (ADR-0003); el hueco queda explicado por la operación
  rechazada.

**Razón**: la idempotencia por clave primaria es la forma más simple y segura de que un
reintento no duplique. El bloqueo de la fila serializa dos envíos simultáneos de la
misma operación.

**Alternativas**: enviar lotes (más complejo de reintentar parcialmente); Background
Sync API (no está en todos los navegadores, ADR-0003).

## R5. Numeración `{serie}-{correlativo}` (FR-016, SC-005; RN-11)

**Decisión**: el equipo guarda su contador en IndexedDB y numera al confirmar la venta.
La venta guarda `series` y `sequence_number`, con índice único. El número `A-000123` se
deriva. `device.last_sequence_number` guarda el mayor correlativo recibido. Al abrir la
app con conexión, el equipo toma `max(local, servidor)` como contador, por si se
restauraron datos viejos. Si llega una venta con un correlativo ya usado por otra
operación, se rechaza con `sequence_conflict`: solo pasa si el equipo perdió datos, y
entonces hay que registrarlo de nuevo (FR-004).

**Razón**: es lo que fija ADR-0003; dos equipos nunca chocan porque tienen series
distintas.

## R6. Alertas de la venta (FR-028, FR-031, FR-032, SC-009; RN-07, RN-10)

**Decisión**: se amplía el `CHECK` de `alert.type` con:

| Tipo | Cuándo | Entidad |
|---|---|---|
| `negative_stock` | Una salida por venta deja el stock de un producto en negativo | venta (detalle: producto, cantidad, stock resultante) |
| `price_mismatch` | El precio unitario de una línea no es el vigente en el servidor | venta (detalle: producto, precio del equipo y del servidor) |
| `total_mismatch` | El total del equipo difiere del recalculado, o los pagos no cubren el total recalculado | venta (detalle: ambos totales y el saldo) |
| `discount_review` | Descuento de un Vendedor sin autorización válida | venta |
| `inactive_user_sync` | El vendedor de la venta está desactivado al registrarla | venta |

Una venta genera una alerta por tipo (con el detalle de todas las líneas afectadas),
no una por línea. **Marcar como revisada una venta para revisión (FR-029) es resolver
su alerta `discount_review`**: la venta no cambia, porque es de solo inserción.
`sale.needs_review` queda en verdadero como dato histórico.

Pendientes del Admin y la tarjeta del inicio cuentan estas alertas como las de compras.

**Razón**: reutiliza la tabla y la pantalla de la 1.2. Una alerta por tipo y venta
evita inundar Pendientes.

## R7. Caja: apertura mínima (FR-005 a FR-009, FR-039; RF-29, RF-30, RN-16)

**Decisión**:

- Tabla `cash_session` con las columnas del modelo de datos. `status` solo admite
  `open` en esta etapa; la 1.4 agrega `closed` y las columnas de cierre.
- Se abre con la operación de cola `cash_session.open` (id generado en el equipo, fondo
  en Bs y USD, ambos ≥ 0). Un índice único parcial
  `(device_id) WHERE status = 'open'` impide dos cajas abiertas (FR-006). Si ya hay
  una, rechazo permanente `cash_session_open` con quién y desde cuándo.
- Al abrir, la pantalla pide la tasa aplicable de hoy y muestra el aviso de RF-18 si es
  de otro día. Sin ninguna tasa, no deja abrir, y el servidor rechaza con
  `exchange_rate_missing` (FR-007).
- La venta lleva `cash_session_id`. El servidor exige que sea del mismo equipo y esté
  abierta. Los pagos, vueltos y devoluciones guardan su caja.
- La caja no es inmutable mientras está abierta: un trigger impide borrarla y cambiar
  el equipo, el fondo, quién la abrió y cuándo. La 1.4 amplía el trigger para el
  cierre.

**Razón**: con la caja desde ahora, la venta tiene su forma final y la 1.4 solo agrega
egresos, cierre y cuadre.

## R8. Descuentos y su autorización (FR-020 a FR-029, SC-011; RN-07)

**Decisión**: una sola tabla `discount_authorization` hace de autorización por PIN y de
solicitud.

- **Vínculo con lo autorizado (FR-026)**: la autorización guarda el id de la venta
  (UUID generado en el equipo al empezar la venta), el id de la línea (UUID del equipo)
  o nulo para el total, el tipo (`amount` o `percent`), el valor y el monto base al que
  se aplica (subtotal de la línea, o neto de la venta antes del descuento total). Si
  algo de eso cambia, la autorización ya no coincide.
- **Por PIN**: `POST /discount-authorizations` con `method: "pin"`, el usuario y el PIN
  del Admin y el detalle. El servidor valida el PIN con `pin.verify_admin_pin`
  (bloqueo de 5 intentos, etapa 1.1a) y crea la autorización `approved`. El PIN nunca
  entra en la cola ni en la venta.
- **Por solicitud**: el mismo endpoint con `method: "request"` la crea `pending`. El
  Admin la ve en Pendientes (`GET /discount-authorizations?status=pending`), con quién
  la pide, el producto o el total, el valor y los montos. La aprueba tal cual, la
  aprueba con otro valor del mismo tipo menor o igual al pedido (se guardan
  `requested_value` y el valor aprobado en `discount_value`, y se recalcula
  `discount_usd`), o la rechaza con un motivo opcional. El
  vendedor consulta su estado cada 3 s (`GET /discount-authorizations/{id}`) mientras
  la pantalla la espera, y Pendientes del Admin cada 15 s. Sin WebSockets ni servicios
  nuevos (principio VI). Si se aprobó con otro valor, la pantalla aplica el valor
  aprobado y lo indica.
- **Al registrar la venta**: por cada descuento, si el vendedor es Admin, se registra
  `authorization_method = admin_self` con él mismo como autorizante. Si es Vendedor,
  se busca una autorización `approved` de la misma venta que coincida en línea, tipo,
  valor y base. Si existe, se liga (columna `discount_authorization_id`, única: cada
  autorización se usa una vez). Si no existe, el descuento se registra igual, la venta
  queda `needs_review` y se crea la alerta `discount_review` (FR-028).
- La línea y la venta guardan `discount_authorized_by`, `discount_authorization_method`
  (`pin`, `request`, `admin_self`, o nulo si va a revisión) y la autorización.
- **Límites**: un descuento en monto es > 0 y ≤ la base; un porcentaje es > 0 y ≤ 100,
  con 2 decimales. Uno del 100 % deja la línea o la venta en 0,00 (escenario 6).
- Las autorizaciones pendientes que nunca se usan quedan como historia. No caducan: su
  vínculo con una venta concreta las vuelve inútiles para otra.

**Razón**: una tabla y un camino de validación para los dos métodos. El vínculo por ids
del equipo funciona igual sin conexión en la 1.5.

**Alternativas**: un token firmado con el detalle del descuento (sin rastro en la base
de las solicitudes rechazadas); mandar el PIN dentro de la venta (expone el PIN en la
cola local).

## R9. Inmutabilidad de las ventas en la base (FR-044, SC-010; RN-12)

**Decisión**: igual que en la 1.2, los triggers de la migración `0006` rechazan
`UPDATE` y `DELETE` en `sale`, `sale_item`, `payment` y `sale_void`, y `DELETE` en
`customer`, `cash_session`, `device` y `discount_authorization`. Hay dos excepciones:

- En `discount_authorization` solo se permite pasar de `pending` a `approved` o
  `rejected` (con quién y cuándo).
- En `device` solo se permite fijar `revoked_at` una vez y avanzar
  `last_sequence_number`.

La venta anulada se reconoce por su fila en `sale_void`; la venta en sí no cambia.

## R10. Anulación (FR-041 a FR-043, SC-008; RF-27)

**Decisión**: `POST /sales/{id}/void` (solo Admin, con conexión, motivo de 5 a 500
caracteres). En una transacción:

1. Bloquea la venta.
2. Rechaza con `invalid_state` si ya está anulada.
3. Crea `sale_void`.
4. Por cada línea, registra con `post_movement` un movimiento `sale_void` positivo,
   enlazado a la venta.
5. Por cada pago de la venta registra su espejo en la caja de la venta: un
   `sale_payment` se devuelve con `void_refund` (sale dinero) y un `change` se
   recupera con `void_change` (entra dinero), con el mismo método, monto y tasa.
6. Audita la anulación con el motivo.

**Esperado por método (para la 1.4)**: fondo + `sale_payment` − `change` −
`void_refund` + `void_change` − egresos.

Si la caja de la venta estuviera cerrada (solo posible desde la 1.4), la respuesta es
la de la pregunta abierta del PRD §10; en esta etapa no ocurre.

**Razón**: espejar cada fila es trivial de probar (la suma de la anulación es la
negativa exacta de la venta) y no inventa reglas de reparto.

## R11. Clientes (FR-019; RF-28)

**Decisión**: tabla `customer` con nombre (2–100 caracteres), documento opcional
normalizado y teléfono opcional.

- **Documento**: cédula `V-12345678` o `E-12345678`, o RIF normalizado con
  `domain/rif.py`. Es único entre los clientes que lo tienen.
- **Búsqueda**: `GET /customers?q=` (Admin y Vendedor) busca por documento o nombre.
- **En la venta**: va el `customer_id` de uno existente o un `customer` nuevo con id
  del equipo. Al registrar, si el id ya existe se usa ese cliente. Si no, y el
  documento ya pertenece a otro cliente, se liga a ese. Si tampoco, se crea. Así una
  venta sin conexión de la 1.5 no falla por un cliente repetido.
- No hay pantalla de gestión de clientes en esta etapa; editar clientes llega con el
  crédito (Fase 2).

## R12. Esquemas por rol y consulta de ventas (FR-045 a FR-049, SC-006, SC-007)

**Decisión**:

- `SaleSeller` no tiene costos. `SaleAdmin` agrega por línea `unit_cost_usd` y
  `margin_usd`, y por venta el costo y el margen totales.
- `GET /sales` y `GET /sales/{id}`: el Admin filtra por fechas, número, vendedor,
  cliente, equipo y estado (`registered`, `voided`, `needs_review`). El Vendedor
  siempre recibe solo sus ventas cuya fecha de negocio es hoy en Caracas, aunque pida
  otros filtros; el detalle de una venta ajena o de otro día devuelve 404.
- Almacén: 403 en ventas, caja, clientes y autorizaciones. En el kardex, las salidas
  por venta y los reversos muestran el número de la venta (`MovementSaleRef`), sin
  enlace para el Almacén porque no puede abrirla.
- `unit_cost_usd` de la línea es el costo promedio del producto al registrarse la venta
  en el servidor (FR-049). Un producto sin costo guarda nulo y el margen no se
  calcula.
- `test_no_cost_leak.py` y `test_permissions_matrix.py` se amplían con todos los
  endpoints de la etapa.

## R13. Datos que necesita la pantalla de venta (FR-010, FR-014, SC-002)

**Decisión**:

- La búsqueda reutiliza `GET /products` (el Vendedor ya recibe precio y stock, sin
  costos), filtrada a productos activos con precio. Responde en < 200 ms con 1.000
  productos (etapa 1.1b).
- `GET /exchange-rates/applicable` se abre al Vendedor: hoy solo lo usan Admin y
  Almacén.
- **Tasa de cada venta (FR-014)**: la pantalla consulta la tasa aplicable al empezar
  cada venta y cada 5 minutos mientras hay una abierta. Si cambió y la venta no tiene
  pagos, muestra un aviso y exige actualizarla antes del primer pago; con pagos, la
  venta conserva la suya. La tasa que se envía es siempre la que el vendedor vio.
- La copia local de productos para vender sin conexión es de la etapa 1.5.

## R14. Pantallas (FR-051; R11 de la 1.2)

**Decisión**: rutas estáticas con parámetros de consulta (export estático):

- `/vender`: pantalla de venta. Buscador, líneas con cantidad en m/cm o unidades,
  descuentos, totales en USD y Bs con la fecha de la tasa, pagos y vuelto, cliente
  opcional, advertencia de stock y confirmación con atajos de teclado en PC. Si el
  equipo no está registrado o no tiene caja abierta, lleva a `/caja`.
- `/caja`: estado del equipo y de su caja. Abrir caja con fondo y aviso de tasa. Si el
  usuario es Admin, registrar el equipo.
- `/ventas` y `/ventas/detalle?id=`: consulta, detalle y anulación (Admin).
- `/configuracion/equipos`: lista de equipos y revocación (Admin).
- `/pendientes`: suma las solicitudes de descuento y las alertas nuevas.
- La barra de la app muestra "Ventas pendientes de envío: N" mientras la cola tenga
  operaciones, y avisa antes de cerrar sesión si hay pendientes (ADR-0003).

## R15. Auditoría de la etapa (FR-050; RF-46)

Acciones nuevas:

- `device.registered`, `device.revoked`;
- `cash_session.opened` (fondo);
- `sale.discounted`: una por venta con descuentos, con el detalle de cada descuento,
  quién autorizó y el método;
- `discount_authorization.requested`, `discount_authorization.approved`,
  `discount_authorization.rejected`;
- `sale.voided`, con el motivo.

Se mantienen `auth.pin_verified` y `alert.resolved`. Las ventas sin descuento no se
auditan: la venta misma es el registro inmutable. `packages/shared/src/audit-actions.ts`
suma el grupo "Ventas y caja".

## R16. Rendimiento y límites (SC-001, SC-002, SC-004, SC-005)

- **Límites**: hasta 100 líneas, 10 pagos y 5 vueltos por venta (422 si se superan).
- **Registro**: una venta de 20 líneas se registra en el servidor en < 1 s, medido en
  una prueba.
- **Idempotencia**: 10 envíos simultáneos de la misma operación dejan una venta
  (SC-004).
- **Numeración**: dos equipos que envían 50 ventas cada uno en paralelo, sin números
  repetidos (SC-005).
- **Bloqueos**: los productos de una venta se bloquean en orden de id para evitar
  bloqueos cruzados entre ventas simultáneas (como R3 de la 1.2).
