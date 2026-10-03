# PRD — Sistema de Inventario, Ventas y Catálogo
## Suministros Hidráulicos Turmero

| Campo | Valor |
|---|---|
| Versión | 0.3 |
| Fecha | 2026-10-03 |
| Estado | En revisión por el dueño |
| Documentos relacionados | `docs/arquitectura.md`, `docs/modelo-de-datos.md`, `docs/plan-de-fases.md`, `CLAUDE.md` |

> Este documento define **qué** se construye y **por qué**. El **cómo** (stack, base de datos, despliegue) va en `docs/arquitectura.md`. Cualquier cambio de alcance o de regla de negocio debe reflejarse aquí y registrarse en `CHANGELOG.md`.

---

## 1. Resumen

Sistema web para gestionar el inventario, las compras, las ventas multimoneda y la caja de un negocio pequeño de mangueras hidráulicas, conexiones, ferrules y ferretería ligera. Incluye un catálogo online público con pedidos por WhatsApp. Debe funcionar en computadora y teléfono, seguir vendiendo cuando se cae el internet y tener un costo de operación cercano a cero.

## 2. Contexto y problema

- El negocio está comenzando y hoy no tiene sistema ni códigos de producto; los productos se identifican por nombre y descripción.
- En Venezuela los precios se manejan en dólares y se cobran en varias monedas y métodos, usando la tasa oficial del BCV para convertir a bolívares.
- Se reciben pagos en bolívares, dólares en efectivo, Zelle y USDT por Binance, con frecuencia combinados en una misma venta.
- Sin un sistema es difícil saber el stock real, cuadrar la caja por método de pago, conocer márgenes y mostrar a los clientes qué hay disponible.

## 3. Objetivos

1. Conocer en todo momento el stock de cada producto y su historial de movimientos.
2. Registrar ventas rápidamente en mostrador, con precios en USD y en Bs, y con pagos mixtos.
3. Cuadrar la caja diaria por método de pago sin cálculos manuales.
4. Registrar compras con proveedor y costo para conocer márgenes.
5. Mostrar un catálogo online actualizado que genere pedidos por WhatsApp.
6. Operar con costo de infraestructura cercano a cero.

### Métricas de éxito (primeros 3 meses de uso)

- Diferencia entre stock del sistema y conteo físico menor al 2 % de las referencias.
- Registrar una venta típica (3 a 5 productos, pago mixto) en menos de 1 minuto.
- Cierre de caja diario completado en menos de 10 minutos.
- Ninguna venta perdida por caída de internet.

## 4. Usuarios y roles

| Rol | Descripción |
|---|---|
| **Administrador** | El dueño. Acceso total: precios, costos, tasas, usuarios, reportes, autorizaciones. |
| **Vendedor** | Atiende el mostrador. Registra ventas, cobra, abre y cierra su caja. |
| **Almacén** | Recibe mercancía, registra compras y entradas, hace ajustes y conteos. |
| **Cliente (público)** | Navega el catálogo online sin iniciar sesión. |

### Matriz de permisos

| Acción | Admin | Vendedor | Almacén |
|---|:-:|:-:|:-:|
| Ver productos y stock | ✅ | ✅ | ✅ |
| Ver costos y márgenes | ✅ | ❌ | ❌ |
| Crear/editar productos | ✅ | ❌ | ✅ (sin precio de venta) |
| Cambiar precio de venta | ✅ | ❌ | ❌ |
| Registrar venta | ✅ | ✅ | ❌ |
| Aplicar descuento | ✅ | Solo con autorización del admin | ❌ |
| Anular venta | ✅ | ❌ | ❌ |
| Abrir/cerrar caja | ✅ | ✅ | ❌ |
| Registrar compras y entradas | ✅ | ❌ | ✅ |
| Ajustes de inventario | ✅ | ❌ | ✅ (con motivo obligatorio) |
| Cargar tasa BCV | ✅ | ❌ | ❌ |
| Gestionar usuarios | ✅ | ❌ | ❌ |
| Ver reportes | ✅ | Solo sus ventas del día | Solo inventario |

