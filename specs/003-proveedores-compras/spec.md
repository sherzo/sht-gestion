# Feature Specification: Proveedores y compras (etapa 1.2)

**Feature Branch**: `003-proveedores-compras`

**Created**: 2026-10-13

**Status**: Draft

**Input**: User description: "Etapa 1.2 — Proveedores y compras (RF-13 a RF-16, RN-05, RN-09, RN-14; PRD v0.9). Proveedores con nombre, RIF, teléfono y notas. Compras con proveedor, fecha, productos, cantidades y costo unitario, en USD o en Bs (si es en Bs se guarda la tasa usada y el equivalente en USD; la tasa queda guardada y nunca se recalcula). Las compras se guardan en borrador y luego se confirman; al confirmar sube el stock mediante movimientos de kardex y se actualiza el costo promedio ponderado del producto (si el stock previo es cero o negativo, el costo pasa a ser el de la compra, sin promediar; la primera compra confirmada bloquea el costo inicial). Las compras confirmadas son inmutables (también en la base de datos); se corrigen anulando (solo admin, con motivo), lo que genera movimientos inversos y recalcula el costo deshaciendo el efecto de la compra; si el resultado no es válido se conserva el costo vigente y se alerta al admin. Roles: Admin y Almacén registran compras; solo el Admin anula; el Vendedor no ve costos."

**Requisitos del PRD**: RF-13 a RF-17, RN-03, RN-05, RN-09, RN-14, RN-15, RN-20 (también RF-08 y RF-09 para el kardex, RF-46 para la auditoría, RNF-02, RNF-05 y RNF-07; supuesto 2 del PRD §9). La carga de la tasa BCV (RF-17, RN-15) se adelanta de la etapa 1.3 a esta. Principios de la constitución: I (decimales exactos y tasa guardada por operación), II (kardex e inmutabilidad), IV (costos solo para quien corresponde) y VII (pruebas del costo promedio y de los reversos).

## Clarifications

### Session 2026-10-13

- Q: Si al confirmar una compra el stock previo es cero o negativo, ¿cuál es el nuevo
  costo? → A: El costo unitario de esa compra, sin promediar (RN-09, PRD v0.9; pregunta
  abierta del plan de fases antes de la 1.2) (FR-011).
- Q: ¿Quién confirma una compra y qué costos ve el Almacén? → A: El Almacén registra y
  confirma compras, y ve los costos de la factura que escribe en ellas; nunca ve el
  costo promedio del producto, el costo antes o después de una compra ni márgenes
  (FR-009, FR-022; matriz de permisos del PRD y principio IV de la constitución
  precisados).
- Q: ¿De dónde sale la tasa de una compra en Bs? → A: Se adelanta a esta etapa la carga
  de la tasa BCV por el Admin, con histórico y corrección auditada (RF-17, RN-15); la
  compra toma la tasa de su fecha o, si no hay, la última anterior, mostrando su fecha
  (FR-012, FR-025 a FR-028).
- Q: Un producto con stock positivo y sin costo, ¿qué costo toma en su primera compra?
  → A: El costo unitario de esa compra, sin promediar, igual que con stock cero o
  negativo (RN-09) (FR-015).
- Q: Las importaciones de China tienen gastos además de la factura (envío cotizado
  por la importadora, a veces comisión de compra del 10 % de la factura, a veces
  entrega al local). ¿Cómo se reflejan en el costo? → A: Como gastos genéricos de la
  compra, cada uno por porcentaje del total de la factura o por monto fijo en USD o
  Bs; el sistema los reparte entre las líneas en proporción a su valor y calcula el
  costo final por unidad, que es el que entra al costo promedio (RN-20, PRD v0.9)
  (User Story 7, FR-029 a FR-033).
- Q: ¿Se agrupan varias facturas en un mismo envío, o llegan gastos después de
  recibir la mercancía? → A: No: cada envío trae una sola factura y todos los gastos
  se conocen al recibirla, así que los gastos se cargan en la misma compra antes de
  confirmarla (FR-029).
- Q: ¿Se guardan gastos frecuentes y quién registra los gastos? → A: Sí, el Admin
  mantiene una lista de gastos frecuentes. El Almacén registra gastos en las compras
  y ve el costo final de cada línea, pero no el costo promedio ni márgenes (FR-032,
  FR-033).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Proveedores (Priority: P1)

El Admin o el encargado de Almacén registra a quién le compra el negocio: nombre, RIF,
teléfono y notas (por ejemplo, días de despacho o el vendedor que lo atiende). Los
proveedores con los que ya no se trabaja se desactivan, nunca se borran, para que sus
compras pasadas sigan mostrando de quién fueron.

**Why this priority**: toda compra se registra contra un proveedor (RF-14); sin
proveedores no hay compras.

**Independent Test**: como Almacén, crear dos proveedores, intentar crear un tercero
con el RIF de uno de ellos y comprobar que se rechaza; desactivar uno y comprobar que
ya no se ofrece al registrar una compra.

**Acceptance Scenarios**:

1. **Given** ningún proveedor registrado, **When** el Almacén crea "Hidráulica Aragua"
   con RIF `J-12345678-9`, teléfono y notas, **Then** el proveedor queda activo y
   disponible para registrar compras.
