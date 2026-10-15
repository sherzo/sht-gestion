# Changelog

Cambios por funcionalidad terminada (RNF-09). Formato basado en
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/). Cada etapa terminada de la
Fase 1 cierra una versión: la 1.0 es `0.1.0`, la 1.1 es `0.2.0`, la 1.2 es `0.3.0`, y así sucesivamente.

## [Sin publicar]

### Añadido

- **Etapa 1.3: ventas multimoneda, pagos mixtos, descuentos y apertura de caja** (RF-18,
  RF-20 a RF-30, RN-01 a RN-07, RN-10, RN-11, RN-16; especificación en
  `specs/004-ventas-multimoneda/`):
  - Equipos de mostrador registrados por el Admin desde su navegador, con serie (`A`,
    `B`…) que nunca se reutiliza y token propio; revocación.
  - Apertura de caja con fondo en Bs y USD, una caja abierta por equipo, aviso de tasa
    faltante con la fecha de la última (adelantada de la 1.4).
  - Cálculo de la venta idéntico en el equipo y en el servidor
    (`domain/sale_math.py` y `packages/shared/src/money.ts`) con los mismos casos en
    `packages/shared/test-vectors/money.json`; `pnpm test` en la CI.
  - Cola de salida real en IndexedDB (Dexie) e idempotencia en `POST /sync/operations`:
    reenviar una venta nunca la duplica; las operaciones pendientes o rechazadas se ven
    en la barra de la app.
  - Pantalla Vender: búsqueda con precio en USD y Bs, cantidades en m o cm, totales,
    cliente opcional, pagos mixtos con referencia, vuelto en uno o varios métodos y
    sobrepago, atajos F2 y F9, y tasa verificada al empezar y cada 5 minutos.
  - Descuentos por ítem o total, en monto o porcentaje: el Admin los aplica; el
    Vendedor los autoriza con el PIN del Admin o por solicitud, que el Admin aprueba (tal
    cual o con un valor menor) o rechaza desde Pendientes. Sin autorización válida la
    venta va a revisión con alerta.
  - Venta sin stock, con precio, total o tasa distintos: se registra igual con alerta
    para el Admin; el servidor nunca rechaza una venta por razones de negocio.
  - Anulación completa solo del Admin, con motivo: reversos de kardex y espejo de cada
    pago y vuelto en la caja de la venta.
  - Consulta de ventas: el Admin filtra y ve costo y margen; el Vendedor solo sus ventas
    de hoy, sin costos. El kardex enlaza con la venta.
  - Inmutabilidad en la base (migración `0006`): ventas, líneas, pagos, anulaciones y
    operaciones de la cola son de solo inserción.
  - Pruebas: casos compartidos en Python y TypeScript, 10 envíos simultáneos de la misma
    venta, 2 equipos × 50 ventas en paralelo, venta de 20 líneas en < 1 s, inmutabilidad
    por SQL, matriz de permisos, fuga de costos y auditoría de la etapa.

### Cambiado

- PRD v0.10, antes de especificar la etapa 1.3: con conexión se permite vender sin stock
  suficiente, con advertencia y alerta al admin (RN-10); sin conexión se permiten
  descuentos, con la venta marcada para revisión del admin (RN-07). La apertura de caja
  (RF-29, RF-30, RN-16) se adelanta de la etapa 1.4 a la 1.3 (también en
  `docs/plan-de-fases.md`). Aclaraciones de la 1.3: tasa de cada venta al empezarla
  (RF-18), aprobación de descuentos con un valor menor (RF-22), vuelto menor o igual que
  el excedente con sobrepago (RF-25) y anulación solo completa (RF-27).
- `docs/modelo-de-datos.md` 1.4 (§3.1, §3.6 a §3.8: `discount_authorization` reemplaza a
  `discount_request`, `payment_method` con `code` como clave, `void_change`,
  `outbox_operation` con su respuesta), `docs/arquitectura.md` 1.4 (flujo de venta con la
  cola real), `docs/guia-de-estilos.md` 1.4 (componentes de ventas y caja), ADR-0003
  (preguntas de la 1.3 resueltas) y ADR-0004 (ruta de los casos compartidos y vuelto).
