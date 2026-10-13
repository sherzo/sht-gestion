# Feature Specification: Productos, categorías e inventario (etapa 1.1b)

**Feature Branch**: `002-productos-inventario`

**Created**: 2026-10-08

**Status**: Draft

**Input**: User description: "@docs/PRD.md @docs/plan-de-fases.md" — siguiente etapa del plan de fases: 1.1b Productos, categorías e inventario.

**Requisitos del PRD**: RF-01 a RF-12, RN-08, RN-09 (costo inicial), RN-13, RN-18, RN-19 (también RF-46 para la auditoría de precios y ajustes, RNF-02, RNF-04, RNF-05 y RNF-07). Principios de la constitución: I (decimales exactos), II (kardex e inmutabilidad), IV (costos y precios solo para quien corresponde) y V (sin kits).

## Clarifications

### Session 2026-10-08

- Q: ¿Hay precios distintos para mayoristas o talleres frecuentes? → A: No por ahora: un
  solo precio de venta por producto; a mayoristas y talleres se les atiende con
  descuentos autorizados (RF-22). El modelo de datos MUST permitir agregar listas de
  precios más adelante sin rediseño (FR-015).
- Q: ¿Cómo se fija el costo de un producto fuera de las compras? → A: Solo el Admin
  puede escribir un costo inicial, y solo mientras el producto no tenga compras
  confirmadas; desde la primera compra confirmada, el costo solo lo cambian las compras
  con el promedio ponderado (RN-09). Cada definición o cambio del costo inicial queda
  auditado (FR-013).
- Q: ¿Quién puede aplicar un conteo físico y aprobar las salidas de inventario? → A:
  El Almacén abre conteos y anota lo contado, pero solo el Admin aplica un conteo, tras
  revisar sus diferencias. Además, los ajustes manuales negativos del Almacén quedan
  pendientes y no cambian el stock hasta que el Admin los aprueba; los positivos del
  Almacén y todos los del Admin se aplican de inmediato (FR-019, FR-019a, FR-026).
- Q: ¿El Almacén ve el stock del sistema mientras cuenta? → A: No, cuenta a ciegas: la
  pantalla de conteo solo le pide lo contado; el stock del sistema y las diferencias
  solo los ve el Admin, al revisar el conteo (FR-025).
- Q: ¿Quién decide qué productos se publican en el catálogo online? → A: Solo el
  Admin publica y despublica; el Almacén prepara fotos y datos (FR-001, FR-009).
- Q: ¿El Vendedor puede consultar el kardex de un producto? → A: No; solo el Admin y
  el Almacén ven el kardex. El Vendedor ve únicamente el stock actual (FR-022).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registro de productos con SKU automático (Priority: P1)

El Admin o el encargado de Almacén da de alta los productos que vende el negocio:
elige la categoría, escribe nombre y descripción, completa los atributos propios de la
categoría (por ejemplo tipo, diámetro y material de una manguera), indica la unidad y
el stock mínimo. El sistema le asigna un código interno único con el prefijo de la
categoría. El Admin, además, fija el precio de venta. Los productos que dejan de
venderse se desactivan, nunca se borran.

**Why this priority**: sin productos no hay inventario, compras (1.2), ventas (1.3) ni
catálogo (1.6). Es lo primero que el negocio necesita cargar.

**Independent Test**: como Almacén, crear una manguera y una conexión y comprobar que
reciben `MAN-0001` y `CON-0001`, que la manguera queda por metro y que no se pide ni se
muestra el precio de venta.

**Acceptance Scenarios**:

1. **Given** la categoría Mangueras sin productos, **When** el Almacén crea una
   manguera con nombre, descripción, tipo R2, diámetro 1/2" y material, **Then** el
   producto queda con SKU `MAN-0001`, unidad metro, stock 0 y sin precio de venta.
2. **Given** que ya existe `CON-0007`, **When** se crea otra conexión, **Then** recibe
   `CON-0008`, aunque se hayan desactivado productos anteriores; ningún SKU se repite
   ni se reutiliza.
3. **Given** el formulario de un producto de Mangueras, **When** se intenta cambiar la
   unidad a "unidad", **Then** el sistema no lo permite: las mangueras siempre van por
   metro (RF-05).
4. **Given** una categoría con un atributo de opciones (ej. tipo R1/R2/R3), **When** se
   guarda un producto con un valor que no está en la lista, **Then** el sistema lo
   rechaza indicando el atributo.
5. **Given** un producto de Ferretería, **When** se crea solo con nombre y
   descripción, **Then** se guarda sin exigir atributos técnicos.
6. **Given** un usuario de Almacén, **When** crea o edita un producto, aun sin pasar
   por la pantalla, **Then** el servidor no le permite fijar ni cambiar el precio de
   venta ni publicar o despublicar el producto, y ninguna respuesta le muestra precio
   de venta ni costo.