2. **Given** un proveedor con RIF `J-12345678-9`, **When** alguien intenta crear otro
   con el RIF `j123456789`, **Then** el sistema lo rechaza indicando que ese RIF ya
   pertenece a "Hidráulica Aragua".
3. **Given** un proveedor sin RIF (un vendedor informal), **When** se guarda, **Then**
   se acepta: el RIF es opcional.
4. **Given** un proveedor con compras, **When** el Admin lo desactiva, **Then** deja de
   ofrecerse en compras nuevas, sus compras pasadas lo siguen mostrando y puede
   reactivarse.
5. **Given** un Vendedor con sesión, **When** intenta ver o editar proveedores,
   **Then** el servidor lo rechaza.

---

### User Story 2 - Compra en USD: borrador, confirmación y costo promedio (Priority: P1)

Llega mercancía con su factura. El Almacén abre una compra nueva, elige el proveedor,
la fecha de la factura y la moneda USD, y agrega cada producto con su cantidad y costo
unitario. Puede guardarla como borrador y retomarla (por ejemplo, mientras termina de
revisar la mercancía). Cuando todo coincide con la factura, la confirma: el stock de
cada producto sube con un movimiento de entrada en el kardex y el costo promedio
ponderado se recalcula. Desde ese momento la compra ya no se puede cambiar.

**Why this priority**: es el corazón de la etapa: sin compras confirmadas el stock no
crece de forma trazable y el negocio no conoce su costo real ni sus márgenes (objetivo
4 del PRD). Es además el paso previo a cargar el inventario real (plan de fases §3).

**Independent Test**: con un producto con stock 10 m y costo 2,00 USD, confirmar una
compra en USD de 30 m a 3,00 USD y comprobar que el stock pasa a 40 m, el costo a
2,750000 USD y que el kardex muestra la entrada con la referencia de la compra.

**Acceptance Scenarios**:

1. **Given** un proveedor activo y dos productos, **When** el Almacén crea una compra
   en USD con 30 m de manguera a 3,00 USD y 20 conexiones a 1,25 USD, **Then** el
   sistema muestra el total de cada línea (90,00 y 25,00) y el total de la compra
   (115,00 USD), y la guarda como borrador sin tocar el stock ni el costo.
2. **Given** una compra en borrador, **When** el Almacén cambia una cantidad, quita una
   línea o agrega otra y guarda, **Then** el borrador refleja los cambios y el stock
   sigue sin moverse.
3. **Given** un producto con stock 10 m y costo 2,000000 USD, **When** se confirma una
   compra con 30 m a 3,00 USD, **Then** el stock pasa a 40 m mediante un movimiento
   "entrada por compra" con su referencia, y el costo pasa a
   (10 × 2 + 30 × 3) ÷ 40 = 2,750000 USD; el kardex guarda el costo antes y después.
4. **Given** un producto con stock −2 m (por ventas sin conexión) y costo 10,00 USD,
   **When** se confirma una compra de 5 m a 12,00 USD, **Then** el stock pasa a 3 m y
   el costo pasa a 12,000000 USD, sin promediar (RN-09).
5. **Given** un producto con stock 0 y costo inicial 4,00 USD fijado por el Admin,
   **When** se confirma su primera compra a 5,00 USD, **Then** el costo pasa a
   5,000000 USD y desde entonces el costo inicial ya no se puede editar (RN-09).
6. **Given** una compra confirmada, **When** cualquier usuario, incluido el Admin,
   intenta cambiar o borrar una línea, la fecha, el proveedor o el total, **Then** el
   sistema lo rechaza, también si se intenta directamente en la base de datos (RN-14).
7. **Given** dos compras del mismo producto confirmadas al mismo tiempo por dos
   usuarios, **When** ambas terminan, **Then** el stock y el costo reflejan las dos,
   como si se hubieran confirmado una tras otra.
8. **Given** un borrador que ya no se necesita, **When** quien puede registrar compras
   lo descarta, **Then** desaparece de la lista de borradores sin dejar movimientos.

---

### User Story 3 - Compra en Bs con su tasa (Priority: P2)

Algunos proveedores facturan en bolívares. El Almacén registra la compra en Bs,
escribe el costo unitario en Bs de cada producto tal como aparece en la factura, y el
sistema calcula el equivalente en USD con la tasa de la compra. La tasa queda guardada
en la compra y nunca se recalcula, aunque después se corrija la tasa del día.

**Why this priority**: es frecuente, pero el negocio puede empezar registrando en USD;
depende además de que el Admin haya cargado la tasa BCV (User Story 6).

**Independent Test**: registrar una compra en Bs con tasa 40,00 de 10 unidades a
100,00 Bs y comprobar que el costo unitario queda en 2,500000 USD, que la compra
muestra 1.000,00 Bs y 25,00 USD, y que al confirmarla el promedio usa 2,500000 USD.

**Acceptance Scenarios**:

1. **Given** una compra en Bs con tasa 36,50, **When** se agrega un producto con
   costo unitario 100,00 Bs, **Then** el costo unitario en USD es 100 ÷ 36,50 =
   2,739726 USD (6 decimales, mitad hacia arriba) y la compra muestra el total en Bs y
   en USD.
2. **Given** una compra en Bs confirmada con tasa 36,50, **When** después se corrige o
   cambia la tasa del día, **Then** la compra conserva 36,50 y sus montos en USD no
   cambian (RN-05).