- `GET /exchange-rates/applicable` se abre al Vendedor; `GET /alerts` trae el número de
  la venta; `GET /inventory/summary` suma las solicitudes de descuento pendientes.

## [0.3.0] — 2026-10-15 — Etapa 1.2: proveedores, compras y tasa BCV

Validada en producción: carga de la tasa del día, compra real registrada y confirmada
con su entrada en el kardex y el costo promedio, y respaldo nocturno restaurado en local
junto con las fotos.

### Corregido

- Respaldo diario: la copia de fotos compara tamaño y MD5 (`rclone --checksum`) en
  lugar de la fecha, que Supabase y Cloud Storage guardan con distinta precisión. Desde
  el 2026-10-14 el paso fallaba con `immutable file modified` sobre una foto ya copiada;
  los volcados de la base sí se subieron (RNF-06, ADR-0009).

### Añadido

- **Etapa 1.2: proveedores, compras con gastos y tasa BCV** (RF-13 a RF-17, RN-03,
  RN-05, RN-09, RN-14, RN-15, RN-20; especificación en `specs/003-proveedores-compras/`):
  - Proveedores con RIF normalizado (`J-12345678-9`) y único; se desactivan, nunca se
    borran.
  - Compras en USD o Bs que se guardan en borrador como un documento completo; el
    servidor recalcula totales, gastos, reparto por valor y costo final por unidad
    (`domain/costing.py`, con casos compartidos de prueba).
  - Gastos de la compra (envío, comisión, entrega al local) por porcentaje de la factura
    o monto fijo en USD o Bs, y lista de gastos frecuentes que mantiene el Admin.
  - Confirmación en una sola transacción: entradas en el kardex con costo antes y
    después, costo promedio con el costo final (con stock previo cero o negativo, o sin
    costo, el de la compra), costo inicial bloqueado y número `C-000001` sin huecos.
    Confirmar sobre datos viejos se rechaza (`stale_data`).
  - Compras confirmadas inmutables también en la base (triggers de la migración `0005`);
    se corrigen anulando (solo Admin, con motivo y vista previa): reversos en el kardex,
    costo deshecho con el costo final y alerta en Pendientes si el resultado no es
    válido.
  - Tasa BCV (adelantada de la 1.3): carga y corrección auditada por el Admin, histórico
    y tasa aplicable por fecha; las compras copian la tasa y su fecha.
  - Consulta de compras con filtros (proveedor, fechas, estado, producto, número o
    factura) y enlace desde el kardex a la compra.
  - Pantallas: Compras (lista, borrador y detalle), Proveedores, Tasa BCV, Gastos
    frecuentes (Configuración) y alertas en Pendientes; tarjetas de borradores y alertas
    en el inicio.
  - Pruebas: costo promedio y reparto con casos compartidos, inmutabilidad por SQL
    directo, 20 confirmaciones simultáneas, 200 líneas en menos de 5 s, matriz de
    permisos, fuga de costos y auditoría de las acciones de la etapa.

### Cambiado

- PRD v0.9, para especificar la etapa 1.2 (`specs/003-proveedores-compras/`): si al
  confirmar una compra el stock previo es cero o negativo, o el producto no tiene
  costo, el costo pasa a ser el costo final por unidad de la compra, sin promediar (RN-09); el
  Almacén registra y confirma compras y ve los costos de factura que escribe, pero no
  el costo promedio ni márgenes (matriz de permisos); la carga de la tasa BCV (RF-17,
  RN-15) se adelanta de la etapa 1.3 a la 1.2 (también en `docs/plan-de-fases.md`);
  gastos de las compras (importaciones): por porcentaje de la factura o monto fijo en
  USD o Bs, lista de gastos frecuentes y costo final por unidad repartido por valor,
  que es el que entra al costo promedio (RF-14, RN-20 nueva, §5.4).