7. **Given** un Vendedor, **When** intenta crear o editar un producto por cualquier
   medio, **Then** el servidor lo rechaza.
8. **Given** un producto activo, **When** el Admin o el Almacén lo desactiva, **Then**
   deja de aparecer en las búsquedas para vender y en el catálogo, conserva su SKU e
   historial, y puede reactivarse.
9. **Given** un producto, **When** se le agregan fotos, **Then** quedan asociadas en el
   orden indicado y la primera es la principal.

---

### User Story 2 - Kardex y ajustes de inventario con motivo (Priority: P1)

Nadie escribe el stock a mano: cada entrada o salida queda como un movimiento con
fecha, tipo, cantidad, usuario, referencia y stock resultante. Cuando hay una
diferencia (mercancía dañada, perdida, un error), el Admin o el Almacén registra un
ajuste positivo o negativo con su motivo. Las salidas que registra el Almacén quedan
pendientes hasta que el Admin las aprueba, para que ninguna falta de mercancía entre al
sistema sin que el dueño la vea. El Admin y el Almacén pueden consultar el historial
de movimientos de un producto.

**Why this priority**: la primera métrica de éxito del PRD es que el stock del sistema
coincida con el conteo físico; eso solo se logra si cada cambio deja rastro (RN-08,
principio II).

**Independent Test**: sobre un producto con stock 10, registrar un ajuste de −2 por
daño y uno de +0,50 m por corrección (en una manguera), y verificar que el stock y el
kardex muestran cada movimiento con su saldo, usuario y motivo.

**Acceptance Scenarios**:

1. **Given** un producto con stock 10 unidades, **When** el Admin registra un ajuste
   de −2 con motivo "daño" y una nota, **Then** el stock queda en 8 y el kardex muestra
   el movimiento con fecha, tipo, cantidad, usuario, motivo, nota y stock resultante 8.
2. **Given** un producto con stock 10, **When** el Almacén registra un ajuste de −2
   por "pérdida", **Then** el ajuste queda pendiente de aprobación, el stock sigue en
   10 y el Admin lo ve en su lista de ajustes por aprobar.
3. **Given** un ajuste pendiente, **When** el Admin lo aprueba, **Then** se genera el
   movimiento con el usuario que lo solicitó y el Admin que lo aprobó, y el stock baja;
   **When** lo rechaza con un motivo, **Then** no se genera movimiento y el Almacén ve
   que fue rechazado y por qué.
4. **Given** un producto con stock 10, **When** el Almacén registra un ajuste de
   +3 por "corrección", **Then** se aplica de inmediato y el stock queda en 13.
5. **Given** el formulario de ajuste, **When** se intenta guardar sin motivo, **Then**
   el sistema lo rechaza (RF-10).
6. **Given** un producto por unidad, **When** se ingresa un ajuste de 1,5, **Then** el
   sistema lo rechaza: las unidades son enteras.
7. **Given** una manguera por metro, **When** se ingresa un ajuste de 0,305 m, **Then**
   el sistema lo rechaza: la precisión máxima es el centímetro (0,30 o 0,31 m).
8. **Given** un producto con stock 3, **When** se registra un ajuste de −5, **Then** el
   sistema lo rechaza porque dejaría el stock negativo; la misma validación se repite
   al aprobar un ajuste pendiente, con el stock de ese momento.
9. **Given** cualquier usuario con la sesión iniciada, **When** intenta cambiar el
   stock de un producto directamente o editar o borrar un movimiento, aun sin pasar por
   la pantalla, **Then** el servidor lo rechaza; la única forma de corregir es un
   movimiento nuevo.
10. **Given** un Vendedor, **When** intenta registrar un ajuste, **Then** el servidor lo
   rechaza; **Given** un Almacén, **When** intenta aprobar o rechazar un ajuste
   pendiente, aun sin pasar por la pantalla, **Then** el servidor lo rechaza; **Given**
   un Vendedor, **When** intenta consultar el kardex de un producto, **Then** el
   servidor lo rechaza (sí ve el stock actual en la búsqueda).
11. **Given** el kardex de un producto, **When** se filtra por rango de fechas o tipo de
   movimiento, **Then** se ven los movimientos más recientes primero, con el stock
   resultante de cada uno.
12. **Given** un ajuste registrado, **When** el Admin consulta la auditoría, **Then**
   aparece con usuario, fecha, producto, cantidad, motivo y stock antes y después.

---

### User Story 3 - Búsqueda rápida y alerta de stock bajo (Priority: P2)

Cualquier usuario encuentra un producto en menos de un segundo escribiendo parte del
nombre, la descripción, el SKU o un atributo (ej. "R2 1/2"), sin preocuparse por
mayúsculas ni acentos. Los productos con stock igual o menor al mínimo se destacan y
pueden listarse para decidir qué comprar.