3. **Given** una compra en Bs, **When** se confirma, **Then** el costo promedio de cada
   producto se calcula con su costo unitario en USD, igual que en una compra en USD.
4. **Given** tasas BCV cargadas para el 10/10 (36,20) y el 13/10 (36,50), sin tasa
   del 11/10, **When** se registra una compra en Bs con fecha 11/10, **Then** usa 36,20
   e indica que es la tasa del 10/10.
5. **Given** que no hay ninguna tasa BCV cargada en o antes de la fecha de la compra,
   **When** el Almacén intenta registrar una compra en Bs, **Then** el sistema le
   indica que el Admin debe cargar la tasa primero; las compras en USD no se bloquean.
6. **Given** un borrador en Bs con fecha 13/10, **When** el Admin corrige la tasa del
   13/10 antes de que se confirme, **Then** el borrador muestra la tasa corregida; al
   confirmarse, la tasa queda fija en la compra.

---

### User Story 4 - Anulación de una compra (Priority: P2)

Una compra confirmada tiene un error (otro proveedor, una cantidad o un costo mal
escrito). Solo el Admin puede anularla, y debe escribir el motivo. La anulación saca
del stock lo que la compra había metido, con movimientos inversos en el kardex, y
deshace su efecto en el costo promedio. Luego se registra la compra correcta.

**Why this priority**: las compras confirmadas son inmutables (RN-14); sin anulación no
habría forma de corregir un error, pero se usa poco.

**Independent Test**: confirmar una compra que lleva un producto de 10 m a 2,00 USD a
40 m a 2,75 USD, anularla y comprobar que el stock vuelve a 10 m, el costo a 2,000000
USD y que el kardex muestra el reverso con el motivo.

**Acceptance Scenarios**:

1. **Given** una compra confirmada que llevó un producto de 10 m a 40 m y de 2,00 a
   2,75 USD, sin otros movimientos después, **When** el Admin la anula con motivo
   "costo mal escrito", **Then** el stock vuelve a 10 m con un movimiento "reverso por
   anulación de compra", el costo vuelve a (40 × 2,75 − 30 × 3) ÷ 10 = 2,000000 USD,
   la compra queda marcada como anulada con motivo, usuario y fecha, y la acción queda
   en la auditoría.
2. **Given** una compra cuyo producto ya se vendió en parte, de modo que anularla deja
   el stock en cero o negativo, **When** el Admin la anula, **Then** el sistema le
   advierte antes de confirmar; al anular, el stock queda con el saldo resultante, el
   costo vigente se conserva y se genera una alerta para el Admin (RN-14).
3. **Given** una compra confirmada, **When** el Almacén o el Vendedor intentan
   anularla, **Then** el servidor lo rechaza.
4. **Given** una compra confirmada, **When** el Admin intenta anularla sin motivo,
   **Then** el sistema no lo permite.
5. **Given** una compra ya anulada, **When** alguien intenta anularla de nuevo,
   **Then** el sistema lo rechaza; una compra se anula una sola vez.

---

### User Story 5 - Consulta de compras (Priority: P3)

El Admin y el Almacén consultan las compras: buscan por proveedor, rango de fechas,
estado (borrador, confirmada, anulada) o producto, y abren el detalle de cada una con
sus líneas, la moneda, la tasa, los totales, quién la registró, quién la confirmó y,
si aplica, quién la anuló y por qué.

**Why this priority**: útil para revisar y reclamar a proveedores, pero el negocio
puede operar las primeras semanas solo con el registro.

**Independent Test**: con 3 compras de dos proveedores, filtrar por uno y por un rango
de fechas y comprobar que la lista y los totales coinciden.

**Acceptance Scenarios**:

1. **Given** compras de varios proveedores, **When** el Almacén filtra por un proveedor
   y un rango de fechas, **Then** ve solo esas compras, con número, fecha, proveedor,
   moneda, total y estado.
2. **Given** una compra anulada, **When** se abre su detalle, **Then** muestra el
   motivo, quién la anuló y cuándo, además de sus datos originales.
3. **Given** un producto, **When** el Admin o el Almacén revisan su kardex, **Then**
   cada entrada por compra y cada reverso enlaza con su compra.

---

### User Story 6 - Carga de la tasa BCV (Priority: P2)

Cada día hábil el Admin carga la tasa BCV publicada. El sistema guarda el histórico con
la fecha y quién la cargó. Si se equivocó, el Admin la corrige y la corrección queda
auditada; las compras ya confirmadas conservan la tasa con la que se registraron. En la
etapa 1.3 esta misma tasa se usará en las ventas.

**Why this priority**: es necesaria para las compras en Bs (User Story 3), pero no para
las compras en USD. Se adelanta de la etapa 1.3 para que las compras en Bs usen la tasa
BCV de su fecha (supuesto 2 del PRD).

**Independent Test**: como Admin, cargar la tasa de hoy, corregirla y comprobar que el
histórico muestra el valor vigente, que la auditoría muestra el anterior y el nuevo, y
que el Almacén y el Vendedor no pueden cargarla.

**Acceptance Scenarios**:

1. **Given** que no hay tasa del 13/10, **When** el Admin carga 36,50 para el 13/10,
   **Then** queda en el histórico con fecha, valor, quién la cargó y cuándo.
