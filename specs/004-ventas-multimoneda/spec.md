# Feature Specification: Ventas multimoneda, pagos mixtos y descuentos (etapa 1.3)

**Feature Branch**: `004-ventas-multimoneda`

**Created**: 2026-10-15

**Status**: Draft

**Input**: User description: "Etapa 1.3 de la Fase 1: ventas multimoneda, pagos mixtos y descuentos (docs/plan-de-fases.md §1.3; RF-18, RF-20 a RF-28, RN-01 a RN-07, RN-10, RN-11; PRD v0.10). Incluye: uso de la tasa BCV vigente en la venta y aviso de tasa faltante usando la última con su fecha (RF-18); registro de equipos de mostrador y series para correlativos únicos entre equipos (RN-11); pantalla de venta con búsqueda de productos, cantidades por metro (ingreso en m o cm) o por unidad, totales en USD y Bs (RN-02); descuentos por ítem o sobre el total, en monto o porcentaje, con autorización del admin por PIN o aprobación (RF-22, RN-07; sin conexión se permiten y la venta queda marcada para revisión); vender sin stock suficiente con advertencia y alerta al admin (RN-10); pagos mixtos con los 6 métodos y referencia obligatoria salvo efectivo (RF-23, RF-24), vuelto con método y moneda (RF-25); la venta guarda tasa, ítems, descuentos, pagos y vendedor (RF-26, RN-05); cliente opcional (RF-28); anulación solo admin con motivo que devuelve stock (RF-27); módulo de dinero en Python y TypeScript con casos compartidos (ADR-0004). Las ventas se envían por la cola de salida con clave de idempotencia (ADR-0003) aunque se use solo con conexión. La caja (RF-29 a RF-33) es la etapa 1.4: definir cómo se relaciona la venta con la caja mientras no exista."

**Requisitos del PRD**: RF-18, RF-20 a RF-28, RF-29 y RF-30 (apertura de caja, adelantada de la 1.4), RN-01 a RN-07, RN-10, RN-11, RN-13, RN-16, RN-18 (también RF-08 para el kardex, RF-46 para la auditoría, RNF-02, RNF-04, RNF-05 y RNF-07; supuesto 4 del PRD §9). Decisiones técnicas previas: ADR-0003 (cola de salida, idempotencia y numeración por equipo) y ADR-0004 (dinero, cantidades y redondeo). Principios de la constitución: I (integridad monetaria), II (kardex e inmutabilidad), III (ventas sin conexión: la venta ya viaja por la cola de salida), IV (sin costos para el Vendedor) y VII (pruebas de conversión, pagos mixtos, vuelto, cm→m y reversos).

## Clarifications

### Session 2026-10-15

- Q: Con conexión, ¿se puede vender un producto sin stock suficiente? → A: Sí, con
  advertencia antes de registrar la venta; si el stock queda negativo, se genera una
  alerta para el Admin (RN-10, PRD v0.10) (User Story 5, FR-030 a FR-032).
- Q: ¿Se permiten descuentos sin conexión? → A: Sí; el vendedor puede aplicarlos y la
  venta queda marcada para que el Admin la revise al sincronizar (RN-07, PRD v0.10). En
  esta etapa el servidor ya acepta y marca esas ventas; el flujo completo sin conexión
  llega en la 1.5 (FR-028, FR-029).
- Q: El PRD exige caja abierta para vender (RF-30), pero la caja es la etapa 1.4. ¿Cómo
  se relaciona la venta con la caja en la 1.3? → A: La apertura de caja con fondo
  inicial y una caja abierta por equipo (RF-29, RF-30, RN-16) se adelanta a esta etapa,
  para que cada venta y cada pago queden ligados a su caja desde el principio. Egresos,
  cierre y cuadre siguen en la 1.4 (User Story 1, FR-005 a FR-009).
- Q: Si un cliente devuelve solo parte de lo que compró, ¿hay devolución parcial? → A:
  No: solo anulación completa; para devolver una parte se anula la venta y se registra
  una nueva con lo que el cliente se queda (FR-041).
- Q: ¿El vuelto debe ser exactamente el excedente? → A: No: puede ser menor o igual;
  la diferencia queda como sobrepago visible en la venta y la caja cuenta el dinero
  real (FR-038).
- Q: Al aprobar una solicitud de descuento, ¿el Admin puede cambiar el valor? → A: Sí:
  puede aprobarla con otro valor del mismo tipo, menor o igual al pedido, y el vendedor
  recibe el descuento ajustado, que es el que se aplica a la venta (FR-025, FR-026).
- Q: Si el Admin carga la tasa del día con la caja abierta o con una venta a medio
  hacer, ¿desde cuándo se usa? → A: Cada venta toma la tasa vigente al empezar; si
  cambia mientras se arma, se avisa para actualizarla antes de registrar pagos; con un
  pago registrado, la tasa de esa venta queda fija (FR-014).
- Q: Si una venta llega con una tasa que no coincide con la tasa BCV cargada para su
  fecha, ¿qué hace el servidor? → A: La registra con la tasa del equipo y crea una
  alerta "Tasa distinta" para el Admin (FR-032).