**Why this priority**: la búsqueda es la base de la pantalla de venta (1.3) y de las
compras (1.2); la alerta de stock bajo evita quedarse sin los productos más vendidos.

**Independent Test**: con 1.000 productos de prueba cargados, buscar por fragmentos de
nombre, SKU y atributos y medir el tiempo; poner un producto en su stock mínimo y
verificar que aparece en la lista de stock bajo.

**Acceptance Scenarios**:

1. **Given** 1.000 productos, **When** se escribe "r2 1/2", **Then** aparecen las
   mangueras R2 de 1/2" en menos de 1 segundo.
2. **Given** un producto "Conexión hembra giratoria", **When** se busca "conexion
   giratoria" (sin acento) o "CON-0012", **Then** el producto aparece.
3. **Given** la búsqueda, **When** se filtra por categoría, por atributo, por estado
   (activo o inactivo) o por "solo stock bajo", **Then** los resultados respetan los
   filtros.
4. **Given** un producto con stock mínimo 5, **When** su stock queda en 5 o menos,
   **Then** se marca como "stock bajo" en las listas y aparece en el listado de stock
   bajo; al subir por encima de 5 deja de aparecer.
5. **Given** un Vendedor, **When** busca productos, **Then** ve nombre, SKU, atributos,
   stock y precio de venta, pero nunca el costo.

---

### User Story 4 - Precio de venta y costo, solo para quien corresponde (Priority: P2)

El Admin fija y cambia el precio de venta en USD (con IVA incluido). Cada cambio queda
en el historial de precios y en la auditoría. El costo del producto solo lo ve el
Admin; en esta etapa queda definido cómo se establece el costo inicial, y desde la
etapa 1.2 lo actualizan las compras con el promedio ponderado.

**Why this priority**: los precios son necesarios para vender (1.3) y para el catálogo
(1.6); la protección de costos y márgenes es un principio no negociable (IV).

**Independent Test**: como Admin, cambiar el precio de un producto dos veces y ver el
historial y la auditoría; como Vendedor y como Almacén, comprobar contra el servidor
que ninguna respuesta incluye el costo y que Almacén tampoco recibe el precio.

**Acceptance Scenarios**:

1. **Given** un producto sin precio, **When** el Admin le fija 12,50 USD, **Then** el
   precio queda vigente desde ese momento, con fecha y usuario en el historial de
   precios y en la auditoría.
2. **Given** un producto con precio 12,50 USD, **When** el Admin lo cambia a 13,00
   USD, **Then** el historial conserva ambos precios con sus fechas y la auditoría
   registra el valor anterior y el nuevo.
3. **Given** un precio con más de 2 decimales o negativo, **When** el Admin intenta
   guardarlo, **Then** el sistema lo rechaza.
4. **Given** un producto sin precio de venta, **When** alguien intenta publicarlo en el
   catálogo, **Then** el sistema no lo permite hasta que tenga precio.
5. **Given** un Vendedor o un Almacén, **When** consulta productos, el kardex (Almacén) o
   cualquier otra función, **Then** ninguna respuesta del servidor incluye costos ni
   márgenes; al Almacén tampoco se le envía el precio de venta.
6. **Given** un producto sin compras confirmadas, **When** el Admin define o corrige
   su costo inicial, **Then** el costo queda guardado y el cambio queda auditado con el
   valor anterior y el nuevo.
7. **Given** un producto con al menos una compra confirmada (desde la etapa 1.2),
   **When** el Admin intenta cambiar su costo a mano, **Then** el sistema lo rechaza:
   desde ese momento el costo solo lo cambian las compras.
8. **Given** un producto sin costo definido, **When** el Admin lo consulta, **Then** ve
   que no tiene costo (y no un costo de cero).

---

### User Story 5 - Conteo físico (Priority: P2)

Para cargar el inventario inicial y para verificar el stock periódicamente, el Admin o
el Almacén abre un conteo (de todo el inventario, de una categoría o de productos
elegidos) y anota lo que cuenta en el estante. Cuando termina, el Admin revisa las
diferencias con el sistema y aplica el conteo: cada diferencia se convierte en un
ajuste con motivo "conteo físico".

**Why this priority**: es la herramienta para cargar el stock inicial antes de la
puesta en uso (plan de fases §3) y para cumplir la métrica de diferencia menor al 2 %.

**Independent Test**: abrir un conteo de la categoría Ferrules, anotar cantidades
distintas al sistema en dos productos e iguales en otro, aplicarlo y comprobar que se
generan exactamente dos ajustes con motivo "conteo físico".

**Acceptance Scenarios**:

1. **Given** un conteo abierto de Ferrules, **When** el Almacén anota las cantidades
   contadas, **Then** la pantalla de conteo solo le muestra los productos y lo que él
   anotó, sin el stock del sistema ni las diferencias, y el servidor no se los envía.