2. **Given** una tasa del 13/10 ya cargada, **When** el Admin intenta cargar otra para
   la misma fecha, **Then** el sistema le ofrece corregir la existente en lugar de
   duplicarla.
3. **Given** la tasa del 13/10 en 36,50, **When** el Admin la corrige a 36,55,
   **Then** la tasa vigente del 13/10 pasa a 36,55, la auditoría guarda 36,50 → 36,55
   con usuario y fecha, y las compras confirmadas con 36,50 no cambian (RN-15, RN-05).
4. **Given** un Almacén o Vendedor con sesión, **When** intentan cargar o corregir una
   tasa, **Then** el servidor lo rechaza; el Almacén sí ve la tasa que usa cada compra.
5. **Given** el histórico de tasas, **When** el Admin lo consulta, **Then** ve las
   tasas de la más reciente a la más antigua, con su fecha y quién las cargó o
   corrigió.

---

### User Story 7 - Compra importada con gastos (Priority: P2)

Llega una importación de China. El Almacén registra la factura del proveedor chino tal
cual, con el precio de cada producto, y en la sección de gastos agrega lo que costó
traerla: el envío que cotizó la importadora, la comisión de compra si la importadora
compró por el negocio y la entrega al local si la hubo. Elige los gastos de la lista
de gastos frecuentes o los escribe a mano. El sistema reparte el total de gastos entre
los productos en proporción a su valor y muestra el costo final por unidad de cada
línea, que es el que entra al costo promedio. Las compras locales sin gastos no
cambian.

**Why this priority**: sin los gastos, el costo de los productos importados queda por
debajo del real y los márgenes se ven mejores de lo que son. Debe estar antes de
cargar el inventario real (al terminar la 1.2), aunque las compras sin gastos ya
funcionen con la User Story 2.

**Independent Test**: registrar la compra del escenario 1 y comprobar el total de
gastos, el reparto por línea y el costo final; confirmarla y comprobar que el costo
promedio usa el costo final.

**Acceptance Scenarios**:

1. **Given** una compra en USD con dos líneas, 60 unidades a 10,00 USD (600,00 USD) y
   40 unidades a 10,00 USD (400,00 USD), con tasa de su fecha 36,50, **When** se
   agregan una comisión de compra del 10 %, un envío de 250,00 USD y una entrega al
   local de 3.650,00 Bs, **Then** los gastos son 100,00 + 250,00 + 100,00 = 450,00
   USD; la primera línea recibe 270,00 USD y la segunda 180,00 USD (45 % de su valor);
   el costo final por unidad es 10 + 270 ÷ 60 = 14,500000 USD en la primera y 10 +
   180 ÷ 40 = 14,500000 USD en la segunda; la compra muestra 1.000,00 USD de
   mercancía, 450,00 USD de gastos y 1.450,00 USD en total.
2. **Given** el gasto frecuente "Comisión de compra" con 10 % sugerido, **When** el
   Almacén lo elige en una compra, **Then** se agrega con 10 % y puede cambiarlo solo
   en esa compra, sin alterar la lista.
3. **Given** una compra sin gastos, **When** se registra, **Then** el costo final de
   cada línea es igual a su costo unitario en USD y la sección de gastos no estorba.
4. **Given** un producto con stock 0, **When** se confirma la compra del escenario 1,
   **Then** su costo pasa al costo final, 14,500000 USD, no al de factura (RN-20,
   RN-09).
5. **Given** la compra del escenario 1 confirmada, **When** el Admin la anula,
   **Then** el costo se deshace con el costo final de cada línea (FR-018).
6. **Given** una compra confirmada con gastos, **When** alguien intenta cambiar o
   quitar un gasto, **Then** el sistema lo rechaza, también en la base de datos
   (RN-14).
7. **Given** un Vendedor, **When** intenta ver la lista de gastos frecuentes, **Then**
   el servidor lo rechaza; el Almacén la ve y la usa, pero solo el Admin la edita.
8. **Given** tres líneas de 100,00 USD cada una y 100,00 USD de gastos, **When** se
   reparten, **Then** las líneas reciben 33,34, 33,33 y 33,33 USD (con empate, el
   residuo va a la primera línea) y la suma es exactamente 100,00 USD.

---

### Edge Cases

- **Mismo producto dos veces en una compra**: no se permiten dos líneas del mismo
  producto; al agregarlo de nuevo, el sistema lo indica para que se corrija la
  cantidad de la línea existente.
- **Cantidades según la unidad**: en metros, hasta 2 decimales (centímetros); en
  unidades, enteros. Una cantidad con más decimales se rechaza, no se redondea.
  Cantidad y costo deben ser mayores que cero.
- **Costo unitario cero** (mercancía de regalo o de reposición): no se admite en Fase
  1; se registra como ajuste positivo con motivo (RF-10).
- **Producto inactivo**: no se puede agregar a una compra nueva; si se desactiva
  mientras está en un borrador, el borrador no se puede confirmar hasta reactivarlo o
  quitar la línea.
- **Proveedor desactivado con borradores**: los borradores no se pueden confirmar
  hasta reactivarlo o cambiar el proveedor.
- **Fecha de la compra**: no puede ser futura (hora de Caracas); puede ser anterior a
  hoy, porque la factura puede llegar días después de la mercancía. El orden del
  kardex y del costo promedio es el de confirmación, no el de la fecha de la factura.