## 5. Alcance

El proyecto se divide en tres fases de alcance. La Fase 1 se construye en etapas, detalladas en la sección 11.

### 5.1 Fase 1 (MVP)

1. Productos e inventario
2. Compras a proveedores
3. Tasa de cambio BCV
4. Ventas multimoneda con pagos mixtos
5. Caja (apertura, cierre y cuadre)
6. Catálogo online con pedido por WhatsApp
7. Usuarios, roles y autenticación
8. Reportes básicos
9. Funcionamiento sin internet (offline) en el módulo de ventas

### 5.2 Fase 2

- Crédito a clientes y cuentas por cobrar
- Nota de entrega impresa o enviada al cliente
- Impresión de etiquetas con código de barras

### 5.3 Fase 3

- Facturación fiscal (IVA e IGTF). Desde la Fase 1, el modelo de datos no debe impedir agregarla.

### 5.4 Fuera de alcance

- **Mangueras armadas como producto compuesto o kit.** El negocio gana por cada producto individual: cuando un cliente pide una manguera con sus conexiones y ferrules, el vendedor registra cada componente como un ítem separado de la venta (ver RN-13).
- Múltiples locales o depósitos.
- Carrito de compras y pagos en línea en el catálogo.
- Tasa USDT/Binance como tasa de conversión.

## 6. Requisitos funcionales

Cada requisito tiene un identificador (`RF-XX`) para poder referenciarlo en tareas, commits y documentación.

### 6.1 Productos

- **RF-01** Crear productos con: nombre, descripción, categoría, unidad de medida, precio de venta en USD, costo en USD, stock mínimo, foto(s) y estado activo o inactivo.
- **RF-02** El sistema genera automáticamente un **código interno (SKU)** único por producto, con prefijo según categoría (ej. `MAN-0001`, `CON-0001`, `FER-0001`, `FRT-0001`).
- **RF-03** Categorías iniciales: Mangueras, Conexiones, Ferrules, Ferretería. Editables por el admin.
- **RF-04** Atributos específicos por categoría, por ejemplo para mangueras: tipo (R1/R2/R3…), diámetro y material; para conexiones: tipo, rosca, medida y material (ej. bronce).
- **RF-05** Unidades de medida: **metro** (admite decimales con precisión de centímetro, ej. 1,5 m o 0,30 m) y **unidad** (entero). Lista ampliable por el admin, por ejemplo con caja o paquete. El stock, el precio y el costo de las mangueras se manejan siempre por metro.
- **RF-06** Búsqueda rápida por nombre, descripción, SKU y atributos.
- **RF-07** Marcar si el producto se publica en el catálogo online.

### 6.2 Inventario

- **RF-08** Cada cambio de stock genera un **movimiento** (kardex) con: fecha, tipo, cantidad, usuario, referencia (venta, compra, ajuste) y stock resultante.
- **RF-09** Tipos de movimiento: entrada por compra, salida por venta, reverso por anulación y ajuste positivo o negativo.
- **RF-10** Los ajustes exigen un motivo, por ejemplo: conteo físico, daño, pérdida o corrección.
- **RF-11** Alerta de **stock bajo** cuando el stock es menor o igual al stock mínimo.
- **RF-12** Conteo físico: registrar cantidades contadas y generar los ajustes de diferencia.

### 6.3 Compras

- **RF-13** Registrar proveedores con nombre, RIF, teléfono y notas.
- **RF-14** Registrar compras con: proveedor, fecha, productos, cantidades y costo unitario.
- **RF-15** Las compras pueden registrarse en USD o en Bs. Si son en Bs, se guarda la tasa usada y el equivalente en USD.
- **RF-16** Al confirmar la compra, sube el stock y se actualiza el costo del producto (ver RN-09).

### 6.4 Tasa de cambio

- **RF-17** El admin carga la **tasa BCV del día**. Se guarda el histórico con fecha y usuario.
- **RF-18** Si no hay tasa cargada para el día, el sistema avisa al abrir caja y usa la última disponible, indicando su fecha.
- **RF-19** (Opcional, posterior) Obtener la tasa BCV automáticamente, con la carga manual como respaldo.

