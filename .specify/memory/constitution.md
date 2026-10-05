# Constitución de SHT Gestión

Sistema de inventario, compras, ventas multimoneda, caja y catálogo online de
Suministros Hidráulicos Turmero.

## Principios fundamentales

### I. Integridad monetaria multimoneda (NO NEGOCIABLE)

- La moneda base es el **USD**: todo precio y costo se almacena en USD (RN-01).
- La única tasa de conversión es la **BCV**, cargada por el admin con histórico (RN-03,
  RF-17). Si falta la del día, se usa la última disponible y se muestra su fecha (RF-18).
- Bs = USD × tasa BCV, redondeado a 2 decimales (RN-02). El modo de redondeo se define
  una sola vez en `docs/arquitectura.md` y se aplica desde un único punto del código.
- USDT, Zelle y efectivo USD equivalen 1:1 a USD (RN-04). Un pago en Bs cubre en USD
  `monto_bs ÷ tasa de la venta` (RN-06).
- Cada venta, pago y compra guarda la tasa usada en ese momento; los históricos MUST NOT
  recalcularse jamás (RN-05).
- Dinero, tasas y cantidades MUST usar tipos decimales exactos, nunca punto flotante.
  Cantidades en `metro` tienen precisión de centímetro; en `unidad` son enteras (RF-05,
  RF-21). La conversión de cm a m ocurre antes de calcular precio y descontar stock.
- El costo se actualiza con promedio ponderado al confirmar compras (RN-09).

**Razón:** un error de conversión o redondeo se traduce directamente en dinero perdido
y en cajas que no cuadran; en un entorno multimoneda con tasa cambiante, solo la tasa
congelada por operación permite reconstruir cualquier cifra histórica.

### II. Trazabilidad e inmutabilidad

- El stock MUST cambiar únicamente mediante movimientos de kardex: entrada por compra,
  salida por venta, reverso por anulación y ajuste ± con motivo obligatorio (RN-08,
  RF-08 a RF-10). No existe una operación que escriba el stock directamente.
- Los registros cerrados (ventas, cierres de caja) MUST NOT editarse ni borrarse; se
  corrigen con anulaciones o movimientos nuevos (RN-12, RF-33).
- Anular una venta es exclusivo del admin, exige motivo, devuelve el stock y revierte
  la caja (RF-27).
- Las acciones sensibles (cambios de precio, descuentos, anulaciones, ajustes, tasas)
  MUST quedar en el registro de auditoría con usuario y fecha (RF-46, RNF-08).
- Los descuentos del vendedor MUST registrar quién los autorizó (RN-07, RF-22).

**Razón:** la métrica de éxito exige que el stock del sistema coincida con el conteo
físico; eso solo es verificable si cada unidad que entra o sale deja rastro.

### III. Ventas sin conexión (NO NEGOCIABLE)

- El módulo de ventas MUST funcionar sin internet, con productos, precios y la última
  tasa disponibles localmente (RNF-01).
- La sincronización MUST ser idempotente: reintentar el envío de una venta nunca la
  duplica.
- Los correlativos de venta MUST ser únicos entre equipos aunque vendan sin conexión
  al mismo tiempo (RN-11).
- Si al sincronizar una venta el stock queda negativo, la venta se registra igual y se
  genera una alerta para el admin; no se descarta ni se bloquea (RN-10).
- Toda decisión de arquitectura (stack, base de datos, autenticación) MUST demostrar
  que soporta este principio antes de adoptarse.

**Razón:** "ninguna venta perdida por caída de internet" es una métrica de éxito del
PRD; en el contexto del negocio los cortes de conexión son frecuentes.

### IV. Seguridad y permisos en el servidor

- Los permisos por rol (Admin, Vendedor, Almacén) MUST verificarse en el servidor; la
  UI solo oculta, nunca protege (RNF-05). La matriz de permisos del PRD (§4) es la
  referencia.
- El Vendedor y el Almacén MUST NOT recibir costos ni márgenes en ninguna respuesta;
  el Almacén no edita precios de venta.
- El catálogo público MUST NOT exponer costos, cantidades exactas ni datos internos:
  solo "Disponible" o "Agotado" (RF-35).
- Las contraseñas y el PIN de admin se almacenan cifrados con un algoritmo de hash
  adecuado para contraseñas.

**Razón:** costos y márgenes son información comercial sensible y el catálogo es
accesible para cualquiera en internet.

### V. El PRD manda y el alcance va por fases

- `docs/PRD.md` es la fuente de verdad del **qué** y el **por qué**. Un cambio de
  alcance o de regla de negocio MUST hacerse primero en el PRD; no se inventan reglas
  en el código.
- No se implementa nada de Fase 2, Fase 3 ni de "Fuera de alcance" sin solicitud
  explícita.
- El modelo de datos MUST NOT impedir la facturación fiscal futura (IVA por producto,
  IGTF por pago en divisas, Fase 3).
- No existen productos compuestos ni kits: una manguera armada son varios ítems
  individuales en la venta (RN-13).