- **Confirmar dos veces la misma compra** (doble clic o dos personas): la segunda vez
  se rechaza; el stock sube una sola vez.
- **Confirmar un borrador que otro usuario cambió**: si quien confirma lo abrió antes
  del último cambio guardado, el sistema no lo confirma: le avisa que cambió y le
  muestra la versión actual para que la revise y vuelva a confirmar.
- **Compra con muchas líneas** (por ejemplo, la carga del inventario real): se admiten
  al menos 200 líneas por compra.
- **Anular una compra cuando hubo compras posteriores del mismo producto**: el costo
  se recalcula sobre el costo y el stock vigentes al anular, con la fórmula de RN-14;
  no se reprocesan las compras posteriores.
- **Resultado inválido al anular**: si deshacer la compra deja el stock en cero o
  negativo, o daría un costo negativo, se conserva el costo vigente y se crea una
  alerta para el Admin con el producto, la compra y los valores (RN-14).
- **Producto con stock pero sin costo** (por ejemplo, stock cargado con un conteo sin
  costo inicial): su primera compra le fija el costo de esa compra, sin promediar
  (FR-015).
- **Compra en Bs sin tasa disponible**: si no hay ninguna tasa en o antes de su fecha,
  no se puede guardar; si solo hay tasas anteriores, usa la última y muestra su fecha.
- **Cambio de moneda o de fecha en un borrador**: al cambiar la moneda, el sistema
  pide confirmar y vacía los costos unitarios para escribirlos de nuevo en la nueva
  moneda; al cambiar la fecha, la tasa se vuelve a buscar para la nueva fecha.
- **Anular la única compra confirmada de un producto**: el costo inicial sigue
  bloqueado; el costo solo cambia con la próxima compra.
- **Duplicado de factura**: si se registra una compra con el mismo proveedor y número
  de factura que otra no anulada, el sistema advierte, pero permite continuar.
- **Gasto en Bs en una compra en USD** (por ejemplo, la entrega al local): se convierte
  con la tasa de la compra (FR-012); si no hay tasa en o antes de su fecha, la compra
  no se puede guardar con ese gasto.
- **Gasto en USD en una compra en Bs**: se admite; el total en Bs de la compra solo
  cubre la mercancía, y los gastos se muestran en su moneda y en USD.
- **Cambio de líneas con gastos ya cargados**: el reparto y el costo final se
  recalculan cada vez que cambian las líneas o los gastos de un borrador; los gastos
  por porcentaje se recalculan sobre el nuevo total de la factura.
- **Gasto mayor que la factura** (por ejemplo, un envío caro para poca mercancía): se
  admite; el sistema advierte cuando los gastos superan el 100 % de la factura, por si
  es un error de escritura.
- **Gasto frecuente desactivado**: deja de ofrecerse en compras nuevas; las compras que
  lo usaron conservan su copia del gasto.
- **Gasto olvidado tras confirmar**: no se agrega a una compra confirmada; se anula la
  compra y se registra de nuevo con el gasto (RN-14, RN-20).

## Requirements *(mandatory)*

### Functional Requirements

**Proveedores (RF-13)**

- **FR-001**: El Admin y el Almacén MUST poder crear, editar, desactivar y reactivar
  proveedores con: nombre (obligatorio), RIF (opcional), teléfono (opcional) y notas
  (opcional). Los proveedores nunca se borran.
- **FR-002**: El RIF, si se indica, MUST normalizarse a mayúsculas con el formato
  `X-NNNNNNNN-N` (letra J, G, V, E, P o C; de 1 a 8 dígitos de número, rellenados con
  ceros a la izquierda hasta 8; y dígito verificador) y MUST ser único entre todos los
  proveedores, activos o no.
- **FR-003**: Las compras nuevas MUST ofrecer solo proveedores activos; las compras
  existentes conservan su proveedor aunque se desactive.

**Registro de compras (RF-14, RF-15)**

- **FR-004**: El Admin y el Almacén MUST poder crear compras con: proveedor, fecha de
  la factura, moneda (USD o Bs), número de factura del proveedor (opcional), notas
  (opcional), una o más líneas con producto activo, cantidad y costo unitario en la
  moneda de la compra, y cero o más gastos (FR-029).
- **FR-005**: Una compra nueva MUST quedar en estado **borrador**. Mientras está en
  borrador se puede editar por completo y descartar; no afecta stock ni costo.
- **FR-006**: Las cantidades MUST respetar los decimales de la unidad del producto
  (metro: 2; unidad: 0) y ser mayores que cero; los costos unitarios MUST ser mayores
  que cero, en USD con hasta 6 decimales o en Bs con hasta 2. Lo que no cumpla se
  rechaza, no se redondea.
- **FR-007**: El sistema MUST calcular el total de cada línea, el total de mercancía,
  el total de gastos y el total de la compra en la moneda de la compra y en USD, y el
  costo final por unidad de cada línea (FR-031), con los redondeos de ADR-0004 (total
  de línea en USD a 2 decimales; costo unitario en Bs convertido a USD con 6
  decimales, mitad hacia arriba).