2. **Given** un conteo listo para revisión, **When** el Admin lo abre, **Then** ve para
   cada producto el stock del sistema al anotar, lo contado y la diferencia, y el total
   de productos con diferencia.
3. **Given** un conteo con diferencias, **When** el Admin lo revisa y lo aplica, **Then** cada
   producto con diferencia recibe un ajuste por la diferencia con motivo "conteo
   físico" y referencia al conteo; los productos sin diferencia no generan movimiento;
   el conteo queda cerrado y no se puede modificar.
4. **Given** un conteo abierto, **When** se cancela con un motivo, **Then** no se genera
   ningún movimiento, queda registrado como cancelado con su motivo y sus productos
   pueden entrar en un conteo nuevo.
5. **Given** un conteo abierto, **When** entre que se anotó un producto y se aplicó el
   conteo hubo otro movimiento de ese producto (por ejemplo, una compra), **Then** la
   diferencia aplicada es la calculada al anotar el producto y el otro movimiento se
   conserva.
6. **Given** un conteo abierto con productos sin anotar, **When** se aplica, **Then**
   el sistema advierte cuántos quedan sin contar y esos productos no se ajustan.
7. **Given** un producto que ya está en un conteo abierto, **When** se intenta abrir
   otro conteo que lo incluya, **Then** el sistema no lo permite.
8. **Given** un conteo abierto por el Almacén con todas las cantidades anotadas,
   **When** el Almacén intenta aplicarlo, aun sin pasar por la pantalla, **Then** el
   servidor lo rechaza; el Almacén puede marcarlo como "listo para revisión" y el Admin
   lo ve en su lista de pendientes.

---

### User Story 6 - Categorías, atributos y unidades configurables (Priority: P3)

El Admin ajusta la estructura del inventario sin depender de un programador: renombra
categorías o crea nuevas con su prefijo de SKU, define qué atributos tiene cada
categoría (texto, número u opción de una lista) y cuáles sirven como filtro, y agrega
unidades como caja o paquete.

**Why this priority**: el sistema arranca con las cuatro categorías y unidades del PRD,
así que se puede trabajar sin esto; se vuelve necesario a medida que el negocio crece.

**Independent Test**: como Admin, agregar la opción "R12" al atributo tipo de
Mangueras, crear la unidad "paquete" sin decimales y una categoría nueva con prefijo
`ACE`; crear un producto en ella y verificar que recibe `ACE-0001`.

**Acceptance Scenarios**:

1. **Given** un sistema recién instalado, **When** el Admin abre las categorías,
   **Then** encuentra Mangueras (`MAN`), Conexiones (`CON`), Ferrules (`FER`) y
   Ferretería (`FRT`), con sus atributos iniciales, y las unidades metro y unidad.
2. **Given** el Admin, **When** crea una categoría con un prefijo de 3 letras que ya
   existe, **Then** el sistema lo rechaza.
3. **Given** una categoría con productos, **When** el Admin intenta cambiar su
   prefijo, **Then** el sistema no lo permite; sí puede cambiar el nombre.
4. **Given** un atributo de opciones, **When** el Admin agrega una opción, **Then**
   queda disponible para los productos; **When** desactiva una opción que usan
   productos, **Then** esos productos conservan su valor pero no se puede elegir para
   productos nuevos.
5. **Given** el Admin, **When** crea la unidad "caja" con 0 decimales, **Then** los
   productos en cajas solo aceptan cantidades enteras.
6. **Given** un Vendedor o un Almacén, **When** intenta modificar categorías, atributos
   o unidades, **Then** el servidor lo rechaza.

---

### Edge Cases

- **Dos usuarios crean productos de la misma categoría al mismo tiempo**: cada uno
  recibe un SKU distinto y consecutivo; nunca se repite.
- **Producto creado en la categoría equivocada**: mientras no tenga movimientos, se
  puede cambiar de categoría y recibe un SKU nuevo de esa categoría (el anterior no se
  reutiliza); con movimientos, la categoría ya no cambia y se resuelve desactivándolo y
  creando otro.
- **Cambio de unidad**: solo se permite mientras el producto no tiene movimientos; las
  mangueras nunca cambian de metro.
- **Nombre duplicado**: se permite (dos productos pueden llamarse igual con distinto
  atributo), pero el sistema advierte, al crear o al renombrar, si ya existe otro activo
  con el mismo nombre en la categoría.
- **Edición sobre datos viejos**: si dos personas editan el mismo producto, gana la
  última que guarda; el sistema le advierte que el producto había cambiado desde que lo
  abrió, para que revise.
- **Stock mínimo 0**: el producto se marca como stock bajo solo cuando se agota.
- **Stock negativo existente** (llegará con las ventas sin conexión, RN-10): el
  producto se muestra con su stock negativo y destacado; un ajuste positivo puede
  llevarlo a cero o más.
