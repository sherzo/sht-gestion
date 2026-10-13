# Investigación (fase 0): productos, categorías e inventario

Decisiones técnicas que resuelven lo que la especificación deja abierto. Parten de
`docs/modelo-de-datos.md` §3.2–3.3, ADR-0002 (fotos y presupuesto), ADR-0004 (decimales),
ADR-0008 (permisos por petición) y el código de la etapa 1.1a.

## R1. SKU automático sin repetidos (FR-002, FR-003, FR-004, SC-006)

- **Decisión:** `category.next_sku_number` se lee con `SELECT … FOR UPDATE` dentro de la
  transacción que crea el producto, se incrementa y se forma
  `{sku_prefix}-{número con al menos 4 dígitos}` (`MAN-0001`, … `MAN-9999`,
  `MAN-10000`). `product.sku` tiene restricción `UNIQUE` como red de seguridad. Al cambiar
  de categoría (solo sin movimientos) se toma un número nuevo de la categoría destino; el
  número anterior no se devuelve. El SKU no figura en ningún esquema de entrada.
- **Razón:** el bloqueo de fila serializa solo las altas de una misma categoría; con
  pocos usuarios no hay contención. Funciona con el pooler de transacciones de Supabase
  porque todo ocurre dentro de una transacción.
- **Alternativas:** secuencias de Postgres por categoría (hay que crearlas al crear
  categorías y no se pueden desplegar con privilegios mínimos); `MAX(sku)+1` (repite
  números con altas simultáneas).

## R2. El stock solo cambia por movimientos, impuesto en la base (FR-016, FR-017, FR-021)

- **Decisión:** dos defensas.
  1. **Servicio único:** `services/inventory.py::post_movement` bloquea el producto
     (`FOR UPDATE`), calcula `balance_after = stock + quantity_delta`, inserta el
     `stock_movement` y actualiza `product.stock`, en la misma transacción que la
     auditoría. Las etapas 1.2 y 1.3 usarán la misma función.
  2. **Triggers:** `stock_movement` rechaza `UPDATE` y `DELETE`; un trigger `BEFORE
     INSERT` verifica que `balance_after` sea igual al stock vigente más el delta y
     actualiza `product.stock`; un trigger `BEFORE UPDATE` en `product` rechaza cualquier
     cambio de `stock` que no venga de ese trigger (`pg_trigger_depth() > 1`).
- **Razón:** la constitución (principio II, modelo de datos §1.4) exige imponer la regla
  en la base, no solo en el código. Con el trigger, ni un error de programación ni una
  consulta manual con el rol de la API pueden escribir el stock directamente. El rol
  `sht_api` ya no tiene `DELETE` en ninguna tabla (`docs/despliegue.md`).
- **Alternativas:** stock calculado como suma del kardex en cada lectura (lento para
  buscar y listar, y la arquitectura ya fija la copia en `product.stock`); solo la regla
  en el servicio (no cumple la puerta 2 de la constitución).

## R3. Validación de cantidades por unidad (FR-020, ADR-0004)

- **Decisión:** `domain/units.py::validate_quantity(value, decimals, allow_zero,
  allow_negative)` sobre `Decimal`: rechaza más decimales de los permitidos por la unidad
  (`unit.decimals`: 0 o 2), sin redondear. Las cantidades viajan como cadenas en JSON
  (`"0.30"`), como fija ADR-0004. El ingreso en centímetros es de la etapa 1.3.
- **Razón:** un único punto de validación, probado sin base de datos (principio VII).
- **Alternativas:** validar con `NUMERIC(14,2)` en la base (redondearía en silencio un
  `0,305`).

## R4. Búsqueda en menos de 1 segundo (FR-032, FR-033, SC-001)

- **Decisión:** columna `product.search_text text` con nombre, descripción, SKU y
  valores de atributos **normalizados** (minúsculas, sin acentos con `unicodedata`,
  espacios simples), que calcula el backend en `domain/search.py` al crear o editar.
  La consulta normaliza el texto igual, lo divide en palabras y exige que cada palabra
  aparezca (`search_text LIKE '%palabra%'` por cada una, en cualquier orden), combinada
  con los filtros; orden por coincidencia exacta de SKU primero y luego por nombre;
  paginación de 50.
- **Razón:** con ~1.000 productos, un recorrido secuencial con `LIKE` tarda pocos
  milisegundos en Postgres; el tiempo lo domina la red (SC-001 se mide con 1.000
  productos de prueba). No requiere extensiones: `unaccent` no es `IMMUTABLE` (no sirve
  en columnas generadas) y `pg_trgm` en Supabase vive en el esquema `extensions`, lo que
  complica las migraciones y el entorno local. Un `tsvector` con diccionario español
  corta mal medidas como `1/2"` y códigos como `CON-0012`.
