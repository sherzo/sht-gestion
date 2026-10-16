# ADR-0003: Ventas sin conexión, sincronización y numeración por equipo

- **Estado:** Aceptada
- **Fecha:** 2026-10-05
- **Requisitos relacionados:** RNF-01, RN-05, RN-10, RN-11, RF-18, RF-26, RF-30; principio III

## Contexto

El módulo de ventas debe funcionar sin internet y sincronizar sin duplicar ventas
(RNF-01). Los números de venta no pueden repetirse aunque haya ventas sin conexión en
varios equipos (RN-11). Al inicio habrá un solo equipo de mostrador y más adelante podría
agregarse un segundo (PRD §2). Una venta requiere caja abierta (RF-30), así que la caja
también debe poder operarse sin conexión.

## Decisión

### Alcance sin conexión

- **Funciona sin conexión:** búsqueda de productos, registro de ventas, apertura de
  caja, egresos y cierre de caja del propio equipo.
- **Requiere conexión:** todo lo demás (productos, precios, compras, ajustes, tasa BCV,
  anulaciones, usuarios, reportes).

### Datos locales (IndexedDB, mediante Dexie)

- Copia de los productos activos: nombre, SKU, atributos, unidad, precio de venta y
  stock aproximado. Nunca costos (principio IV).
- La última tasa BCV, con su fecha (RF-18).
- La identidad del equipo y su serie de numeración.
- La sesión del usuario (ADR-0005).
- La **cola de salida**: las operaciones pendientes de enviar al servidor.

La copia local se refresca al iniciar la app y periódicamente mientras haya conexión.
La app solicita almacenamiento persistente (`navigator.storage.persist()`) para que el
navegador no borre los datos locales por falta de espacio.

### Cola de salida e idempotencia

- Toda operación hecha en el mostrador (abrir caja, venta, egreso, cerrar caja) se guarda
  primero en la cola local y después se envía, haya o no conexión. Así hay un solo
  camino de código, no uno en línea y otro sin conexión.
- Cada operación lleva un identificador UUIDv7 generado en el equipo. El servidor lo
  usa como clave de idempotencia: si recibe de nuevo una operación ya procesada,
  devuelve el resultado original sin volver a aplicarla. Así un reintento nunca duplica
  una venta.
- Las operaciones se envían en orden. Se reintentan al recuperar la conexión, al abrir
  la app y periódicamente con espera creciente. No se depende de la Background Sync
  API, que no está disponible en todos los navegadores.
- El servidor es la autoridad: recalcula cada venta (ADR-0004) y aplica los movimientos
  de kardex y de caja en una sola transacción.

### Numeración por equipo (RN-11)

- El admin registra cada equipo una vez, con conexión. El servidor le asigna una
  **serie** única (`A`, `B`, …).
- El número de venta es `{serie}-{correlativo de 6 dígitos}`, por ejemplo `A-000123`. El
  equipo lleva su propio contador y numera sin conexión.
- La base de datos garantiza la unicidad de `(serie, correlativo)`.
- **Una serie nunca se reutiliza.** Si un equipo pierde sus datos locales o se
  reemplaza, se registra de nuevo y recibe una serie nueva. Así no puede chocar con
  números emitidos antes y aún no sincronizados.
- Este número es interno y no tiene valor fiscal. En la Fase 3, el número de factura lo
  asignará el medio fiscal y será independiente de este.

### Reglas al sincronizar

- **Stock:** una venta sin conexión no se bloquea por stock. Si al aplicarla el stock
  queda negativo, se registra igual y se genera una alerta para el admin (RN-10).
- **Tasa:** la venta guarda la tasa con la que se hizo en el equipo, aunque al
  sincronizar exista una más reciente (RN-05, RF-18).
- **Precio:** la venta guarda el precio unitario con el que se vendió. Si no coincide
  con el precio vigente en el servidor cuando el equipo actualizó su copia local, la
  venta se registra igual y se genera una alerta para el admin.
- **Diferencias de cálculo:** si el total recalculado por el servidor difiere del
  calculado en el equipo, prevalece el del servidor, se conserva el del equipo y se
  genera una alerta.

### Actualizaciones de la app