### 6.5 Ventas

- **RF-20** Pantalla de venta: buscar productos, agregar cantidades y ver el total en **USD y en Bs** (tasa BCV vigente).
- **RF-21** Validar cantidades según la unidad: decimales para metros y enteros para unidades. En productos por metro, el vendedor puede escribir la cantidad en **metros o en centímetros** (ej. 30 cm); el sistema la convierte a metros (0,30 m), calcula el precio (precio por metro × 0,30) y descuenta 0,30 m del inventario.
- **RF-22** **Descuentos**: el vendedor solo puede aplicarlos con autorización del admin, mediante PIN del admin en el momento o mediante solicitud que el admin aprueba. Queda registrado quién autorizó.
- **RF-23** **Pagos mixtos**: una venta puede pagarse con uno o varios métodos hasta cubrir el total.
- **RF-24** Métodos de pago:

| Método | Moneda | Requiere referencia |
|---|---|:-:|
| Efectivo Bs | VES | ❌ |
| Pago móvil / transferencia | VES | ✅ |
| Punto de venta (tarjeta) | VES | ✅ |
| Efectivo USD | USD | ❌ |
| Zelle | USD | ✅ |
| Binance USDT | USDT (1:1 USD) | ✅ |

- **RF-25** Calcular el **vuelto** cuando el pago excede el total y registrar en qué método y moneda se entregó.
- **RF-26** Cada venta guarda: número correlativo, fecha y hora, vendedor, caja, ítems con precio unitario en USD, tasa BCV usada, descuentos, pagos y vuelto.
- **RF-27** Solo el admin puede anular una venta, con motivo obligatorio. La anulación devuelve el stock y revierte los movimientos de caja.
- **RF-28** Cliente opcional en la venta: nombre, cédula o RIF y teléfono. Será obligatorio para ventas a crédito en la fase 2.

### 6.6 Caja

- **RF-29** **Apertura de caja**: el vendedor indica el fondo inicial por moneda (Bs y USD en efectivo).
- **RF-30** Una venta solo puede registrarse con una caja abierta.
- **RF-31** **Cierre de caja**: el sistema muestra lo esperado por método de pago, el vendedor ingresa lo contado o verificado, y el sistema calcula las diferencias.
- **RF-32** Registrar egresos de caja (gastos menores, retiros) con motivo.
- **RF-33** El cierre queda guardado y no se puede editar; las correcciones se hacen con movimientos nuevos.

### 6.7 Catálogo online

- **RF-34** Página pública, accesible desde el teléfono, con los productos marcados para publicar.
- **RF-35** Muestra: foto, nombre, descripción, atributos, **precio en USD**, **precio en Bs** (última tasa BCV) y **disponibilidad** ("Disponible" o "Agotado"). **No** muestra cantidades exactas ni costos.
- **RF-36** Filtros por categoría y atributos, más búsqueda por texto.
- **RF-37** El cliente agrega productos a una lista y un **botón de WhatsApp** abre un mensaje con el pedido armado (productos, cantidades y total estimado) al número del negocio.
- **RF-38** El catálogo se actualiza periódicamente (cada X horas, configurable), no en tiempo real, para minimizar costos.

### 6.8 Reportes (V1)

- **RF-39** Ventas por día o rango, agrupadas por método de pago y moneda.
- **RF-40** Productos con stock bajo.
- **RF-41** Valor del inventario a costo y a precio de venta, en USD.
- **RF-42** Margen por producto y por período (solo admin).
- **RF-43** Productos más vendidos.

### 6.9 Usuarios

- **RF-44** Inicio de sesión con usuario y contraseña, más un PIN de admin para autorizaciones.
- **RF-45** El admin crea, desactiva y asigna roles a los usuarios.
- **RF-46** Registro de auditoría de acciones sensibles: cambios de precio, descuentos, anulaciones, ajustes y cambios de tasa.