- **Ruta de crecimiento:** si el catálogo supera ~10.000 productos, se agrega un índice
  `pg_trgm` sobre `search_text` sin cambiar la API. La búsqueda del mostrador sin
  conexión (etapa 1.5) usará la copia local y la misma normalización en TypeScript.
- **Alternativas:** `tsvector` generado (descartado por lo anterior); servicio de
  búsqueda externo (viola RNF-03 y el principio VI).
- **Cambio de documentación:** `docs/modelo-de-datos.md` §3.2 y §4 pasan de "tsvector +
  trigram" a esta columna normalizada.

## R5. Atributos por categoría (FR-006, FR-028, FR-030)

- **Decisión:** `attribute_definition` con `key`, `label`, `data_type` (`text`,
  `number`, `option`), `options` jsonb como lista de `{"value": "R2", "is_active":
  true}`, `is_required`, `is_filterable`, `sort_order`, `is_active`. El producto guarda
  `attributes` jsonb `{key: valor}`; `domain/attributes.py` valida contra las
  definiciones activas: obligatorios presentes, número decimal válido, opción existente
  y activa (al crear o al cambiar ese atributo; un valor ya guardado de una opción
  desactivada se conserva). Las claves desconocidas se rechazan.
- **Atributos iniciales (FR-028, cierra un pendiente de la aclaración):**

  | Categoría | Atributos (obligatorios en **negrita**) |
  |---|---|
  | Mangueras | **Tipo** (opción: R1, R2, R3, R12, 4SP, 4SH), **Diámetro** (opción: 1/4", 5/16", 3/8", 1/2", 5/8", 3/4", 1", 1 1/4", 1 1/2", 2"), Material (texto) |
  | Conexiones | **Tipo** (texto), Rosca (opción: JIC, NPT, BSP, ORFS, Métrica), **Medida** (opción: las del diámetro), Material (texto) |
  | Ferrules | **Tipo** (texto), **Medida** (opción: las del diámetro) |
  | Ferretería | ninguno |

  Tipo y diámetro de mangueras, y rosca y medida de conexiones, son filtrables. El Admin
  ajusta todo esto antes de la puesta en uso (pregunta abierta de las medidas comunes).
- **Razón:** jsonb evita una tabla EAV y una migración por atributo; la validación en el
  dominio se prueba sin base de datos.
- **Alternativas:** tabla `product_attribute_value` (más uniones para buscar y filtrar,
  sin beneficio con este volumen); columnas fijas por categoría (no editables por el
  Admin, contradice RF-04).

## R6. Precio de venta, costo y esquemas por rol (FR-011 a FR-015, principio IV)

- **Decisión:**
  - `product.sale_price_usd` (`usd_amount`, nulo = sin precio) y `product_price` de
    solo inserción con cada fijación (`price_usd`, `valid_from`, `set_by`). Solo
    `PUT /products/{id}/price` (Admin) los cambia.
  - `product.avg_cost_usd` (`usd_cost`, nulo = sin costo, distinto de `0`) y
    `product.cost_locked` (bool, `false`). `PUT /products/{id}/initial-cost` (Admin)
    acepta costos `>= 0` con hasta 6 decimales y responde 409 `cost_locked` si
    `cost_locked` es verdadero. La etapa 1.2 lo pone en `true` al confirmar la primera
    compra (RN-09).
  - **Tres esquemas de respuesta** para producto y kardex: `ProductAdmin` (precio y
    costo), `ProductSeller` (precio, sin costo) y `ProductWarehouse` (ni precio ni
    costo). El endpoint elige el esquema por el rol leído de la base; el OpenAPI los
    declara como unión. Los campos prohibidos no existen en el esquema del rol, no se
    filtran después (arquitectura §4.4).
  - Prueba transversal `test_no_cost_leak.py`: recorre cada endpoint de la etapa con
    Vendedor y Almacén y falla si la respuesta JSON contiene, en cualquier nivel, claves
    con `cost` o `margin`, o con `price` en el caso del Almacén (SC-004).
- **Listas de precios futuras (RN-18):** el diseño no las impide: se agregarían una
  tabla `price_list` y `price_list_id` nulo en `product_price` (nulo = precio general),
  sin tocar `product` ni las ventas, que guardan su propio precio unitario.