- Q: ¿A nombre de quién queda una venta enviada desde el mostrador? → A: Del usuario
  de la sesión que la envía; otro vendedor en la venta se rechaza. La regla para
  ventas sin conexión enviadas después por otro usuario se define en la 1.5 (FR-015).
- Q: Si se revoca un equipo con ventas sin enviar, ¿qué pasa con ellas? → A: Se
  aceptan las operaciones creadas antes de la revocación; las posteriores se rechazan
  (FR-002).
- Q: ¿Cómo se interpreta un documento escrito sin guiones, como `V123456789`? → A: Con
  `V` o `E` siempre es cédula (6 a 8 dígitos); el RIF de una persona natural se escribe
  con guiones (`V-12345678-9`). Con `J`, `G`, `P` o `C` es RIF (FR-019).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Equipo de mostrador y apertura de caja (Priority: P1)

El Admin registra una sola vez, con conexión, el equipo del mostrador (la PC o tablet
desde la que se vende). El sistema le asigna una serie (`A`, luego `B`…) que identifica
sus ventas. Al comenzar el día, el vendedor abre la caja de ese equipo indicando el
fondo inicial en efectivo Bs y efectivo USD. Si la tasa BCV del día todavía no está
cargada, el sistema lo avisa al abrir la caja y muestra la fecha de la última tasa
disponible.

**Why this priority**: toda venta necesita un equipo registrado (su número sale de la
serie del equipo, RN-11) y una caja abierta en ese equipo (RF-30). Sin esto no hay
ventas.

**Independent Test**: como Admin, registrar el equipo "Mostrador principal" y comprobar
que recibe la serie `A`; registrar un segundo equipo y ver que recibe `B`. Como
Vendedor, en el equipo `A`, abrir caja con 500,00 Bs y 20,00 USD; intentar abrir otra
caja en el mismo equipo y ver que se rechaza. Sin tasa del día, ver el aviso con la
fecha de la última tasa.

**Acceptance Scenarios**:

1. **Given** un navegador sin equipo registrado, **When** el Admin lo registra con el
   nombre "Mostrador principal", **Then** el equipo recibe la primera serie libre y
   queda listo para abrir caja y vender.
2. **Given** un equipo revocado con serie `A`, **When** el Admin registra un equipo
   nuevo, **Then** recibe `B`: una serie nunca se reutiliza.
3. **Given** un equipo registrado sin caja abierta, **When** el Vendedor abre caja con
   500,00 Bs y 20,00 USD de fondo, **Then** la caja queda abierta a su nombre, con el
   fondo, la fecha y la hora.
4. **Given** un equipo con caja abierta, **When** alguien intenta abrir otra en ese
   equipo, **Then** se rechaza y se indica quién tiene la caja abierta y desde cuándo
   (RN-16).
5. **Given** que hoy no se cargó la tasa y la última es de ayer, **When** el Vendedor
   abre caja, **Then** ve el aviso "No hay tasa BCV de hoy; se usará la del dd/mm/aaaa"
   y puede abrir igual (RF-18).
6. **Given** un usuario de Almacén, **When** intenta abrir caja o vender, **Then** el
   servidor lo rechaza.

---

### User Story 2 - Venta con un solo pago (Priority: P1)

El vendedor busca productos por nombre, SKU o medida, los agrega a la venta con su
cantidad (por unidad, o por metro escribiendo metros o centímetros) y ve el total en
USD y en Bs con la tasa vigente. Opcionalmente anota el cliente. Cobra con un método
de pago y confirma. La venta recibe su número (`A-000001`), descuenta el stock mediante
movimientos de kardex y queda guardada con su tasa, sus ítems, su pago, el vendedor y
la caja.

**Why this priority**: es el corazón del sistema; el objetivo del negocio es vender
rápido y con totales correctos en las dos monedas.

**Independent Test**: con caja abierta y tasa 36,50, vender 2 conexiones a 3,25 USD y
30 cm de manguera a 4,00 USD/m; ver subtotales 6,50 y 1,20, total 7,70 USD y
281,05 Bs; cobrar 7,70 en Efectivo USD; comprobar el número `A-000001`, las dos salidas
en el kardex y el stock descontado (0,30 m de la manguera).

**Acceptance Scenarios**:

1. **Given** un producto por metro a 4,00 USD/m, **When** el vendedor escribe `30 cm`,
   **Then** la línea muestra 0,30 m y 1,20 USD, y al confirmar se descuentan 0,30 m del
   inventario (RF-21).
2. **Given** un producto por unidad, **When** el vendedor escribe 1,5, **Then** el
   sistema no lo acepta: las unidades son enteras (RF-21).
3. **Given** un producto por metro, **When** el vendedor escribe `0,305 m` o `30,5 cm`,
   **Then** el sistema no lo acepta: la precisión es de centímetro; no se redondea en
   silencio.
4. **Given** una venta de 7,70 USD con tasa 36,50, **When** se muestra el total,
   **Then** se ve 7,70 USD y 281,05 Bs, y el total en Bs se calcula sobre el total en
   USD, no sumando líneas (RN-02).
5. **Given** la venta lista, **When** el vendedor la confirma con un pago que la cubre,
   **Then** la venta queda registrada con el siguiente número de la serie del equipo,
   la tasa usada y su fecha, los ítems con su precio unitario, el pago, el vendedor y
   la caja (RF-26, RN-05).