### 6.10 Fase 2 — Crédito y cuentas por cobrar

- **RF-47** Ventas a crédito solo a clientes registrados y habilitados por el admin.
- **RF-48** La deuda se registra en **USD**.
- **RF-49** Los abonos se aceptan en cualquier método; los abonos en Bs se convierten con la tasa BCV del día del abono.
- **RF-50** Estado de cuenta por cliente y reporte de cuentas por cobrar con antigüedad.

### 6.11 Fase 2 — Nota de entrega

- **RF-51** Generar la nota de entrega de cada venta con: datos del negocio, número correlativo, fecha, cliente (si se registró), ítems, precios en USD y Bs, tasa BCV usada, descuentos y pagos.
- **RF-52** Formatos: impresión (formato a definir, ver sección 10) y PDF para enviar al cliente por WhatsApp.
- **RF-53** Reimprimir o reenviar la nota de cualquier venta desde el historial.
- **RF-54** Mientras no exista facturación fiscal, la nota lleva la leyenda "Sin valor fiscal".

### 6.12 Fase 3 — Facturación fiscal

Los requisitos exactos se definirán con el contador según la normativa vigente del SENIAT al momento de implementarla.

- **RF-55** Calcular IVA por producto según su alícuota.
- **RF-56** Calcular IGTF en los pagos en divisas, cuando aplique.
- **RF-57** Emitir la factura por el medio que exija la normativa (máquina fiscal o imprenta digital autorizada).

## 7. Reglas de negocio

| ID | Regla |
|---|---|
| RN-01 | La **moneda base** del sistema es el USD. Todos los precios y costos se almacenan en USD. |
| RN-02 | Precio en Bs = precio en USD × tasa BCV vigente, redondeado a 2 decimales. |
| RN-03 | La única tasa de conversión es la **BCV**. La tabla de tasas admite otros tipos a futuro. |
| RN-04 | **USDT equivale 1:1 a USD.** Zelle y efectivo USD también cuentan como USD. |
| RN-05 | Cada venta, pago y compra guarda la tasa usada en ese momento; los históricos no se recalculan. |
| RN-06 | Un pago en Bs cubre en USD el monto en Bs ÷ tasa BCV de la venta. |
| RN-07 | Los descuentos del vendedor requieren autorización del admin. |
| RN-08 | El stock no se modifica directamente; solo mediante movimientos (RF-08). |
| RN-09 | Supuesto: el costo del producto se actualiza con **costo promedio ponderado** al registrar compras. |
| RN-10 | Las ventas registradas sin internet se sincronizan al volver la conexión. Si una venta deja stock negativo, se registra y se genera una alerta para el admin. |
| RN-11 | Los números correlativos de venta no se repiten aunque haya ventas sin conexión en varios equipos (ver arquitectura). |
| RN-12 | Los registros cerrados (ventas, cierres de caja) no se editan ni se borran; se corrigen con anulaciones o movimientos nuevos. |
| RN-13 | Toda venta se registra **por producto individual**, cada uno con su propio precio y margen. No existen productos compuestos, kits ni cargos de mano de obra: una manguera con sus conexiones y ferrules son varios ítems en la misma venta. |

## 8. Requisitos no funcionales

- **RNF-01 Sin conexión (crítico):** el módulo de ventas debe funcionar sin internet, con productos, precios y la última tasa disponibles localmente, y sincronizar automáticamente al reconectar sin duplicar ventas.
- **RNF-02 Multidispositivo:** interfaz adaptable a computadora, tablet y teléfono.
- **RNF-03 Costo:** infraestructura en planes gratuitos o de muy bajo costo mientras el volumen lo permita (hasta ~1.000 productos y pocos usuarios).
- **RNF-04 Rendimiento:** búsqueda de productos en menos de 1 segundo; registro de venta fluido en equipos modestos.
- **RNF-05 Seguridad:** contraseñas cifradas, permisos verificados en el servidor y no solo en la interfaz, y el catálogo público sin acceso a costos ni a datos internos.
- **RNF-06 Respaldos:** respaldo automático diario de la base de datos y posibilidad de exportar datos (CSV o Excel).
- **RNF-07 Localización:** interfaz en español; formato venezolano de números (`1.234,56`) y fechas (`dd/mm/aaaa`); zona horaria America/Caracas.
- **RNF-08 Auditoría:** las acciones sensibles quedan registradas con usuario y fecha (RF-46).
- **RNF-09 Documentación progresiva:** cada funcionalidad terminada actualiza la documentación en `docs/` y el `CHANGELOG.md`, y las decisiones técnicas se registran en `docs/decisiones/`.