- Constitución 1.2.0 (aprobada por el dueño): el principio IV admite que el Almacén
  reciba los costos de factura, los gastos y el costo final de las compras que
  registra, nunca el costo promedio ni márgenes.
- `docs/modelo-de-datos.md` §3.4 (tablas `purchase_charge` y `charge_template`, costo
  final en `purchase_item`, tasa opcional con su fecha en `purchase`; versión 1.3 con
  `voided`, `sequence_counter` y `alert`), `docs/arquitectura.md` 1.3 (compras y tasa),
  `docs/guia-de-estilos.md` 1.3 (componentes de compras), ADR-0004 (redondeo
  de gastos, reparto y costo final) y glosario de `docs/arquitectura.md`.

## [0.2.0] — 2026-10-13 — Etapa 1.1: usuarios, permisos, productos e inventario

Validada en producción: instalación del admin, ingreso (la API responde en ~0,4 s con
la instancia activa), alta de productos con foto subida desde el teléfono, búsqueda y
respaldo nocturno con fotos restaurado en local junto con la base. El código de
instalación (`setup-code`) se reemplazó por un valor aleatorio tras instalar.

### Añadido

- **Etapa 1.1b: productos, categorías e inventario** (RF-01 a RF-12, RN-08, RN-09, RN-13,
  RN-18, RN-19, RNF-04; especificación en `specs/002-productos-inventario/`, ADR-0009):
  - Categorías Mangueras, Conexiones, Ferrules y Ferretería con sus atributos y las
    unidades metro y unidad, instaladas por la migración `0004`; el admin crea y edita
    categorías, atributos (opciones que se agregan o desactivan) y unidades.
  - Productos con SKU automático por categoría que nunca se repite (`MAN-0001`…),
    atributos validados, mangueras siempre por metro, categoría y unidad fijas tras el
    primer movimiento, desactivación sin borrar y avisos de nombre repetido, producto
    inactivo con stock y edición sobre datos viejos.
  - Fotos (hasta 5) normalizadas en el servidor a WebP de 1.200 px sin metadatos,
    guardadas en Supabase Storage con la clave solo en la API.
  - Precio de venta en USD con IVA incluido e historial de solo inserción; costo
    inicial solo del admin mientras no haya compras; publicación en el catálogo solo de
    productos activos con precio. Esquemas de respuesta por rol: el vendedor no recibe
    costos y el almacén tampoco recibe precios (prueba transversal de fuga).
  - Kardex impuesto en la base: el stock solo cambia al insertar un movimiento (trigger
    que verifica el saldo y rechaza escrituras directas); movimientos y precios de solo
    inserción.
  - Ajustes con motivo; las salidas del almacén quedan pendientes hasta que el admin
    las aprueba (revalidando el stock del momento) o rechaza con motivo; el almacén ve
    y puede retirar sus solicitudes. Cada ajuste se audita con el stock antes y después.
  - Conteo físico a ciegas para el almacén (sin stock del sistema ni diferencias), con
    revisión y aplicación solo del admin; un producto en un solo conteo abierto a la vez;
    la diferencia se calcula contra el stock al anotar.
  - Búsqueda sin mayúsculas ni acentos por nombre, descripción, SKU y atributos, con
    filtros; menos de 200 ms en el servidor con 1.000 productos. Stock bajo, pendientes
    del admin y tarjetas del inicio.
  - App interna: productos (lista, alta y ficha con datos, fotos, precio y costo, y
    kardex), ajuste de inventario, pendientes, mis solicitudes, stock bajo, conteos y
    configuración; componentes `DecimalInput`, `StatusChip` y `Tabs`; formato de
    números `1.234,56` en `packages/shared`.
  - Respaldo diario de las fotos con rclone a `fotos/` del bucket de respaldos; comando
    `app.cli seed-demo-products` (solo local).
  - Correcciones de la revisión de código: los valores de atributos desactivados se
    conservan al editar, `0.500` se lee como decimal, las fotos se procesan sin bloquear
    el producto, aplicar un conteo confirma los productos sin contar con el dato del
    servidor, y el costo se muestra sin los ceros que sobran (`100,00`, `7,253333`).