**Razón:** el negocio está empezando y las reglas aún se validan con el dueño; un único
documento de referencia evita que el código y el negocio diverjan.

### VI. Simplicidad y costo cercano a cero

- La infraestructura MUST operar en planes gratuitos o de muy bajo costo para ~1.000
  productos y pocos usuarios (RNF-03). Todo servicio con costo se justifica en un ADR.
- Se prefiere la solución más simple que cumpla el requisito (YAGNI). Toda complejidad
  adicional (servicios extra, colas, microservicios) se justifica en el plan.
- El catálogo público se regenera periódicamente, no en tiempo real (RF-38).
- La búsqueda de productos responde en menos de 1 segundo y la venta es fluida en
  equipos modestos (RNF-04).

**Razón:** es un negocio pequeño; cada costo fijo y cada pieza extra de infraestructura
pesa más que en una empresa grande.

### VII. Pruebas automatizadas de las reglas críticas

- Las siguientes reglas MUST tener pruebas automatizadas antes de considerarse
  terminadas: conversión y redondeo USD↔Bs, pagos mixtos y vuelto, conversión cm→m y
  validación de unidades, costo promedio ponderado, movimientos de kardex y reversos,
  permisos por rol en el servidor, cuadre de caja y sincronización offline sin
  duplicados.
- Las pruebas referencian el `RF-XX` o `RN-XX` que verifican.
- Un error encontrado en estas reglas se corrige añadiendo primero la prueba que lo
  reproduce.

**Razón:** son las reglas donde un fallo silencioso cuesta dinero o rompe la
confianza en el inventario; las pruebas manuales no escalan con cada cambio.

## Restricciones técnicas y de localización

- **Idioma:** todo en español: UI, documentación, commits y comentarios. Los
  identificadores de código pueden ir en inglés si el stack lo hace más natural; la
  decisión se toma una vez en `docs/arquitectura.md` y se aplica de forma consistente.
- **Localización (RNF-07):** números `1.234,56`, fechas `dd/mm/aaaa`, zona horaria
  `America/Caracas`.
- **Multidispositivo (RNF-02):** interfaz responsive para PC, tablet y teléfono.
- **Respaldos (RNF-06):** respaldo automático diario de la base de datos y exportación
  a CSV o Excel.
- **SKU (RF-02):** generado automáticamente con prefijo por categoría (`MAN-`, `CON-`,
  `FER-`, `FRT-`) y correlativo de 4 dígitos.
- **Pagos (RF-24):** todo método excepto el efectivo exige referencia; el vuelto
  registra método y moneda (RF-25). Una venta requiere caja abierta (RF-30).

## Flujo de trabajo y puertas de calidad

- Cada tarea, commit y documento referencia los `RF-XX` / `RN-XX` / `RNF-XX` que toca.
- Las decisiones técnicas relevantes (stack, base de datos, estrategia offline,
  despliegue, redondeo) se registran como ADR en `docs/decisiones/`.
- Al terminar una funcionalidad se actualizan `docs/` y `CHANGELOG.md` (RNF-09). Una
  funcionalidad sin documentación actualizada no está terminada.
- Se trabaja en ramas por funcionalidad y se integra a `main` mediante revisión.
- **Puertas del "Constitution Check" de cada plan** (todas deben cumplirse o
  justificarse en "Complexity Tracking"):
  1. ¿Montos y cantidades usan decimales exactos y guardan la tasa de la operación? (I)
  2. ¿Todo cambio de stock pasa por kardex y los registros cerrados son inmutables? (II)
  3. ¿La funcionalidad, si toca ventas, funciona sin conexión sin duplicar? (III)
  4. ¿Los permisos se verifican en el servidor y no se filtran costos? (IV)
  5. ¿Está dentro del alcance de la fase actual y respaldada por el PRD? (V)
  6. ¿Se mantiene dentro de costo ~0 sin complejidad injustificada? (VI)
  7. ¿Las reglas críticas que toca tienen pruebas automatizadas? (VII)

## Gobernanza

- Esta constitución prevalece sobre cualquier otra práctica de desarrollo del
  proyecto. En reglas de negocio, `docs/PRD.md` es la fuente de verdad; si el PRD
  cambia una regla reflejada aquí, la constitución se enmienda en el mismo cambio.
- `CLAUDE.md` es la guía operativa para el desarrollo asistido y MUST mantenerse
  coherente con esta constitución.
- **Enmiendas:** se proponen por escrito con su motivo, las aprueba el dueño del
  proyecto y se registran en `CHANGELOG.md`. Si afectan código existente, incluyen un
  plan de migración.
- **Versionado semántico:** MAJOR al eliminar o redefinir un principio de forma
  incompatible; MINOR al añadir un principio o sección, o ampliar materialmente una
  guía; PATCH para aclaraciones y redacción.
- **Cumplimiento:** cada plan pasa el "Constitution Check" y cada revisión de código
  verifica los principios afectados. Las excepciones se justifican por escrito en el
  plan o en un ADR.

**Version**: 1.0.0 | **Ratified**: 2026-10-05 | **Last Amended**: 2026-10-05