6. **Given** que se cortó la conexión al confirmar, **When** la app reintenta el envío,
   **Then** el servidor no duplica la venta ni el kardex: devuelve la venta ya
   registrada (ADR-0003).
7. **Given** un producto inactivo o sin precio de venta, **When** el vendedor lo busca,
   **Then** no aparece como vendible.
8. **Given** una venta, **When** el vendedor agrega el cliente (nombre, cédula o RIF y
   teléfono) o elige uno ya registrado, **Then** la venta lo guarda; sin cliente también
   se registra (RF-28).
9. **Given** una venta por un Vendedor, **When** consulta su detalle, **Then** nunca ve
   costos ni márgenes (principio IV).

---

### User Story 3 - Pagos mixtos y vuelto (Priority: P1)

El cliente paga con varios métodos: parte en dólares en efectivo, parte por pago móvil
en bolívares, etc. El sistema muestra cuánto falta en USD y en Bs después de cada pago,
exige referencia en los métodos que la requieren y, si el cliente paga de más, calcula
el vuelto y registra en qué método y moneda se entregó.

**Why this priority**: en Venezuela casi toda venta mezcla monedas y métodos; sin pagos
mixtos el sistema no sirve para el mostrador.

**Independent Test**: venta de 50,00 USD con tasa 36,50: pagar 20,00 en Efectivo USD,
luego 730,00 Bs por Pago móvil con referencia (cubre 20,00 USD) y 10,00 USD en Zelle sin
referencia (rechazado) y con referencia (aceptado); comprobar que falta 0,00. Otra venta de 7,70 USD pagada con un billete de 10,00 USD: vuelto 2,30 USD en
Efectivo USD, o 83,95 Bs en Efectivo Bs.

**Acceptance Scenarios**:

1. **Given** una venta con total 50,00 USD y tasa 36,50, **When** se registra un pago
   de 730,00 Bs, **Then** cubre 20,00 USD (730,00 ÷ 36,50, RN-06) y el saldo pendiente
   se muestra en USD y en Bs.
2. **Given** un pago en Zelle, Binance USDT o Efectivo USD, **When** se registra,
   **Then** cubre su monto 1:1 en USD (RN-04).
3. **Given** un pago por Pago móvil, Punto de venta, Zelle o Binance USDT, **When** no
   tiene referencia, **Then** no se acepta; en Efectivo Bs y Efectivo USD la referencia
   no se pide (RF-24).
4. **Given** pagos que no cubren el total, **When** el vendedor intenta confirmar,
   **Then** no se permite: en esta fase no hay ventas a crédito.
5. **Given** pagos que superan el total en 2,30 USD, **When** el vendedor elige
   entregar el vuelto en Efectivo Bs con tasa 36,50, **Then** el vuelto es 83,95 Bs y
   queda registrado con su método y moneda (RF-25).
6. **Given** que el cliente paga el monto exacto en Bs que muestra la pantalla para el
   saldo pendiente, **When** se registra, **Then** el saldo queda en cero (sin un
   céntimo de diferencia por redondeo).
7. **Given** un cliente que paga por Zelle y recibe el vuelto en Efectivo Bs, **When**
   se registra, **Then** se permite: el vuelto puede entregarse en cualquier método o
   moneda (supuesto 4), pero nunca supera el excedente pagado.
8. **Given** un excedente de 0,30 USD y sin sencillo, **When** el vendedor registra un
   vuelto menor o ninguno, **Then** la venta se confirma y el detalle muestra el
   sobrepago de la diferencia.

---

### User Story 4 - Descuentos autorizados (Priority: P2)

Para atender a talleres y clientes frecuentes (RN-18), se aplican descuentos a un ítem
o al total de la venta, en monto en USD o en porcentaje. Si vende el Admin, aplica el
descuento directamente. Si vende un Vendedor, necesita la autorización del Admin: el
Admin escribe su PIN en el equipo en ese momento, o el vendedor envía una solicitud que
el Admin aprueba desde su propia sesión. La venta guarda quién autorizó cada descuento.

**Why this priority**: es frecuente en el negocio, pero se puede vender sin descuentos;
por eso va después de la venta y los pagos.

**Independent Test**: como Vendedor, aplicar 10 % a una línea de 20,00 USD; ver que
pide autorización; autorizar con el PIN del Admin; comprobar que la línea queda en
18,00 USD y que la venta registra al Admin como autorizante. Repetir con un descuento
de 5,00 USD sobre el total, por solicitud que el Admin aprueba desde otro equipo.

**Acceptance Scenarios**:

1. **Given** una línea de 20,00 USD, **When** se aplica 10 %, **Then** su descuento es
   2,00 USD y su neto 18,00 USD.
2. **Given** una venta con descuento sobre el total, **When** se registra, **Then** el
   descuento se reparte entre las líneas en proporción a su neto y la suma de lo
   repartido es exactamente el descuento total (ADR-0004).
3. **Given** un Vendedor que aplica un descuento, **When** el Admin escribe un PIN
   correcto, **Then** el descuento se aplica y queda registrado quién autorizó, cómo
   (PIN) y cuándo (RN-07).