- **Etapa 1.1a: usuarios, autenticación y permisos** (RF-44, RF-45, RF-46, RNF-05,
  RNF-08; especificación en `specs/001-usuarios-autenticacion-permisos/`, ADR-0008):
  - Instalación del primer administrador con código secreto, solo con la base vacía.
  - Inicio de sesión con usuario y contraseña (Argon2id), jornada de 12 horas con token
    de acceso de 15 minutos y token de renovación rotativo en cookie `HttpOnly`; cierre
    de sesión inmediato; bloqueo de 15 minutos tras 5 fallos, por nombre de usuario,
    exista o no.
  - Permisos declarados en cada endpoint y verificados en el servidor contra la base de
    datos en cada petición: desactivar, cambiar el rol o cerrar sesión rige desde la
    siguiente operación. Prueba que impide rutas sin declaración y matriz de permisos
    completa por rol.
  - Gestión de usuarios por el admin: alta con contraseña temporal (se cambia al
    entrar), edición, cambio de rol, desactivación y restablecimiento; siempre queda un
    admin activo. Comando `app.cli reset-password` para recuperar al único admin.
  - PIN del admin (4 a 6 dígitos) con verificación y bloqueo, listo para los descuentos
    de la etapa 1.3.
  - Auditoría de solo inserción (un trigger impide modificarla) en la misma transacción
    que cada acción, sin contraseñas ni PIN, con consulta filtrada por usuario, acción y
    fechas de Caracas.
  - App interna: pantallas de instalación, ingreso, inicio, cambio de contraseña, mi
    cuenta (PIN), usuarios y auditoría; menú por rol; reingreso sin perder lo escrito si
    vence la sesión; componentes base de la guía de estilos e íconos `lucide-react`.
  - Correcciones de la revisión de código: intentos de ingreso en paralelo serializados,
    cada intento bloqueado auditado, la cuenta de fallos vuelve a cero al vencer un bloqueo,
    límite de 5 fallos al comprobar la contraseña actual (cierra la sesión), el admin no se
    restablece su propia contraseña, filtros de auditoría por grupo y aviso cuando la app
    no puede contactar a la API (migración 0003).
  - Tipos de la API generados desde el OpenAPI (`pnpm api:types`) y formato de fechas
    `dd/mm/aaaa hh:mm` en hora de Caracas en `packages/shared`.

### Cambiado

- PRD v0.7: precisiones de RF-44 y RF-45 (jornada de 12 horas, código de instalación,
  un rol por usuario, contraseña temporal).
- PRD v0.8, para especificar la etapa 1.1b (`specs/002-productos-inventario/`): costo
  inicial fijado por el admin mientras el producto no tenga compras confirmadas (RN-09)
  y un solo precio de venta por producto, sin precios de mayorista en la Fase 1
  (RN-18); las salidas de inventario del Almacén necesitan aprobación del admin y los
  conteos los aplica solo el admin (RN-19, matriz de permisos); solo el admin publica
  en el catálogo y el vendedor no ve el kardex (matriz de permisos).
- `docs/arquitectura.md` 1.1, `docs/modelo-de-datos.md` 1.1, `docs/despliegue.md` 0.3 y
  `docs/guia-de-estilos.md` 1.1 actualizados para la etapa 1.1a.
- `docs/arquitectura.md` 1.2, `docs/modelo-de-datos.md` 1.2, `docs/despliegue.md` 0.4 y
  `docs/guia-de-estilos.md` 1.2 actualizados para la etapa 1.1b: búsqueda con texto
  normalizado sin extensiones de Postgres (en lugar de `tsvector` y trigram), tabla
  `adjustment_request`, estados de conteo, flujo y respaldo de fotos.
- Despliegue de la API: secreto `supabase-storage-key` y variables de fotos; la regla de
  borrado a los 30 días del bucket de respaldos se limita a los volcados (`sht-*`).