- **Alternativas:** un único esquema con campos nulos según el rol (fácil de filtrar
  mal: la arquitectura lo descarta); endpoints separados por rol (duplica rutas).

## R7. Ajustes manuales y aprobación del Almacén (FR-019, FR-019a, FR-019b, RN-19)

- **Decisión:**
  - `POST /inventory/adjustments`: el Admin (cualquier signo) y el Almacén (positivo)
    generan el movimiento de inmediato. Un negativo del Almacén crea una fila en
    `adjustment_request` (`pending`) **sin** movimiento.
  - `POST /inventory/adjustment-requests/{id}/approve` (Admin): bloquea la solicitud y el
    producto, valida que siga `pending` y que el stock no quede negativo, crea el
    movimiento (`reference_type = 'adjustment_request'`) y marca `approved`. `reject`
    (Admin, motivo obligatorio) y `withdraw` (el Almacén que la creó) cambian el estado
    sin movimiento.
  - Trigger: `adjustment_request` solo admite `UPDATE` mientras está `pending`, y solo
    hacia un estado final.
  - El movimiento queda con `created_by` = quien lo ejecuta (el Admin que aprueba); quien
    lo solicitó está en la solicitud, y el kardex muestra ambos.
- **Razón:** el kardex sigue siendo solo de hechos consumados e inmutables; la
  solicitud pendiente es un registro aparte con su propio ciclo de vida. Revalidar al
  aprobar cubre el caso de stock que bajó mientras tanto (casos límite de la spec).
- **Alternativas:** movimiento con estado "pendiente" dentro del kardex (rompe la
  inmutabilidad y complica el saldo); aprobar con PIN del Admin en el equipo del Almacén
  (el PIN es para descuentos en el mostrador; aquí el Admin aprueba desde su sesión).

## R8. Conteo físico a ciegas (FR-024 a FR-027, RN-19)

- **Decisión:**
  - `stock_count` con `status`: `open` → `ready_for_review` → `applied`, con
    `ready_for_review` → `open` (el Admin lo devuelve) y `open | ready_for_review` →
    `cancelled`. Alcance guardado en `scope` jsonb (`all`, categorías o productos).
    El Almacén solo cancela conteos `open`; uno `ready_for_review` lo decide el Admin
    (FR-025a). Cancelar exige motivo.
  - Al abrir, se crean las líneas con `counted_quantity` nulo: en `all` y por
    categorías, de los productos activos y de los inactivos con stock distinto de cero
    (FR-007); en `products`, de los elegidos, estén activos o no. Índice único parcial
    `stock_count_line (product_id) WHERE is_open` impide que un producto esté en dos
    conteos abiertos aunque se abran a la vez (FR-024).
  - Al anotar una línea se guardan `counted_quantity`, `expected_quantity` (stock en ese
    momento), `counted_by` y `counted_at`; anotar de nuevo vuelve a tomar el stock
    (FR-025).
  - **A ciegas:** las respuestas del conteo para el Almacén usan `StockCountLineBlind`,
    sin `expected_quantity` ni `difference` (mismo criterio que R6). La ficha de
    producto sigue mostrando el stock, como permite la matriz (supuesto de la spec).
  - Aplicar (Admin): bloquea el conteo; por cada línea anotada con diferencia distinta de
    cero, `post_movement` con `adjustment_reason = 'physical_count'` y
    `reference_type = 'stock_count_line'`, permitiendo saldo negativo e informándolo en
    la respuesta; marca las líneas `is_open = false` y el conteo `applied`, todo en una
    transacción. Cancelar también marca las líneas `is_open = false` (libera los
    productos para otro conteo) antes de pasar el conteo a `cancelled`.
  - Triggers: en las líneas, los campos de anotación (`counted_quantity`,
    `expected_quantity`, `counted_by`, `counted_at`) solo cambian con el conteo `open`;
    los de cierre (`is_open` a `false` y `stock_movement_id`) solo cambian con el conteo
    `open` o `ready_for_review`, que es cuando se aplica o se cancela. Por eso el
    servicio cierra primero las líneas y después cambia el estado del conteo. Una vez
    `applied` o `cancelled`, ni las líneas ni el conteo cambian.
- **Razón:** calcular la diferencia contra el stock del momento de anotar conserva las
  compras y ventas posteriores (supuesto de la spec). El índice parcial resuelve la
  concurrencia sin bloqueos explícitos.
- **Alternativas:** foto del stock al abrir el conteo (pierde los movimientos durante el
  conteo); tabla aparte de "productos en conteo" (más filas que mantener y borrar, y el
  rol de la API no tiene `DELETE`).