4. **Given** un PIN incorrecto 5 veces, **When** se intenta de nuevo, **Then** el PIN
   queda bloqueado 15 minutos (regla ya vigente desde la etapa 1.1a) y el descuento no
   se aplica.
5. **Given** un Vendedor que envía una solicitud de descuento, **When** el Admin la ve
   en su sesión y la aprueba, **Then** el vendedor ve la aprobación y puede confirmar la
   venta con ese descuento; si el Admin la rechaza, el descuento no se aplica.
5a. **Given** una solicitud de 10 % sobre una línea, **When** el Admin la aprueba con
   5 %, **Then** el vendedor ve que se aprobó con 5 %, la línea queda con ese descuento
   y la venta registra el valor pedido y el aprobado; el Admin no puede aprobar un valor
   mayor que el pedido ni cambiar el tipo (monto o porcentaje).
6. **Given** un descuento mayor que el monto al que se aplica, **When** se intenta,
   **Then** no se acepta: ninguna línea ni venta queda en negativo; un descuento del
   100 % sí se permite.
7. **Given** una venta que llega al servidor con un descuento de Vendedor sin
   autorización válida (por ejemplo, hecha sin conexión), **When** se registra,
   **Then** se acepta tal como se hizo, queda marcada para revisión del Admin y se
   genera una alerta (RN-07).
8. **Given** cualquier descuento aplicado, **When** se registra la venta, **Then**
   queda en la auditoría (RF-46).

---

### User Story 5 - Venta sin stock suficiente (Priority: P2)

Si el vendedor agrega más cantidad de la que el sistema tiene en stock (porque el
inventario está desactualizado o la mercancía llegó y no se registró), el sistema lo
advierte pero permite vender. Si la venta deja el stock negativo, el Admin recibe una
alerta para revisar el inventario.

**Why this priority**: evita perder ventas por un inventario mal cargado y, a la vez,
avisa al Admin para corregirlo.

**Independent Test**: con un producto con stock 2, vender 3; ver la advertencia,
confirmar y comprobar que el stock queda en −1 y que aparece una alerta de stock
negativo en Pendientes del Admin.

**Acceptance Scenarios**:

1. **Given** un producto con stock 2, **When** el vendedor agrega 3, **Then** ve una
   advertencia con el stock disponible y puede continuar (RN-10).
2. **Given** la venta confirmada, **When** el stock del producto queda negativo,
   **Then** la venta se registra igual y se crea una alerta para el Admin con el
   producto, la venta y el stock resultante.
3. **Given** un Vendedor, **When** ve la advertencia, **Then** solo ve el stock actual,
   nunca costos ni el kardex.

---

### User Story 6 - Anulación de una venta (Priority: P2)

El Admin anula una venta registrada por error, indicando el motivo. La venta no se
borra: queda marcada como anulada, el stock vuelve con movimientos de reverso y los
pagos se revierten con devoluciones en la caja.

**Why this priority**: los errores de mostrador pasan; sin anulación el stock y la caja
dejan de cuadrar.

**Independent Test**: anular la venta `A-000001` como Admin con el motivo "Cliente
devolvió la mercancía"; comprobar que el stock vuelve, que el kardex muestra los
reversos, que se registran las devoluciones de los pagos y el vuelto en la caja y que
la acción queda auditada. Intentarlo como Vendedor y ver que se rechaza.

**Acceptance Scenarios**:

1. **Given** una venta registrada, **When** el Admin la anula con motivo, **Then** se
   genera un movimiento de reverso por cada línea, se registran devoluciones por los
   pagos (neto del vuelto) y la venta queda anulada con quién, cuándo y por qué (RF-27).
2. **Given** una anulación sin motivo, **When** se intenta, **Then** se rechaza.
3. **Given** una venta ya anulada, **When** se intenta anular de nuevo, **Then** se
   rechaza; una venta no se anula dos veces.
4. **Given** un Vendedor o un usuario de Almacén, **When** intenta anular, **Then** el
   servidor lo rechaza.
5. **Given** una venta, **When** alguien intenta modificarla o borrarla (incluso
   directamente en la base de datos), **Then** no es posible: solo se anula (RN-12).

---

### User Story 7 - Consulta de ventas (Priority: P3)

El Admin consulta las ventas por fecha, número, vendedor, cliente, equipo y estado
(registrada, anulada, marcada para revisión) y abre el detalle con ítems, descuentos,
pagos, vuelto, tasa y quién autorizó. El Vendedor solo ve sus propias ventas del día.

**Why this priority**: necesaria para revisar y anular, pero el negocio puede vender
sin ella los primeros días.

**Independent Test**: con ventas de dos vendedores en dos días, comprobar que el Admin
ve y filtra todas y que cada Vendedor solo ve sus ventas de hoy, sin costos.

**Acceptance Scenarios**:

1. **Given** ventas de varios días y vendedores, **When** el Admin filtra por rango de
   fechas y vendedor, **Then** ve solo esas ventas, con fechas `dd/mm/aaaa` y montos
   `1.234,56`.
2. **Given** un Vendedor, **When** consulta ventas, **Then** solo recibe las suyas del
   día (hora de Caracas), aunque pida otras fechas o vendedores.