## 9. Supuestos a confirmar

Estas decisiones se tomaron para avanzar. Si alguna no es correcta, se corrige aquí antes de implementar.

1. El costo se calcula con promedio ponderado (RN-09).
2. Las compras en Bs se convierten a USD con la tasa BCV del día de la compra.
3. Los prefijos de SKU por categoría son los de RF-02.
4. El vuelto puede entregarse en cualquier moneda o método disponible en caja.
5. Cada vendedor maneja su propia caja; si hay un solo equipo, la caja es compartida por turno.
6. Un producto con stock mayor que cero se muestra como "Disponible" en el catálogo.
7. Los productos de ferretería no requieren atributos técnicos, solo nombre y descripción.

## 10. Preguntas abiertas

- ¿Número de WhatsApp del negocio para el catálogo?
- ¿Cada cuántas horas debe actualizarse el catálogo (ej. 2, 6 o 12)?
- ¿Existen precios distintos para mayoristas o talleres frecuentes?
- ¿Qué medidas de mangueras y conexiones son las más comunes, para precargar los atributos?
- ¿Habrá un solo equipo de mostrador o varios vendiendo al mismo tiempo?
- Fase 2: ¿la nota de entrega se imprimirá en impresora térmica (ticket) o en hoja carta/media carta?

## 11. Plan de fases (resumen)

El detalle va en `docs/plan-de-fases.md`.

### Fase 1 (MVP), por etapas

| Etapa | Contenido |
|---|---|
| 1.0 | Arquitectura, modelo de datos, `CLAUDE.md`, repositorio y despliegue base |
| 1.1 | Usuarios y roles, productos, categorías, inventario y movimientos |
| 1.2 | Proveedores y compras |
| 1.3 | Tasa BCV, ventas multimoneda, pagos mixtos y descuentos autorizados |
| 1.4 | Caja: apertura, cierre y cuadre |
| 1.5 | Funcionamiento sin conexión y sincronización |
| 1.6 | Catálogo online y pedido por WhatsApp |
| 1.7 | Reportes |

### Fases posteriores

| Fase | Contenido |
|---|---|
| 2 | Crédito y cuentas por cobrar, nota de entrega impresa o en PDF, etiquetas con código de barras |
| 3 | Facturación fiscal (IVA e IGTF) |

## 12. Glosario

- **BCV:** Banco Central de Venezuela; publica la tasa oficial USD/VES.
- **USDT:** stablecoin equivalente a 1 USD, recibida por Binance.
- **SKU:** código interno único de cada producto.
- **Kardex:** historial de movimientos de inventario de un producto.
- **Ferrule:** casquillo que se prensa para fijar la conexión a la manguera.
- **Pago mixto:** venta pagada con más de un método o moneda.
- **Cuadre de caja:** comparación entre lo que el sistema espera y lo contado por método de pago.

---

## Historial de cambios

| Versión | Fecha | Cambio |
|---|---|---|
| 0.1 | 2026-10-03 | Borrador inicial a partir de la entrevista con el dueño |
| 0.2 | 2026-10-03 | Eliminadas las mangueras armadas (se vende por producto individual, RN-13). Nota de entrega pasa a Fase 2 y facturación fiscal a Fase 3. Eliminada la verificación automática de USDT. El plan de construcción de la Fase 1 se organiza en etapas. |
| 0.3 | 2026-10-03 | Precisadas las ventas fraccionadas por metro: precisión de centímetro e ingreso en cm con conversión automática (RF-05, RF-21). |