## R9. Fotos de productos (FR-008)

- **Decisión:**
  - **Subida a través de la API:** el navegador reduce la imagen (lado mayor de 1.600 px,
    JPEG por canvas, que funciona en todos los navegadores) y la envía en
    `multipart/form-data` a `POST /products/{id}/photos`. La API valida tipo real y
    tamaño (máximo 5 MB recibidos), la normaliza con **Pillow** a WebP de lado mayor
    1.200 px, sin metadatos EXIF (corrige la orientación), y la guarda en Supabase
    Storage.
  - **Bucket público `product-photos`**, ruta `products/{product_id}/{photo_id}.webp`
    (UUIDv7, no adivinable). La app y el catálogo usan la URL pública. Las fotos no son
    información sensible: se publican en el catálogo.
  - **Acceso a Storage:** `services/photo_storage.py` con dos implementaciones: Supabase
    (API REST de Storage con `httpx` y la clave secreta del proyecto, secreto nuevo
    `supabase-storage-key`) y disco local para desarrollo y pruebas
    (`PHOTO_STORAGE=local`, servido en `/media` solo en `local`).
  - `product_photo` sin borrado físico de filas: quitar una foto pone `removed_at` y
    borra el objeto de Storage. Máximo 5 fotos activas; el orden se cambia con
    `PUT /products/{id}/photos/order`.
- **Razón:** la clave de Storage nunca llega al navegador y el permiso de quién sube se
  verifica en la API (principio IV). Normalizar en el servidor garantiza el formato
  aunque el navegador no sepa codificar WebP (Safari). Con WebP de 1.200 px (~100–200 KB),
  1.000 productos con 3 fotos ocupan ~0,5 GB: dentro de 1 GB de Supabase Free, con el
  criterio de ADR-0002 para pasar a Pro al 70 %.
- **Respaldo de fotos (pendiente de `docs/despliegue.md` §8):** el workflow
  `backup.yml` suma un paso que sincroniza el bucket con `rclone` (protocolo S3 de
  Supabase Storage) hacia `gs://sht-gestion-respaldos/fotos/`, sin la regla de 30 días
  para ese prefijo. Hoy la regla del bucket borra cualquier objeto de más de 30 días
  (`docs/despliegue.md`), así que se cambia en el bucket real a
  `{"action": {"type": "Delete"}, "condition": {"age": 30, "matchesPrefix": ["sht-"]}}`,
  que solo alcanza los volcados de la base. Las fotos ocupan poco y entran en el nivel
  gratuito.
- **Alternativas:** subida directa del navegador con URL firmada (ahorra un salto, pero
  la validación y normalización quedarían sin control del servidor); compresión solo en
  el navegador (Safari no exporta WebP); bucket privado con URL firmadas (complica el
  catálogo y la caché sin proteger nada sensible).

## R10. Activación, edición y cambios restringidos (FR-004, FR-005, FR-007)

- **Decisión:** `PATCH /products/{id}` (Admin y Almacén) edita nombre, descripción,
  atributos, stock mínimo, categoría, unidad e `is_active`. Categoría y unidad solo
  cambian si el producto no tiene movimientos (409 `product_has_movements`); la unidad
  de una categoría con `unit_locked` no cambia (422). El stock mínimo se valida con los
  decimales de la unidad (R3), también cuando cambia la unidad. Publicar
  (`is_published`) va en `PUT /products/{id}/publication` (solo Admin), que exige
  producto activo y con precio. Desactivar un producto lo despublica en la misma
  operación.
- **Advertencias sin bloquear** (`warnings` en la respuesta de alta y edición):
  `duplicate_name` si hay otro producto activo con el mismo nombre en la categoría (al
  crear o al renombrar); `has_stock` al desactivar un producto con stock distinto de
  cero; `stale_data` cuando el `updated_at` enviado no coincide con el guardado (R15).
- **Razón:** separar publicación y precio en endpoints propios hace trivial la matriz
  de permisos y la auditoría de cada cambio.

## R11. Stock bajo y pendientes del Admin (RF-11, FR-019b, FR-023)

- **Decisión:** "stock bajo" = producto activo con `stock <= min_stock`; filtro
  `low_stock=true` en la búsqueda y `GET /inventory/low-stock`. `GET /inventory/summary`
  devuelve contadores para el inicio: productos con stock bajo (Admin y Almacén),
  ajustes pendientes y conteos listos para revisión (Admin), y solicitudes propias
  (Almacén). La pantalla de inicio los muestra como tarjetas con enlace (cierra el
  pendiente "dónde aparece el aviso" de la aclaración). Sin notificaciones push.