3. **Given** el detalle de una venta, **When** lo abre el Admin, **Then** ve el costo
   unitario y el margen de cada línea; el Vendedor nunca los recibe.
4. **Given** el kardex de un producto, **When** el Admin o Almacén ve una salida por
   venta, **Then** puede ir a la venta que la originó.

---

### Edge Cases

- **Sin ninguna tasa cargada**: no se puede abrir caja ni vender; se avisa que el Admin
  debe cargar la tasa BCV.
- **Tasa corregida después de vender**: las ventas ya registradas conservan la tasa con
  la que se hicieron (RN-05, RN-15).
- **Tasa nueva con una venta a medio hacer**: sin pagos, aviso y actualización de la
  tasa de la venta antes del primer pago; con pagos, la venta conserva su tasa
  (FR-014).
- **Cambio de precio mientras la venta está en pantalla**: la venta usa el precio que
  el equipo mostró; si al registrarse no coincide con el vigente en el servidor, se
  registra igual y se alerta al Admin (ADR-0003).
- **Total distinto entre el equipo y el servidor**: prevalece el del servidor, se
  conserva el del equipo y se alerta al Admin (ADR-0003). Con los casos compartidos
  (FR-040) esto no debería ocurrir.
- **El mismo producto dos veces en la venta**: se permite (por ejemplo, dos tramos de
  manguera de distinto largo); cada línea es independiente (RN-13).
- **Línea con cantidad cero**: no se acepta.
- **Venta sin líneas**: no se puede confirmar.
- **Pago con monto cero o negativo**: no se acepta.
- **Pagos que cubren exactamente con redondeo en Bs**: el saldo se considera cubierto
  cuando el monto en Bs pagado iguala el saldo mostrado en Bs (User Story 3, escenario
  6).
- **Usuario desactivado o sesión vencida con una venta en la cola**: en esta etapa la
  venta la envía el mismo vendedor con su sesión, así que se reenvía al volver a
  ingresar. El caso de ventas sin conexión enviadas por otro usuario, con la alerta de
  vendedor desactivado, se define en la 1.5 (ADR-0003).
- **Equipo revocado**: no puede abrir caja ni vender; las ventas que tenía en la cola se
  aceptan si se hicieron antes de la revocación (FR-002).
- **Tasa de la venta distinta de la cargada** (error, manipulación o tasa corregida
  después de vender): la venta se registra con la tasa del equipo y se alerta al Admin
  (FR-032).
- **Anular una venta cuya caja ya está cerrada**: en esta etapa no hay cierre de caja;
  la devolución va a la caja de la venta. Qué caja recibe la devolución cuando esa caja
  ya está cerrada se decide antes de la etapa 1.4 (PRD §10).
- **Venta con varios descuentos de ítem y uno sobre el total**: el descuento total se
  calcula sobre la suma de los netos de las líneas (ADR-0004).
- **Solicitud de descuento pendiente y el vendedor cambia la venta**: si cambia la línea
  o el total afectado, la solicitud deja de valer y debe pedirse de nuevo.
- **Dos vendedores en el mismo equipo**: venden en la misma caja abierta; cada venta
  guarda quién la hizo (RN-16).
- **Vuelto sin efectivo suficiente en caja**: el sistema no lo impide en esta etapa (el
  cuadre de caja llega en la 1.4).

## Requirements *(mandatory)*

### Functional Requirements

**Equipos y caja**

- **FR-001**: El Admin MUST poder registrar un equipo de mostrador con un nombre, desde
  ese mismo equipo y con conexión. El sistema MUST asignarle la siguiente serie libre
  (`A`, `B`, …, y luego combinaciones de letras) que nunca se reutiliza (RN-11,
  ADR-0003).
- **FR-002**: El Admin MUST poder ver los equipos registrados y revocar uno; un equipo
  revocado no puede abrir caja ni vender, y su serie no vuelve a asignarse. Las
  operaciones que el equipo creó antes de la revocación y aún no había enviado se
  aceptan; las creadas después se rechazan.
- **FR-003**: Solo se MUST poder vender desde un equipo registrado y vigente.
- **FR-004**: Si el equipo pierde sus datos locales, MUST registrarse de nuevo y recibir
  una serie nueva.
- **FR-005**: Admin y Vendedor MUST poder abrir caja en un equipo registrado, con fondo
  inicial en efectivo Bs y efectivo USD (cero permitido) (RF-29).
- **FR-006**: Un equipo MUST tener como máximo una caja abierta, garantizado también en
  la base de datos (RN-16).
- **FR-007**: Al abrir caja sin tasa del día, el sistema MUST avisarlo y mostrar la
  fecha de la última tasa; sin ninguna tasa cargada, MUST impedir abrir caja (RF-18).
- **FR-008**: Una venta MUST registrarse solo con una caja abierta en el equipo (RF-30);
  cualquier usuario que pueda vender, vende en la caja abierta de ese equipo y la venta
  guarda quién la hizo (RN-16).
- **FR-009**: Egresos, cierre y cuadre de caja quedan fuera de esta etapa (1.4); la caja
  abierta en esta etapa queda abierta hasta entonces.

**Venta**

- **FR-010**: El vendedor MUST poder buscar productos activos con precio de venta por
  nombre, SKU o medida, con resultados en menos de 1 segundo (RNF-04), viendo precio en
  USD y Bs y stock actual.