- **FR-008**: Cada compra confirmada MUST recibir un número correlativo único con el
  formato `C-000001`, asignado al confirmar, sin saltos entre compras confirmadas.
  Los borradores se identifican por proveedor, fecha y quién los creó.

**Confirmación, stock y costo (RF-16, RN-09)**

- **FR-009**: El Admin y el Almacén MUST poder confirmar compras en borrador, propias
  o de otro usuario. Al registrar y confirmar, el Almacén ve los costos de la factura
  (costo unitario, totales de línea y de la compra), los gastos, el costo final por
  línea y la tasa, pero nunca el costo promedio del producto ni su efecto (FR-022).
- **FR-010**: Al confirmar, el sistema MUST, en una sola operación de todo o nada: (a)
  revalidar que el proveedor y todos los productos están activos y que la compra sigue
  en borrador; (b) asignar el número; (c) generar por cada línea un movimiento de
  kardex "entrada por compra" con la cantidad, la referencia a la línea y el stock
  resultante; (d) recalcular el costo de cada producto según FR-011 y guardar en el
  movimiento el costo antes y después; (e) bloquear el costo inicial del producto
  (RN-09); y (f) registrar quién confirmó y cuándo.
- **FR-011**: El nuevo costo de cada producto MUST calcularse así (RN-09, ADR-0004, 6
  decimales, mitad hacia arriba), con S = stock antes de la entrada, C = costo vigente,
  q = cantidad comprada y c = costo final por unidad de la línea en USD (FR-031; sin
  gastos, es el costo unitario de factura en USD):
  - si S > 0 y el producto tiene costo: (S × C + q × c) ÷ (S + q);
  - si S ≤ 0, o si el producto no tiene costo: c, sin promediar (FR-015).
- **FR-012**: Una compra en Bs MUST usar la tasa BCV cargada para su fecha o, si no
  hay, la última anterior a esa fecha, mostrando de qué fecha es; quien registra no
  puede escribir otra tasa. Si no existe ninguna tasa en o antes de la fecha, la compra
  en Bs no se puede guardar. Mientras es borrador, la compra muestra la tasa vigente
  para su fecha (incluidas correcciones); al confirmarse, la tasa queda fija.
- **FR-013**: Una compra confirmada MUST guardar la tasa usada, la fecha de esa tasa
  y sus montos en Bs y en USD; ningún cambio posterior de tasas la recalcula (RN-05).
  Las compras en USD guardan la tasa de su fecha si existe, solo como referencia; su
  falta no las bloquea.
- **FR-014**: Confirmaciones simultáneas que tocan el mismo producto MUST dar el mismo
  stock y costo que si se hubieran confirmado una tras otra; una compra MUST
  confirmarse una sola vez.
- **FR-015**: Si un producto tiene stock positivo pero ningún costo (por ejemplo,
  stock cargado con un conteo sin costo inicial), al confirmar su primera compra su
  costo MUST pasar a ser el costo final por unidad de esa compra, sin promediar
  (RN-09). La confirmación no se bloquea.

**Inmutabilidad y anulación (RN-14)**

- **FR-016**: Una compra confirmada, sus líneas y sus gastos MUST NOT editarse ni borrarse por
  ninguna vía, incluida la base de datos; los borradores tampoco pueden pasar a
  confirmados fuera del proceso de FR-010.
- **FR-017**: Solo el Admin MUST poder anular una compra confirmada, con un motivo
  obligatorio (mínimo 5 caracteres). Una compra se anula una sola vez y los borradores
  no se anulan (se descartan).
- **FR-018**: Al anular, el sistema MUST, en una sola operación: (a) generar por cada
  línea un movimiento "reverso por anulación de compra" por la cantidad comprada, aunque
  el stock quede en cero o negativo; (b) recalcular el costo de cada producto
  deshaciendo la compra, con S = stock vigente, C = costo vigente y c = costo final
  por unidad de la línea: (S × C − q × c) ÷ (S − q); (c) si S − q ≤ 0 o el resultado es negativo, conservar el
  costo vigente y crear una alerta para el Admin con el producto, la compra, el stock y
  los costos; (d) guardar en cada movimiento el costo antes y después; y (e) registrar
  el motivo, quién anuló y cuándo.
- **FR-019**: Antes de anular, el sistema MUST mostrar al Admin, por producto, el stock
  y el costo resultantes, y advertir cuáles quedarán en cero o negativo o conservarán
  el costo.

**Consulta (RF-08, RF-09)**

- **FR-020**: El Admin y el Almacén MUST poder listar compras con filtros por
  proveedor, rango de fechas, estado (borrador, confirmada, anulada) y producto, y ver
  el detalle de cada una con sus líneas, moneda, tasa, totales, y quién la registró,
  confirmó o anuló.
- **FR-021**: Los movimientos de kardex de compras y anulaciones MUST enlazar con su
  compra.

**Permisos, privacidad y auditoría (RNF-05, RF-46)**

- **FR-022**: Todos los permisos de esta etapa MUST verificarse en el servidor. El
  Vendedor MUST NOT ver proveedores, compras ni tasas. Ninguna respuesta al Vendedor
  o al Almacén MUST incluir el costo promedio del producto, el costo antes o después de
  una compra ni márgenes; el Almacén solo recibe los costos de factura, los gastos y
  el costo final por línea de las compras (FR-009).