- Despliegue de la API: secretos `jwt-secret` y `setup-code`, y cookie de sesión
  provisional `SameSite=None` mientras no haya dominio propio.
- Guía de estilos base (`docs/guia-de-estilos.md`, ADR-0007, RNF-02): paleta derivada
  del logo (azul `#03045E` y ámbar `#F7AA00`) con escalas, grises, colores de estado y
  tokens semánticos validados por contraste; tipografía Montserrat + Inter autoalojada;
  solo tema claro.
- Logo en SVG extraído del PDF original (`docs/marca/`): versiones vertical, horizontal,
  negativa, monocromática, isotipo e ícono de la app.
- Tailwind CSS v4 en la app y el catálogo con el tema compartido
  `packages/shared/styles/theme.css`; logo, favicon y color de la barra del navegador en
  ambas páginas mínimas.

## [0.1.0] — 2026-10-07 — Etapa 1.0: arquitectura, modelo de datos y despliegue base

### Añadido

- Producción en marcha: API en https://sht-api-wilmjh5geq-uk.a.run.app (Cloud Run), app
  interna en https://sht-gestion-app.pages.dev y catálogo en
  https://sht-gestion-catalogo.pages.dev (Cloudflare Pages), base de datos en Supabase.
  Respaldo diario cifrado en Cloud Storage y restauración probada en local (RNF-06).
- Monorepo con `backend/` (FastAPI, endpoints de salud, Alembic con los dominios
  decimales de ADR-0004, pruebas, Dockerfile), `frontend/` y `catalog/` (Next.js
  estático) y `packages/shared/`; Postgres local con Docker Compose.
- Workflows de GitHub Actions: CI, despliegue de la API en Cloud Run, despliegue de la
  app y el catálogo en Cloudflare Pages (crea los proyectos si no existen) y respaldo
  diario. Autenticación con Google Cloud sin claves (Workload Identity Federation).
- `docs/despliegue.md`: configuración real de Google Cloud, Supabase, Cloudflare y
  GitHub, particularidades de Windows y procedimiento de restauración.
- `docs/plan-de-fases.md`: alcance, entregables y criterios de terminado por etapa,
  puesta en uso real por partes y preguntas abiertas asignadas a cada etapa.
- `docs/modelo-de-datos.md`: tablas, dominios decimales, inmutabilidad impuesta en la
  base de datos y previsiones para la Fase 2 (crédito) y la Fase 3 (IVA/IGTF).
- `docs/arquitectura.md` y ADRs 0001–0006 en `docs/decisiones/`: stack FastAPI +
  Next.js estático/PWA + Supabase; hosting y presupuesto; ventas sin conexión con
  numeración por equipo; dinero y redondeo; autenticación propia; idioma de
  identificadores.
- Constitución del proyecto (`.specify/memory/constitution.md`): 7 principios, puertas
  del "Constitution Check" y reglas de gobernanza.
- Spec Kit inicializado con integración Claude.
- PRD y `CLAUDE.md` con el contexto del proyecto.

### Cambiado

- PRD v0.4: un solo equipo de mostrador al inicio (§2); presupuesto de infraestructura
  con tope de 35–40 USD/mes (RNF-03); nuevas preguntas abiertas surgidas de la
  arquitectura (§10).
- PRD v0.5: descuentos por ítem o total, en monto o porcentaje (RF-22); compras
  confirmadas inmutables y anulables solo por el admin (RN-14); corrección auditada de
  la tasa (RN-15); una caja por equipo (RN-16); precios con IVA incluido (RN-17).
- PRD v0.6: resumen y objetivos alineados con el presupuesto de RNF-03.
- ADR-0004: reglas de redondeo de descuentos y reparto del descuento total entre ítems.
- Constitución v1.0.0 → v1.1.0: el principio VI pasa a "Simplicidad y costo controlado"
  y remite al presupuesto de RNF-03.
- Arquitectura, modelo de datos y plan de fases pasan de borrador a versión 1.0 vigente.
- `CLAUDE.md` y `README.md` actualizados con el stack, el estado y cómo se trabaja.