- El service worker nuevo **no** se activa por su cuenta en medio de una venta. La app
  avisa que hay una versión nueva y se actualiza cuando el usuario acepta y no hay
  ventas en curso.
- Una versión no se publica en producción hasta haberse probado en el equipo real
  (ambiente de pruebas, ADR-0002), una vez que el negocio use el sistema con datos
  reales.

### Resuelto en la etapa 1.3 (PRD v0.10)

- **Descuentos sin conexión:** se permiten; como el PIN no puede validarse en el equipo,
  la venta queda marcada para revisión del Admin (`needs_review`) con una alerta
  `discount_review` (RN-07). Con conexión, el descuento del Vendedor se autoriza antes de
  confirmar: PIN validado en el servidor o solicitud aprobada, atada a la venta, la línea,
  el valor y la base (`discount_authorization`).
- **Venta sin stock con conexión:** se advierte y se permite; si el stock queda negativo,
  alerta para el Admin (RN-10).
- **Implementación** (specs/004-ventas-multimoneda, research R3 a R5): el equipo se
  identifica con un token propio en `X-Device-Token`; la cola usa Dexie y envía una
  operación por petición a `POST /sync/operations`; el servidor bloquea el id de la
  operación y guarda su respuesta, también la de un rechazo estructural o de datos fuera
  de límites, para repetirla en un reenvío (rearmada con el esquema del rol de quien la
  reenvía). Un equipo revocado nunca abre caja; sus ventas creadas antes de la revocación
  en una caja abierta antes de ella se aceptan con una alerta `revoked_device_sync`. En la
  1.3 la venta queda a nombre del usuario de la sesión que la envía; la cola del equipo
  solo envía las ventas del usuario con sesión y deja las demás esperando a su vendedor.
  La 1.5 define el caso de ventas sin conexión de un vendedor que no vuelve a ingresar.

### Resuelto en la etapa 1.4 (PRD v0.11 y v0.12)

- La cola suma los tipos `cash_outflow.create` (egreso) y `cash_session.close` (cierre
  desde el equipo de la caja), con la misma idempotencia. Como la venta, quedan a nombre
  del usuario de la sesión y la cola del equipo los deja esperando a su dueño. El equipo
  no cierra mientras tenga operaciones de esa caja pendientes o rechazadas sin descartar.
- El cierre envía el esperado que vio el equipo; el servidor recalcula y, si difiere,
  guarda el suyo, conserva el del equipo y crea la alerta `expected_mismatch`, sin
  rechazar el cierre.
- Una caja huérfana la cierra el Admin con conexión (fuera de la cola). Una venta o un
  egreso creados en el equipo antes de ese cierre (`created_at` u `occurred_at` <
  `closed_at`) se registran en su caja con la alerta `post_close_operation`; los creados
  después se rechazan con `cash_session_closed`. Lo que llegó después del cierre se
  marca comparando horas del servidor (`closed_recorded_at`), nunca la del equipo.
- Al anular una venta de una caja ya cerrada, el dinero se revierte en la caja abierta
  del equipo desde el que anula el Admin y el cierre anterior no cambia (RF-27). En la
  1.3 la devolución iba siempre a la caja de la venta.

## Alternativas consideradas

- **Motores de sincronización** (PowerSync, ElectricSQL, RxDB, Replicache): resuelven la
  réplica bidireccional completa, que aquí no hace falta (solo se envían operaciones del
  mostrador) y añaden una dependencia y, en algunos casos, costo.
- **Número provisional sin conexión y definitivo al sincronizar:** confunde al cliente,
  que ya recibió un número.
- **Bloques de correlativos reservados por equipo** (numeración global): exige conexión
  para pedir bloques y deja huecos; no aporta valor sin facturación fiscal.

## Consecuencias

- El mostrador nunca deja de vender por falta de internet.
- No hay una numeración única para todo el negocio, sino una por serie.
- Si se borran los datos del navegador con operaciones aún sin enviar, esas operaciones
  se pierden. Se mitiga con almacenamiento persistente, envío inmediato cuando hay
  conexión, un indicador visible de operaciones pendientes y un aviso antes de cerrar
  sesión si hay pendientes.
- El servidor debe procesar operaciones atrasadas, por ejemplo ventas de hace horas con
  la tasa de ayer, sin rechazarlas.