- **FR-023**: MUST quedar en la auditoría con usuario y fecha: confirmar una compra,
  anularla (con motivo), cambiar el costo de un producto por una compra o una
  anulación (valor anterior y nuevo), y cargar o corregir una tasa (valor anterior y
  nuevo).
- **FR-024**: Las pantallas de proveedores, compras y tasas MUST usarse en teléfono,
  tablet y PC (RNF-02), con números `1.234,56`, fechas `dd/mm/aaaa` y hora de Caracas
  (RNF-07).

**Tasa BCV (RF-17, RN-03, RN-15; adelantada de la etapa 1.3)**

- **FR-025**: Solo el Admin MUST poder cargar la tasa BCV de una fecha: un valor mayor
  que cero, con hasta 8 decimales, para una fecha que no sea futura (hora de Caracas).
  Hay una sola tasa BCV por fecha; el tipo de tasa queda registrado para admitir otros
  a futuro sin usarlos (RN-03).
- **FR-026**: Solo el Admin MUST poder corregir una tasa ya cargada; la corrección
  reemplaza el valor vigente de esa fecha y queda auditada con el valor anterior y el
  nuevo (RN-15). Las tasas no se borran.
- **FR-027**: El Admin MUST poder consultar el histórico de tasas, de la más reciente a
  la más antigua, con fecha, valor y quién la cargó o corrigió por última vez. El
  Almacén ve solo la tasa que aplica a cada compra.
- **FR-028**: Corregir una tasa MUST NOT alterar ninguna compra confirmada; solo afecta
  a los borradores con esa fecha (FR-012) y a las operaciones futuras.

**Gastos de la compra y costo final (RF-14, RN-20)**

- **FR-029**: Una compra MUST admitir cero o más gastos, cada uno con descripción
  (obligatoria) y uno de dos tipos: **porcentaje** del total de mercancía de la
  factura (mayor que 0 y hasta 100, con hasta 2 decimales) o **monto fijo** en USD o
  Bs (mayor que 0, con 2 decimales). Mientras la compra es borrador, los gastos se
  agregan, cambian y quitan libremente; al confirmarla quedan fijos (FR-016).
- **FR-030**: El monto en USD de cada gasto MUST calcularse así, a 2 decimales con
  mitad hacia arriba: porcentaje × total de mercancía en USD; monto fijo en USD tal
  cual; monto fijo en Bs ÷ tasa de la compra (FR-012). El total de gastos es la suma.
- **FR-031**: El total de gastos MUST repartirse entre las líneas en proporción al
  total en USD de cada una, truncando a 2 decimales; el residuo va a la línea de
  mayor valor (la primera, si hay empate), de modo que la suma de lo repartido sea
  exactamente el total de gastos. El **costo final por unidad** de cada línea es su
  costo unitario en USD + (gasto asignado ÷ cantidad), a 6 decimales con mitad hacia
  arriba. Cada línea guarda su costo de factura, el gasto asignado y el costo final.
  Cada gasto registra su método de reparto (en la Fase 1, siempre por valor) para
  admitir otros métodos más adelante.
- **FR-032**: El Admin MUST poder mantener una lista de **gastos frecuentes** con:
  nombre, tipo (porcentaje o monto fijo), valor sugerido (opcional) y moneda (si es
  monto fijo). Se crean, editan, desactivan y reactivan, nunca se borran. Al
  registrar una compra, el Admin y el Almacén pueden elegir un gasto frecuente activo,
  que se copia a la compra y se puede cambiar ahí sin alterar la lista; editar la
  lista no cambia las compras existentes.
- **FR-033**: El Admin y el Almacén MUST poder registrar gastos en las compras y ver
  el costo final de cada línea. El Almacén ve la lista de gastos frecuentes pero no la
  edita. El Vendedor MUST NOT ver gastos ni la lista de gastos frecuentes.

### Key Entities *(include if feature involves data)*

- **Proveedor**: a quién se le compra. Nombre, RIF único opcional, teléfono, notas y
  estado. Nunca se borra.
- **Compra**: factura de un proveedor registrada en el sistema. Número correlativo (al
  confirmar), proveedor, fecha de la factura, número de factura del proveedor, moneda,
  tasa, total de mercancía, total de gastos y total en USD y en Bs (si aplica), estado
  (borrador, confirmada), quién la creó, quién la confirmó y cuándo, y notas.
  Inmutable una vez confirmada.
- **Línea de compra**: producto, cantidad, costo unitario en la moneda de la compra,
  costo unitario en USD, total de la línea, gasto asignado y costo final por unidad.
  Genera un movimiento de entrada al confirmar.
- **Gasto de la compra**: descripción, tipo (porcentaje o monto fijo), porcentaje o
  monto y moneda, monto en USD, método de reparto (por valor) y, si se eligió de la
  lista, de qué gasto frecuente viene. Inmutable una vez confirmada la compra.
- **Gasto frecuente**: plantilla de un gasto habitual (nombre, tipo, valor sugerido,
  moneda y estado). La mantiene el Admin; nunca se borra.
- **Anulación de compra**: motivo, quién y cuándo. Una por compra; genera los
  movimientos de reverso y, si aplica, alertas de costo.
- **Tasa de cambio**: tasa BCV de una fecha. Tipo (BCV), fecha, valor, quién la cargó
  y cuándo, y última corrección. Una por tipo y fecha; las compras copian su valor.