- **FR-011**: El sistema MUST validar la cantidad según la unidad: `unidad` solo
  enteros; `metro` hasta 2 decimales, con ingreso en metros o en centímetros convertido
  a metros (`cm ÷ 100`) antes de calcular precio y stock. Cantidades con más precisión
  se rechazan, no se redondean (RF-21, ADR-0004).
- **FR-012**: El precio unitario de cada línea MUST ser el precio de venta vigente del
  producto; el vendedor no lo cambia (RN-18). Las rebajas se hacen con descuentos
  (FR-020).
- **FR-013**: El sistema MUST calcular subtotal por línea, descuentos, total en USD y
  total en Bs (total USD × tasa, redondeado a 2 decimales con mitad hacia arriba) en el
  equipo y en el servidor con exactamente las mismas reglas (RN-02, ADR-0004).
- **FR-014**: La venta MUST usar la tasa BCV del día o, si no hay, la última disponible,
  mostrando su fecha (RF-18), y guardar la tasa y su fecha; nunca se recalcula (RN-05).
  Cada venta toma la tasa vigente al empezar. Si la tasa vigente cambia mientras la
  venta se arma y todavía no tiene pagos, el sistema MUST avisarlo y pedir que se
  actualice (recalculando los montos en Bs) antes de registrar el primer pago; con al
  menos un pago registrado, la
  tasa de la venta queda fija y la nueva aplica desde la venta siguiente. El equipo MUST
  comprobar la tasa vigente al empezar cada venta y al menos cada 5 minutos mientras
  una venta está abierta.
- **FR-015**: Cada venta MUST guardar: número, fecha y hora, fecha de negocio (Caracas),
  vendedor, equipo, caja, cliente (opcional), ítems con cantidad y precio unitario en
  USD, descuentos con quién los autorizó, tasa y su fecha, totales en USD y Bs, pagos y
  vuelto (RF-26). El vendedor de la venta MUST ser el usuario de la sesión que la envía;
  si la venta indica otro, se rechaza (en la 1.5 se define el caso de ventas sin
  conexión enviadas después por otro usuario).
- **FR-016**: El número de venta MUST ser `{serie}-{correlativo de 6 dígitos}` (ej.
  `A-000123`), asignado por el equipo con su propio contador, único en la base de datos
  (RN-11).
- **FR-017**: Toda venta MUST enviarse por la cola de salida con un identificador único
  generado en el equipo; reenviarla MUST devolver la venta ya registrada sin duplicar
  venta, pagos ni movimientos (ADR-0003). La app MUST mostrar las ventas pendientes de
  envío y reintentarlas sola.
- **FR-018**: Al registrar una venta, el servidor MUST recalcularla y aplicar en una sola
  transacción la venta, los pagos, una salida de kardex por línea y la auditoría (RF-08,
  ADR-0003). Ninguna parte queda aplicada a medias.
- **FR-019**: El cliente MUST ser opcional: nombre, cédula o RIF y teléfono; se puede
  elegir uno ya registrado (buscando por documento o nombre) o crearlo en la venta. La
  cédula o RIF no se repite entre clientes (RF-28). Con `V` o `E` el documento es una
  cédula (6 a 8 dígitos, por ejemplo `V-12345678`); el RIF de una persona natural se
  escribe con guiones (`V-12345678-9`); con `J`, `G`, `P` o `C` es un RIF.

**Descuentos**

- **FR-020**: Se MUST poder aplicar descuentos a un ítem y/o al total de la venta, cada
  uno como monto en USD o como porcentaje (RF-22); el descuento no puede superar el
  monto al que se aplica.
- **FR-021**: El descuento sobre el total MUST repartirse entre las líneas en proporción
  a su neto, con el residuo de redondeo en la línea de mayor neto, y la suma repartida
  MUST ser exactamente el descuento total (ADR-0004).
- **FR-022**: El Admin MUST poder aplicar descuentos en sus ventas sin otra
  autorización; queda registrado como autorizado por él mismo.
- **FR-023**: Un descuento del Vendedor MUST requerir autorización del Admin, por PIN
  escrito en el equipo o por solicitud aprobada (RN-07).
- **FR-024**: La autorización por PIN MUST validarse en el servidor y respetar el
  bloqueo tras 5 intentos fallidos (etapa 1.1a).
- **FR-025**: El Vendedor MUST poder enviar una solicitud de descuento con el detalle
  (línea o total, tipo y valor, montos afectados); el Admin MUST verla en su sesión y
  aprobarla tal cual, aprobarla con otro valor del mismo tipo menor o igual al pedido,
  o rechazarla (con motivo opcional); el vendedor MUST ver la respuesta, con el valor
  aprobado, sin recargar a mano.
- **FR-026**: Una autorización (por PIN o solicitud) MUST valer solo para el descuento
  autorizado, con el valor aprobado; si cambia la línea, el monto afectado o el valor,
  se pide de nuevo. La autorización guarda el valor pedido y el aprobado.
- **FR-027**: Cada descuento MUST guardar quién lo autorizó, cómo (`PIN`, `solicitud`,
  `admin vende`) y cuándo, y quedar en la auditoría (RN-07, RF-46).