- **Ajuste que no cambia nada (cantidad 0)**: se rechaza.
- **Stock que baja mientras un ajuste está pendiente**: si al aprobarlo dejaría el
  stock negativo, el Admin no puede aprobarlo tal cual; lo rechaza con motivo y el
  Almacén registra otro con la cantidad correcta.
- **Varios ajustes pendientes del mismo producto**: se permiten; cada uno se decide por
  separado y en cada aprobación se valida con el stock de ese momento.
- **Producto desactivado con stock**: se permite; el sistema advierte que tiene stock y
  sigue apareciendo en el inventario y en los conteos.
- **Foto muy pesada o en formato no admitido**: se rechaza con un mensaje que indica
  el tamaño y los formatos aceptados.
- **Búsqueda sin resultados**: se muestra un mensaje claro; el Almacén y el Admin ven
  la opción de crear el producto.
- **Atributo eliminado de una categoría con productos**: no se elimina, se desactiva;
  los productos conservan el valor histórico.
- **Kit o manguera armada**: no existe como producto (RN-13); el sistema no ofrece
  componer productos.

## Requirements *(mandatory)*

### Functional Requirements

**Productos (RF-01, RF-02, RF-05, RF-07, RN-13)**

- **FR-001**: El Admin y el Almacén MUST poder crear y editar productos con: nombre,
  descripción, categoría, unidad, atributos de su categoría, stock mínimo, fotos,
  y estado activo o inactivo. Solo el Admin MUST poder fijar o cambiar el precio de
  venta y publicar o despublicar el producto en el catálogo.
- **FR-002**: El sistema MUST asignar a cada producto nuevo un SKU único con el formato
  `{prefijo de la categoría}-{correlativo de 4 dígitos}` (ej. `MAN-0001`), consecutivo
  por categoría, que nunca se repite ni se reutiliza, aun con creaciones simultáneas.
  Si una categoría supera 9.999 productos, el correlativo sigue con más dígitos.
- **FR-003**: El SKU MUST NOT poder editarse a mano.
- **FR-004**: Un producto MUST poder cambiar de categoría o de unidad solo mientras no
  tenga movimientos de inventario; al cambiar de categoría recibe un SKU nuevo.
- **FR-005**: Los productos de una categoría con unidad fija (Mangueras) MUST usar
  siempre esa unidad (metro).
- **FR-006**: El sistema MUST validar los atributos contra la definición de la
  categoría: tipo de dato, opciones permitidas y atributos obligatorios.
- **FR-007**: Los productos MUST NOT borrarse; se desactivan y reactivan. Un producto
  inactivo no aparece en la búsqueda para vender ni en el catálogo, pero sí en el
  inventario, el kardex y los conteos.
- **FR-008**: Cada producto MUST admitir hasta 5 fotos (JPG, PNG o WebP, máximo 5 MB
  cada una antes de optimizar) con un orden; la primera es la principal. El sistema
  MUST guardarlas optimizadas para no agotar el almacenamiento (RNF-03).
- **FR-009**: Un producto MUST poder publicarse en el catálogo solo si está activo y
  tiene precio de venta (RF-07), y solo por decisión del Admin; el Almacén prepara
  fotos, descripción y atributos, pero no publica ni despublica. Desactivar un producto
  (Admin o Almacén) lo saca del catálogo. Mostrar el catálogo es de la etapa 1.6.
- **FR-010**: El sistema MUST NOT ofrecer productos compuestos ni kits (RN-13).

**Precios y costos (RF-01, RN-01, RN-17, RF-46, principio IV)**

- **FR-011**: El precio de venta MUST guardarse en USD, con IVA incluido, con 2
  decimales exactos y mayor que cero.
- **FR-012**: Cada fijación o cambio de precio MUST quedar en un historial de precios
  (precio, desde cuándo, quién) que no se edita ni se borra, y en la auditoría con el
  valor anterior y el nuevo.
- **FR-013**: El costo del producto MUST guardarse en USD con precisión exacta
  (RN-01), solo visible para el Admin. Solo el Admin MUST poder definir o corregir a
  mano un costo inicial (mayor o igual a cero), y solo mientras el producto no tenga
  compras confirmadas; desde la primera compra confirmada (etapa 1.2), el costo solo
  cambia por el promedio ponderado de las compras (RN-09). Un producto puede no tener
  costo definido, y eso se distingue de un costo cero.
- **FR-014**: Las respuestas del servidor a Vendedor y Almacén MUST NOT incluir costos
  ni márgenes; las del Almacén MUST NOT incluir el precio de venta. Las pruebas de
  permisos MUST verificarlo en cada función de la etapa.
- **FR-015**: Cada producto MUST tener un único precio de venta; no hay precios por
  tipo de cliente en la Fase 1. El modelo de datos MUST permitir agregar listas de
  precios (ej. mayorista) más adelante sin rediseño.