- **Alerta**: aviso para el Admin cuando una anulación no pudo recalcular el costo
  (RN-14). Producto, compra, valores y si ya se revisó.
- **Movimiento de inventario (kardex)**, de la etapa 1.1b: se agregan las entradas por
  compra y los reversos por anulación, con el costo antes y después.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Las pruebas automatizadas del costo promedio pasan con los casos
  compartidos: stock previo positivo, cero y negativo, producto sin costo, compras en
  USD y en Bs, compras con gastos por porcentaje y fijos en ambas monedas, anulación
  sin movimientos posteriores, anulación con ventas o compras posteriores y anulación
  con resultado inválido (criterio de terminado de la etapa 1.2).
- **SC-002**: Ningún intento de modificar o borrar una compra confirmada, sus líneas o sus gastos
  tiene éxito, ni por la aplicación ni directamente en la base de datos, verificado con
  pruebas (criterio de terminado de la etapa 1.2).
- **SC-003**: El Almacén registra y guarda una compra típica de 10 líneas en menos de
  5 minutos.
- **SC-004**: El 100 % de las entradas y salidas por compras y anulaciones tiene su
  movimiento en el kardex, y la suma de movimientos de cada producto coincide siempre
  con su stock.
- **SC-005**: El 100 % de las funciones de la etapa tiene pruebas con cada rol y sin
  sesión; ninguna respuesta al Vendedor o al Almacén contiene el costo promedio ni
  márgenes.
- **SC-006**: 20 confirmaciones simultáneas de compras del mismo producto dan el mismo
  stock y costo que confirmarlas una por una, y ningún número de compra se repite.
- **SC-007**: El 100 % de las confirmaciones, anulaciones, cambios de costo por compra
  y cargas o correcciones de tasa aparece en la auditoría con usuario, fecha y valores
  antes y después.
- **SC-008**: Todas las pantallas de la etapa se usan en un teléfono de 360 px de ancho
  y en PC sin desplazamiento horizontal.
- **SC-009**: Corregir una tasa no cambia ni un céntimo de ninguna compra confirmada,
  verificado con pruebas (RN-05).
- **SC-010**: En el 100 % de los casos de prueba, la suma de los gastos asignados a las
  líneas es exactamente igual al total de gastos de la compra.
- **SC-011**: Agregar los gastos de una importación (de la lista de gastos frecuentes
  o a mano) toma menos de 1 minuto adicional al registro de la factura.

## Assumptions

- **Compras solo con conexión**: las compras se registran con internet (el número
  `C-000001` lo asigna el servidor, `docs/modelo-de-datos.md` §3.4); el trabajo sin
  conexión es solo para ventas (principio III).
- **Recepción completa**: cada compra se confirma de una vez con todas sus líneas; no
  hay recepciones parciales ni órdenes de compra a proveedores.
- **Costo de la compra**: el costo unitario es el que se pagó al proveedor, con IVA
  incluido si la factura lo trae (los precios del negocio incluyen IVA, RN-17). Los
  fletes, comisiones y otros gastos se registran como gastos de la compra (RN-20).
- **Reparto por valor**: es una simplificación consciente. Los fletes que la
  importadora cobra por peso y volumen quedan repartidos de forma aproximada (los
  productos pesados y baratos, como la manguera, reciben algo menos de lo que les
  tocaría), a cambio de no tener que registrar pesos. El modelo admite agregar otros
  métodos de reparto sin rediseño.
- **Importaciones**: cada envío trae una sola factura y todos sus gastos se conocen al
  recibirla. Los embarques con varias facturas, los gastos posteriores a la
  confirmación y el pago a la importadora quedan fuera de la Fase 1 (PRD §5.4).
- **Número de factura del proveedor**: campo opcional, no exigido por RF-14, que
  sirve para buscar la compra y advertir duplicados.
- **Orden del costo**: el costo promedio se calcula en el orden en que se confirman las
  compras, no por la fecha de la factura; confirmar una compra con fecha anterior no
  reprocesa las posteriores.
- **Precio de venta**: confirmar una compra no cambia el precio de venta; el Admin lo
  ajusta aparte si quiere (RF-07). Mostrar el margen es parte de los reportes (1.7).
- **Pago a proveedores**: no se registra el pago de las compras ni cuentas por pagar;
  la compra no toca la caja (la caja es del mostrador, etapa 1.4).
- **Tasa adelantada**: de la etapa 1.3 se adelanta solo la carga, la corrección y el
  histórico de la tasa (RF-17, RN-15). El aviso de tasa faltante al abrir caja (RF-18),
  los precios en Bs y el uso de la tasa en ventas siguen en la 1.3; la obtención
  automática de la tasa (RF-19) sigue como opcional posterior.
- **Fuera de alcance** (otras etapas): ventas, pagos y tasa en la pantalla de venta
  (1.3); caja (1.4); reportes de compras, valor del inventario y márgenes (1.7);
  importación masiva de compras desde Excel; cuentas por pagar.
- **Dependencias**: etapa 1.1 (usuarios, roles, auditoría, productos, kardex, costo
  inicial y su bloqueo), `docs/modelo-de-datos.md` §3.4 y §3.5, ADR-0004 (decimales y
  redondeo) y la tabla de alertas del modelo de datos.