- **Razón:** la consulta es trivial con ~1.000 productos; no hace falta tabla de
  alertas para esto. La tabla `alert` del modelo queda para las anomalías de la
  sincronización (etapa 1.5).

## R12. Datos iniciales (FR-028)

- **Decisión:** la migración `0004` crea las tablas y, en la misma revisión, inserta
  las unidades `m` (metro, 2 decimales) y `u` (unidad, 0), las cuatro categorías con
  prefijo, unidad sugerida y `unit_locked` en Mangueras, y los atributos de R5. Los
  identificadores son UUIDv7 fijos en la migración para que sean reproducibles.
- **Razón:** el sistema debe tener la estructura al instalarse, sin depender de un
  paso manual. Es una migración de datos de una sola vez; luego el Admin edita.

## R13. Pantallas en un sitio estático (FR-035, FR-036)

- **Decisión:** rutas sin segmentos dinámicos (el export estático no los admite sin
  conocer los ID al compilar): `/productos/` (lista y búsqueda), `/productos/ficha/?id=`
  (ficha con pestañas datos, fotos, precio/costo, kardex), `/productos/nuevo/`,
  `/inventario/ajuste/`, `/inventario/stock-bajo/`, `/inventario/conteos/`,
  `/inventario/conteo/?id=`, `/pendientes/` (Admin), `/inventario/mis-solicitudes/`
  (Almacén), `/configuracion/categorias/` y `/configuracion/unidades/`. Menú por rol
  como en 1.1a. Componentes nuevos de la guía de estilos: buscador con filtros, chips de
  estado (stock bajo, stock negativo, inactivo, publicado, pendiente), galería de fotos y campo
  decimal con coma.
- **Formato:** `packages/shared/src/format.ts` suma `formatDecimal` (`1.234,56`) y
  `formatQuantity` según los decimales de la unidad, y `parseDecimalInput` (acepta coma
  decimal y punto de miles, devuelve la cadena con punto para la API). No hay aritmética
  de dinero en el frontend en esta etapa: el módulo `money.ts` llega con la 1.3.

## R14. Auditoría de la etapa (FR-034, SC-007)

- **Decisión:** acciones nuevas con `record_audit` en la misma transacción:
  `product.created`, `product.updated`, `product.category_changed` (SKU anterior y
  nuevo), `product.activated`/`deactivated`, `product.published`/`unpublished`,
  `product.price_set`, `product.initial_cost_set`, `product.photo_added`/`removed`,
  `inventory.adjustment_applied`, `inventory.adjustment_requested`,
  `inventory.adjustment_approved`/`rejected`/`withdrawn`,
  `stock_count.opened`/`ready`/`returned`/`applied`/`cancelled`,
  `category.created`/`updated`, `attribute.created`/`updated`, `unit.created`/`updated`.
  Cada ajuste, manual o generado al aplicar un conteo, escribe su propio
  `inventory.adjustment_applied` con producto, cantidad, motivo y stock antes y después
  (los del conteo llevan además `stock_count_id`); `stock_count.applied` resume el
  conteo (líneas, ajustes generados y productos que quedaron negativos) (SC-007).
  Etiquetas en español en `packages/shared/src/audit-actions.ts` y filtros por grupo
  (Productos, Inventario, Configuración) en la pantalla de auditoría.
- **Razón:** extiende el diseño de 1.1a (FR-024 de esa spec) sin cambios de esquema.

## R15. Concurrencia en ediciones de producto

- **Decisión:** el último que guarda gana en los datos descriptivos (nombre,
  atributos). `PATCH /products/{id}` recibe el `updated_at` que la pantalla leyó; si no
  coincide con el guardado, el cambio se aplica igual y la respuesta incluye
  `warnings: ["stale_data"]` para que la pantalla avise y muestre los datos actuales.
  Stock, precio, costo y SKU nunca se editan en conflicto porque pasan por
  operaciones con bloqueo de fila (R1, R2, R6).
- **Razón:** pocos usuarios; un control optimista completo no compensa en datos
  descriptivos.

## R16. Rendimiento y pruebas de carga ligeras (SC-001, SC-006)

- **Decisión:** prueba `db` que carga 1.000 productos sintéticos y mide la búsqueda en
  el servidor (< 200 ms por consulta en CI, margen amplio para el segundo de SC-001 con
  red); prueba de 20 altas simultáneas en hilos sobre la misma categoría para SC-006; la
  medición de punta a punta en el teléfono se hace en la validación manual
  (quickstart).