**Inventario y kardex (RF-08 a RF-11, RN-08)**

- **FR-016**: El stock de un producto MUST cambiar únicamente mediante movimientos de
  inventario; no existe ninguna función que lo escriba directamente.
- **FR-017**: Cada movimiento MUST guardar: fecha y hora, tipo, cantidad con signo,
  usuario, referencia a su origen, stock resultante y, en ajustes, motivo y nota. Los
  movimientos MUST NOT editarse ni borrarse.
- **FR-018**: El sistema MUST admitir los tipos de movimiento entrada por compra,
  salida por venta, reverso por anulación (de venta o de compra) y ajuste positivo o
  negativo (RF-09); en esta etapa solo se generan ajustes (manuales o por conteo), y
  los demás tipos los usan las etapas 1.2 y 1.3.
- **FR-019**: El Admin y el Almacén MUST poder registrar ajustes positivos o negativos
  con motivo obligatorio (conteo físico, daño, pérdida o corrección) y una nota
  opcional (RF-10). Un ajuste manual MUST NOT dejar el stock negativo ni tener
  cantidad cero. Los ajustes del Admin y los positivos del Almacén se aplican de
  inmediato.
- **FR-019a**: Un ajuste negativo registrado por el Almacén MUST quedar pendiente de
  aprobación, sin generar movimiento ni cambiar el stock, hasta que un Admin lo apruebe
  o lo rechace con motivo. Al aprobarlo se genera el movimiento, con quien lo solicitó y
  quien lo aprobó, y se vuelve a validar que no deje el stock negativo con el stock de
  ese momento. Un ajuste pendiente no se edita: el Almacén puede retirarlo y registrar
  otro. Solicitud, aprobación, rechazo y retiro quedan registrados.
- **FR-019b**: El Admin MUST tener una lista de pendientes con los ajustes por aprobar
  y los conteos listos para revisión; el Almacén MUST poder ver el estado de sus
  solicitudes (pendiente, aprobada, rechazada con motivo, retirada).
- **FR-020**: Las cantidades MUST validarse según la unidad: enteras en `unidad` (y en
  las unidades sin decimales), hasta 2 decimales (centímetros) en `metro`, siempre con
  aritmética decimal exacta.
- **FR-021**: Un movimiento y la actualización del stock resultante MUST ocurrir
  juntos: si uno falla, no ocurre ninguno; los movimientos simultáneos sobre un mismo
  producto MUST dar un stock final correcto.
- **FR-022**: El Admin y el Almacén MUST poder consultar el kardex de un producto,
  filtrado por fechas y tipo, con los más recientes primero; al Almacén MUST NOT
  mostrársele costos. El Vendedor MUST NOT acceder al kardex: solo ve el stock actual
  de cada producto.
- **FR-023**: El sistema MUST marcar como "stock bajo" todo producto activo cuyo stock
  sea menor o igual a su stock mínimo, y ofrecer el listado de productos con stock bajo
  al Admin y al Almacén (RF-11).

**Conteo físico (RF-12)**

- **FR-024**: El Admin y el Almacén MUST poder abrir un conteo de todo el inventario,
  de una o varias categorías o de productos elegidos. El conteo de todo o por categoría
  incluye los productos activos y los inactivos con stock distinto de cero (FR-007); en
  los productos elegidos se puede incluir cualquier producto, activo o inactivo. Un
  producto MUST NOT estar en dos conteos abiertos a la vez; al aplicarse o cancelarse
  un conteo, sus productos quedan libres para otro.
- **FR-025**: Al anotar la cantidad contada de un producto, el sistema MUST guardar el
  stock del sistema en ese momento y calcular la diferencia contra él. El conteo MUST
  ser a ciegas para el Almacén: las respuestas del conteo que recibe no incluyen el
  stock del sistema ni las diferencias; solo el Admin los ve, al revisar el conteo.
- **FR-025a**: Solo el Admin MUST poder aplicar un conteo. El Almacén puede abrirlo,
  anotar cantidades, corregir sus anotaciones mientras esté abierto, marcarlo como
  "listo para revisión" y cancelarlo mientras esté abierto. Un conteo listo para
  revisión ya no admite anotaciones y solo lo decide el Admin: lo aplica, lo cancela o
  lo devuelve a abierto para que se vuelva a contar. Cancelar exige un motivo.
- **FR-026**: Al aplicar un conteo, el sistema MUST generar, para cada producto anotado
  con diferencia, un ajuste por esa diferencia con motivo "conteo físico" y referencia
  al conteo, todo junto o nada. Los productos sin anotar no se ajustan y el sistema
  advierte cuántos son antes de aplicar. A diferencia del ajuste manual, el ajuste por
  conteo se aplica aunque el stock resultante quede negativo por salidas posteriores a
  la anotación; el sistema señala esos productos al aplicar.