- **FR-028**: Si una venta llega al servidor con un descuento de Vendedor sin
  autorización válida, el servidor MUST registrarla igual, marcarla para revisión y
  crear una alerta para el Admin (RN-07, PRD v0.10).
- **FR-029**: El Admin MUST poder marcar como revisada una venta marcada para revisión;
  la venta no cambia (para corregirla se anula).

**Stock**

- **FR-030**: Si la cantidad de una línea supera el stock actual, el sistema MUST
  advertirlo antes de confirmar, mostrando el stock disponible, y permitir continuar
  (RN-10).
- **FR-031**: Una venta MUST registrarse aunque deje stock negativo; en ese caso MUST
  crearse una alerta para el Admin con producto, venta y stock resultante (RN-10).
- **FR-032**: Si el precio de una línea no coincide con el precio vigente en el
  servidor, el total calculado en el equipo difiere del recalculado, o la tasa de la
  venta no coincide con la tasa BCV cargada para su fecha (o no hay tasa cargada para
  esa fecha), la venta MUST registrarse (prevalece el cálculo del servidor, se conserva
  el del equipo y la tasa enviada) y MUST crearse una alerta (ADR-0003).

**Pagos y vuelto**

- **FR-033**: Una venta MUST admitir uno o varios pagos con los métodos Efectivo Bs,
  Pago móvil / transferencia, Punto de venta, Efectivo USD, Zelle y Binance USDT
  (RF-23, RF-24).
- **FR-034**: Todo método excepto Efectivo Bs y Efectivo USD MUST exigir referencia
  (RF-24).
- **FR-035**: Un pago en Bs MUST cubrir en USD `monto Bs ÷ tasa de la venta`,
  redondeado a 2 decimales; USD, Zelle y USDT cubren 1:1 (RN-04, RN-06). Cada pago
  guarda su monto en su moneda, su equivalente en USD y la tasa de la venta (RN-05).
- **FR-036**: El sistema MUST mostrar el saldo pendiente en USD y en Bs después de cada
  pago, y el monto en Bs sugerido para cubrir el saldo MUST cubrirlo exactamente.
- **FR-037**: Una venta MUST confirmarse solo si los pagos cubren el total; no hay
  ventas a crédito en la Fase 1.
- **FR-038**: Si los pagos superan el total, el sistema MUST calcular el vuelto y
  registrarlo con su método y moneda (cualquiera de los seis, con referencia si el
  método la exige); el vuelto en Bs es excedente USD × tasa, redondeado (RF-25,
  ADR-0004). El vuelto puede ser uno o varios (por ejemplo, parte en USD y parte en
  Bs), y su total en USD MUST ser menor o igual que el excedente; si es menor (por
  ejemplo, no hay sencillo y el cliente deja la diferencia), la diferencia queda como
  sobrepago, visible en el detalle de la venta.
- **FR-039**: Cada pago y vuelto MUST quedar ligado a la caja de la venta.

**Dinero compartido**

- **FR-040**: Los cálculos de dinero y cantidades (líneas, cm→m, descuentos y reparto,
  totales, Bs, pagos, saldo y vuelto) MUST tener casos de prueba compartidos que el
  equipo y el servidor ejecutan con resultados idénticos; si difieren, la integración
  continua falla (ADR-0004, principio VII).

**Anulación**

- **FR-041**: Solo el Admin MUST poder anular una venta, con motivo obligatorio (RF-27).
  La anulación es siempre de la venta completa: no hay devoluciones parciales; para
  devolver una parte se anula y se registra una venta nueva con lo que el cliente se
  queda.
- **FR-042**: Anular MUST generar un movimiento de reverso de kardex por cada línea, y
  devoluciones de dinero en la caja de la venta por los pagos netos del vuelto, en una
  sola transacción (RF-27). La caja que recibe la devolución cuando la caja de la venta
  ya está cerrada se define en la etapa 1.4.
- **FR-043**: Una venta MUST anularse como máximo una vez; la anulación queda en la
  auditoría con motivo, usuario y fecha (RF-46).
- **FR-044**: Ventas, ítems, pagos y anulaciones MUST ser inmutables, también ante
  cambios directos en la base de datos (RN-12).

**Consulta, permisos y auditoría**

- **FR-045**: El Admin MUST poder consultar ventas por rango de fechas, número,
  vendedor, cliente, equipo y estado, y abrir su detalle completo con costo unitario y
  margen por línea.
- **FR-046**: El Vendedor MUST ver solo sus propias ventas del día (hora de Caracas),
  sin costos ni márgenes; el servidor lo impone (matriz de permisos).
- **FR-047**: El Almacén MUST NOT registrar, ver ni anular ventas, ni abrir caja; sí ve
  en el kardex las salidas por venta y su número.
- **FR-048**: Cada salida de kardex por venta y cada reverso por anulación MUST enlazar
  a su venta.
- **FR-049**: Cada línea MUST guardar el costo promedio del producto al registrarse la
  venta en el servidor, visible solo para el Admin (base del margen, RF-42).
- **FR-050**: Se MUST auditar: registro y revocación de equipos, apertura de caja,
  descuentos y su autorización, solicitudes de descuento aprobadas o rechazadas,
  anulación de ventas y alertas revisadas (RF-46).