- **FR-027**: Un conteo aplicado o cancelado MUST NOT modificarse; queda registrado
  quién lo abrió, quién lo aplicó o canceló y cuándo.

**Categorías, atributos y unidades (RF-03, RF-04, RF-05)**

- **FR-028**: El sistema MUST incluir al instalarse las categorías Mangueras (`MAN`,
  unidad fija metro), Conexiones (`CON`), Ferrules (`FER`) y Ferretería (`FRT`), las
  unidades metro (2 decimales) y unidad (0 decimales) y los atributos iniciales:
  Mangueras: tipo (opciones R1, R2, R3…), diámetro y material; Conexiones: tipo,
  rosca, medida y material; Ferrules: tipo y medida; Ferretería: ninguno.
- **FR-029**: Solo el Admin MUST poder crear, renombrar, activar y desactivar
  categorías; el prefijo es de 3 letras mayúsculas, único y no cambia una vez que la
  categoría tiene productos.
- **FR-030**: Solo el Admin MUST poder definir los atributos de cada categoría
  (nombre, tipo texto, número u opción, lista de opciones, si es obligatorio, si sirve
  de filtro, orden) y desactivarlos; desactivar un atributo u opción no altera los
  valores ya guardados en los productos.
- **FR-031**: Solo el Admin MUST poder agregar unidades (nombre, abreviatura y
  decimales permitidos: 0 o 2) y desactivarlas; una unidad en uso no se borra.

**Búsqueda (RF-06, RNF-04)**

- **FR-032**: El sistema MUST buscar productos por nombre, descripción, SKU y valores
  de atributos, sin distinguir mayúsculas ni acentos y aceptando varias palabras en
  cualquier orden.
- **FR-033**: La búsqueda MUST permitir filtrar por categoría, valores de atributos
  filtrables, estado (activo o inactivo), publicación y stock bajo.

**Auditoría (RF-46, RNF-08)**

- **FR-034**: El sistema MUST auditar: fijación y cambio de precio de venta,
  definición o cambio de costo fuera de las compras, ajustes de inventario (manuales y
  por conteo, cada uno con su producto, cantidad y stock antes y después), solicitud, aprobación, rechazo y retiro de ajustes pendientes,
  apertura, aplicación y cancelación de conteos, publicación y despublicación en el
  catálogo, y cambios de categorías,
  atributos y unidades, con valores anteriores y nuevos.

**Pantallas (RNF-02, RNF-07)**

- **FR-035**: La app MUST ofrecer las pantallas de: lista y búsqueda de productos,
  ficha de producto (con fotos, atributos, stock y, según el rol, precio y costo),
  formulario de producto, kardex, ajuste de inventario, pendientes por aprobar (Admin)
  y estado de mis solicitudes (Almacén), stock bajo, conteos físicos y
  configuración de categorías, atributos y unidades, siguiendo
  `docs/guia-de-estilos.md`.
- **FR-036**: Las pantallas MUST poder usarse en teléfono, tablet y PC, en español,
  con números `1.234,56`, fechas `dd/mm/aaaa` y hora de Caracas. Las cantidades en
  metro se muestran con 2 decimales y las enteras sin decimales.

### Key Entities *(include if feature involves data)*

- **Categoría**: agrupa productos (Mangueras, Conexiones, Ferrules, Ferretería y las
  que agregue el Admin). Nombre, prefijo de SKU único, correlativo siguiente, unidad
  sugerida o fija, estado.
- **Definición de atributo**: característica que tienen los productos de una
  categoría (ej. tipo, diámetro, rosca). Etiqueta, tipo de dato, opciones, si es
  obligatoria, si sirve de filtro, orden y estado.
- **Unidad**: cómo se mide un producto (metro, unidad, caja…). Nombre, abreviatura,
  decimales permitidos y estado.
- **Producto**: lo que se compra y se vende individualmente. SKU, categoría, unidad,
  nombre, descripción, valores de atributos, precio de venta vigente, costo, stock
  (resultado del kardex), stock mínimo, fotos, estado y publicación. Nunca se borra.
- **Historial de precios**: cada precio de venta que tuvo un producto, desde cuándo y
  quién lo fijó. Solo se agrega.
- **Foto de producto**: imagen asociada a un producto con su orden.
- **Movimiento de inventario (kardex)**: hecho inmutable que cambia el stock: tipo,
  cantidad con signo, stock resultante, motivo y nota (en ajustes), referencia de
  origen, usuario y fecha.
- **Solicitud de ajuste**: ajuste negativo registrado por el Almacén que espera la
  decisión del Admin. Producto, cantidad, motivo, nota, quién lo solicitó y cuándo,
  estado (pendiente, aprobada, rechazada, retirada), quién decidió, cuándo y motivo del
  rechazo. Al aprobarse genera el movimiento de inventario; mientras está pendiente no
  afecta el stock.
- **Conteo físico**: sesión de conteo con su alcance, estado (abierto, listo para
  revisión, aplicado, cancelado) y quién lo abrió, quién lo marcó listo y quién lo
  aplicó o canceló; sus líneas guardan por producto el stock del sistema al anotar, lo
  contado y la diferencia.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Con 1.000 productos de prueba, el 95 % de las búsquedas muestra
  resultados en menos de 1 segundo (criterio de terminado de la etapa 1.1b).
- **SC-002**: El Almacén registra un producto nuevo con sus atributos en menos de 1
  minuto.
- **SC-003**: El 100 % de los cambios de stock de la etapa tiene su movimiento en el
  kardex, y la suma de los movimientos de cada producto coincide siempre con su stock.
- **SC-004**: El 100 % de las funciones de la etapa tiene pruebas automatizadas con cada
  rol y sin sesión; ninguna respuesta a Vendedor o Almacén contiene costos, y ninguna
  respuesta al Almacén contiene el precio de venta.
- **SC-005**: Un conteo de 100 productos se anota y el Admin lo aplica en una sola
  jornada, y genera exactamente un ajuste por cada producto con diferencia.
- **SC-005a**: Ninguna salida de inventario registrada por el Almacén (ajuste negativo
  o conteo) cambia el stock sin la aprobación de un Admin, verificado con pruebas en el
  servidor.
- **SC-006**: Ningún SKU se repite, incluso con 20 creaciones simultáneas en una misma
  categoría.
- **SC-007**: El 100 % de los cambios de precio y de los ajustes aparece en la
  auditoría con usuario, fecha y valores antes y después.
- **SC-008**: Todas las pantallas de la etapa se usan en un teléfono de 360 px de
  ancho y en PC sin desplazamiento horizontal.

## Assumptions

- **Atributos iniciales y medidas comunes**: el sistema se instala con los atributos de
  FR-028 y listas de opciones editables; las medidas más comunes de mangueras y
  conexiones (pregunta abierta del PRD §10) las carga el Admin como opciones antes de
  la puesta en uso, sin cambios de código. Diámetro y medida se manejan como opciones
  (ej. 1/4", 3/8", 1/2") y no como números, porque así se nombran en el negocio.
- **Ajustes manuales sin stock negativo**: un ajuste manual no puede dejar el stock
  bajo cero; el stock negativo solo puede aparecer por ventas sin conexión (RN-10,
  etapa 1.5).
- **Conteo con movimientos simultáneos**: la diferencia se calcula contra el stock del
  sistema en el momento de anotar cada producto (FR-025), así las compras o ventas que
  ocurran después no se pierden ni se duplican. Se recomienda contar con el local sin
  movimiento, pero no se exige.
- **Inventario inicial**: el stock inicial se carga con un conteo físico (US5) y el
  Admin define el costo inicial de cada producto (FR-013); no hay un tipo de movimiento
  especial de "carga inicial". Al confirmar la primera compra (etapa 1.2), el promedio
  ponderado parte del stock y el costo inicial existentes.
- **Mayoristas y talleres**: se atienden con descuentos autorizados (RF-22, etapa 1.3);
  las listas de precios quedan como posible mejora futura que pasaría primero por el
  PRD.
- **Ingreso en centímetros**: escribir cantidades en cm y convertirlas a metros es
  parte de la pantalla de venta (RF-21, etapa 1.3); en ajustes y conteos se escriben
  metros con hasta 2 decimales.
- **Visibilidad del stock**: todos los roles ven el stock exacto en la app interna; el
  catálogo público (etapa 1.6) solo mostrará "Disponible" o "Agotado".
- **Conteo a ciegas**: oculta el stock solo dentro del conteo; la matriz del PRD
  permite al Almacén ver el stock en la lista de productos, así que es un control
  práctico contra anotar la cifra del sistema por costumbre, no una barrera absoluta.
  La revisión del Admin (RN-19) es el control de fondo.
- **Fotos**: se guardan optimizadas para cuidar el límite gratuito de almacenamiento
  (RNF-03); 5 fotos por producto bastan para el catálogo.
- **Fuera de alcance** (otras etapas): proveedores, compras y costo promedio ponderado
  (1.2); tasa BCV, precio en Bs y ventas (1.3); catálogo público y su regeneración
  (1.6); reportes de valor del inventario y más vendidos (1.7); códigos de barras y
  etiquetas (Fase 2); IVA por producto (Fase 3, el modelo debe permitir agregar la
  alícuota sin rediseño).
- **Dependencias**: etapa 1.1a (usuarios, roles, permisos y auditoría),
  `docs/modelo-de-datos.md` §3.2 y §3.3, ADR-0004 (decimales y redondeo),
  `docs/guia-de-estilos.md` y el almacenamiento de fotos definido en la etapa 1.0.