- **FR-051**: Montos con formato `1.234,56`, fechas `dd/mm/aaaa` y hora de Caracas en
  toda la interfaz (RNF-07); pantalla de venta usable en PC, tablet y teléfono
  (RNF-02).

### Key Entities *(include if feature involves data)*

- **Equipo**: dispositivo de mostrador registrado por el Admin; nombre, serie única que
  nunca se reutiliza, contador de ventas, estado (vigente o revocado).
- **Caja**: sesión de caja de un equipo; quién la abrió y cuándo, fondo inicial en Bs y
  USD, estado (abierta; el cierre llega en la 1.4). Una abierta por equipo.
- **Cliente**: nombre, cédula o RIF (único, opcional) y teléfono.
- **Venta**: número `{serie}-{correlativo}`, equipo, caja, vendedor, cliente opcional,
  fecha y hora, tasa y su fecha, descuento sobre el total, totales en USD y Bs, total
  calculado en el equipo, marca de revisión, estado (registrada o anulada).
- **Línea de venta**: producto, cantidad en su unidad, precio unitario en USD,
  subtotal, descuento propio, parte del descuento total, neto y costo al venderse (solo
  Admin).
- **Pago**: método, moneda, monto, equivalente en USD, tasa, referencia y tipo (pago,
  vuelto o devolución por anulación), ligado a una caja.
- **Método de pago**: los seis del PRD con su moneda, si exige referencia y si es
  efectivo.
- **Autorización de descuento**: descuento al que aplica, Admin que autorizó, forma
  (PIN, solicitud, Admin vende) y fecha. En el modelo de datos, autorizaciones y
  solicitudes son una sola tabla (research R8).
- **Solicitud de descuento**: quién la pide, desde qué equipo, detalle, valor pedido y
  aprobado, estado (pendiente, aprobada, rechazada), quién decidió, cuándo y motivo del
  rechazo.
- **Anulación de venta**: venta, motivo, quién y cuándo.
- **Operación de la cola de salida**: identificador único del equipo, tipo, contenido,
  resultado; garantiza que un reenvío no duplique.
- **Alerta**: se amplía con stock negativo, precio distinto, total distinto, tasa
  distinta, descuento para revisión y usuario inactivo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Una venta típica (3 a 5 productos, con un tramo de manguera en cm y pago
  mixto en dos métodos) se registra en menos de 1 minuto.
- **SC-002**: La búsqueda de productos en la pantalla de venta responde en menos de
  1 segundo con 1.000 productos (RNF-04).
- **SC-003**: El 100 % de los casos compartidos de dinero da el mismo resultado en el
  equipo y en el servidor.
- **SC-004**: Reenviar la misma venta 10 veces deja exactamente 1 venta, sus pagos y sus
  movimientos de kardex.
- **SC-005**: Dos equipos que venden a la vez nunca producen el mismo número de venta.
- **SC-006**: Ninguna respuesta del servidor a un Vendedor contiene costos ni márgenes,
  verificado con pruebas por cada endpoint de esta etapa.
- **SC-007**: Cada permiso de la matriz para esta etapa (vender, descontar, anular,
  abrir caja, consultar ventas, registrar equipos) está cubierto por pruebas por rol en
  el servidor.
- **SC-008**: Tras anular una venta, el stock de cada producto vuelve exactamente al
  valor previo a la venta y las devoluciones suman lo cobrado neto del vuelto.
- **SC-009**: Toda venta con stock negativo, descuento sin autorización válida, precio
  distinto, total distinto o tasa distinta genera su alerta (0 casos sin alerta en las pruebas).
- **SC-010**: Ninguna venta, línea, pago ni anulación puede modificarse ni borrarse,
  verificado con cambios directos en la base de datos.
- **SC-011**: Un descuento autorizado por PIN se aplica en menos de 15 segundos desde
  que se pide.

## Assumptions

- Las ventas reales empiezan en la etapa 1.5 (plan de fases §3); en esta etapa la venta
  funciona con conexión, pero ya viaja por la cola de salida para no rehacerla en la
  1.5. La copia local de productos, el funcionamiento sin conexión y el service worker
  son de la 1.5.
- La caja abierta en esta etapa no se cierra hasta la 1.4; en pruebas se puede mantener
  abierta o reiniciar los datos.
- El precio de venta no se modifica en el mostrador (RN-18); las rebajas son descuentos.
- El vuelto puede entregarse en cualquier método y moneda (supuesto 4 del PRD); en esta
  etapa no se valida contra el efectivo disponible en caja (eso es cuadre, 1.4).
- No hay ventas a crédito ni pagos parciales en la Fase 1; el crédito es Fase 2.
- La nota de entrega impresa es Fase 2; en esta etapa la venta se consulta en pantalla.
- Los precios incluyen IVA (RN-17); la venta no desglosa impuestos (Fase 3). El modelo
  conserva el neto por línea para la futura base imponible.
- La serie del equipo se guarda en el navegador del equipo; borrar los datos del
  navegador obliga a registrarlo de nuevo (ADR-0003).
- La solicitud de descuento requiere conexión del vendedor y del Admin.
- Los métodos de pago son fijos en esta etapa (los seis del PRD); el Admin no los edita.
