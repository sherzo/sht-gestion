# Research: Proveedores, compras con gastos y tasa BCV (etapa 1.2)

Decisiones técnicas de la etapa. Cada una cita los requisitos de
[spec.md](spec.md) que resuelve. No quedaron preguntas abiertas en el contexto técnico:
el stack, el patrón de capas y las convenciones vienen de las etapas 1.1a y 1.1b.

## R1. Cálculos de costo en un módulo de dominio puro (FR-007, FR-011, FR-018, FR-030, FR-031; RN-09, RN-20; ADR-0004)

**Decisión:** nuevo `backend/app/domain/costing.py`, sin base de datos, con:

- `charge_amount_usd(charge, merchandise_total_usd, rate)`: porcentaje × total, monto
  en USD o monto en Bs ÷ tasa, a 2 decimales;
- `allocate_by_value(line_totals, charges_total)`: reparto proporcional a 2 decimales,
  con el residuo a la línea de mayor valor (la primera, si hay empate);
- `landed_unit_cost(unit_cost_usd, allocated, quantity)`: a 6 decimales;
- `weighted_average(stock, cost, quantity, unit_cost)`: devuelve `unit_cost` si
  `stock <= 0` o `cost is None` (FR-011, FR-015);
- `undo_purchase(stock, cost, quantity, unit_cost)`: devuelve `None` si
  `stock - quantity <= 0` o si el resultado es negativo, para que quien llama conserve
  el costo y cree la alerta (FR-018).

`app/domain/money.py` suma los helpers de redondeo `round_usd` (2 decimales),
`round_cost` (6) y `ves_to_usd_cost`, todos con `ROUND_HALF_UP`. Es el único lugar del
backend que redondea montos (ADR-0004).

**Casos compartidos (SC-001):** un archivo `backend/tests/cases/costing_cases.json` con
los ejemplos de la spec y los bordes (stock positivo, cero y negativo, producto sin
costo, Bs, gastos por porcentaje y fijos, empate en el reparto, anulación válida e
inválida). Lo consumen las pruebas de dominio y las de integración.

**Razón:** son reglas críticas (principio VII) y se prueban sin base de datos, como
`units.py` y `sku.py` en la 1.1b.

**Alternativas:** calcular en SQL (difícil de probar y duplicaría el redondeo);
replicar el cálculo en TypeScript (innecesario: los costos no viajan al mostrador sin
conexión, ADR-0004; ver R4).

## R2. Inmutabilidad de las compras impuesta en la base (FR-016, SC-002; RN-14)

**Decisión:** la migración `0005_proveedores_y_compras` agrega triggers con el mismo
estilo que `0004`:

- `purchase_guard` (BEFORE UPDATE OR DELETE en `purchase`):
  - `DELETE` solo si `status = 'draft'`;
  - `UPDATE` libre con `OLD.status = 'draft'`;
  - `confirmed → voided` solo cambia `status` (ninguna otra columna);
  - cualquier otro cambio se rechaza.
  - Al pasar a `confirmed` exige `number`, `confirmed_by` y `confirmed_at`.
- `purchase_child_guard` (BEFORE INSERT OR UPDATE OR DELETE en `purchase_item` y
  `purchase_charge`): solo si la compra madre está en `draft`.
- `purchase_void`: de solo inserción, con el `reject_change()` de `0004`.

**Descartar un borrador:** el servicio borra primero las líneas y los gastos, y después
la compra, en la misma transacción. No se usa `ON DELETE CASCADE`, para que el trigger
de las hijas vea la compra madre todavía en `draft`.

**Estado `voided`:** la compra anulada pasa de `confirmed` a `voided`, y el detalle de
la anulación queda en `purchase_void`. Así el listado filtra por estado sin `JOIN`.
`docs/modelo-de-datos.md` §3.4 se actualiza: `status` = `draft | confirmed | voided`.

**Alternativas:** solo validar en el servicio (no cumple "ni en la base de datos",
SC-002); permisos `REVOKE` por rol (la API usa un solo rol de base de datos y los
triggers ya son el patrón del proyecto).

## R3. Confirmación atómica, sin dobles confirmaciones ni bloqueos cruzados (FR-008, FR-010, FR-014, SC-006)

**Decisión:** `services/purchases.py::confirm_purchase`, en una sola transacción:

1. Lee la compra con `SELECT … FOR UPDATE`. Si no está en `draft`, responde 409
   `invalid_state`; así una segunda confirmación (doble clic) falla. Si el
   `updated_at` recibido no coincide con el guardado, responde 409 `stale_data` con la
   compra actual: otro usuario la cambió y hay que revisarla antes de confirmar (spec,
   Edge Cases). A diferencia de guardar (R4), aquí no se sigue adelante, porque
   confirmar es irreversible.
2. Revalida que el proveedor y los productos estén activos y vuelve a buscar la tasa
   para la fecha (R6).
3. Recalcula y guarda los montos con `costing` (las líneas siguen en borrador).
4. Bloquea los productos **en orden de `product_id`**, para evitar bloqueos cruzados
   entre dos compras con los mismos productos.
5. Por cada línea, llama a `post_movement` (`type='purchase'`) con el costo antes y
   después, actualiza `product.avg_cost_usd`, pone `cost_locked = true` y audita
   `product.cost_updated`.
6. Toma el número con `sequence_counter` (fila `purchase`, `FOR UPDATE`). Se toma al
   final para no retener ese bloqueo mientras se procesan las líneas; como todo va en
   la misma transacción, un fallo no deja huecos (FR-008).
7. Pasa la compra a `confirmed`, audita `purchase.confirmed` y confirma la
   transacción.

`post_movement` (`services/inventory.py`) suma los parámetros opcionales
`cost_before_usd` y `cost_after_usd`. Las columnas ya existen en `stock_movement`.

**Prueba de concurrencia:** 20 hilos confirman compras del mismo producto (SC-006). El
stock y el costo deben coincidir con confirmarlas en serie, y los números deben ser
consecutivos y sin repetirse.

**Alternativas:** una secuencia de Postgres (deja huecos si la transacción falla, y
FR-008 pide que no haya); número al crear el borrador (deja huecos al descartar).

## R4. El servidor es el único que calcula; el borrador se guarda entero (FR-005, FR-007, FR-029 a FR-031)

**Decisión:**

- `PUT /purchases/{id}` reemplaza el borrador completo: cabecera, líneas y gastos.
  Responde con todos los montos calculados (totales de línea, total de mercancía,
  gastos en USD, reparto y costo final).
- La pantalla calcula en el navegador solo lo trivial: cantidad × costo de cada línea,
  para mostrarlo al escribir. El reparto y el costo final los muestra después de
  guardar, con el botón "Guardar y calcular".
- Al guardar, el borrador vuelve con `warnings`:
  - `stale_data`: `updated_at` distinto, igual que en productos (R15 de la 1.1b);
  - `duplicate_invoice`;
  - `charges_over_100_percent`.

**Razón:** una sola implementación del redondeo (ADR-0004), y un borrador con 200
líneas se guarda en una petición. La compra se registra con conexión (spec,
Assumptions).

**Alternativas:** un endpoint por línea (más peticiones y más estados intermedios);
replicar `costing` en TypeScript (dos implementaciones que mantener iguales sin
necesidad).

## R5. Proveedores y RIF (FR-001 a FR-003)

**Decisión:** `domain/rif.py::normalize_rif(text)`:

- acepta mayúsculas o minúsculas, con o sin guiones o espacios;
- exige la letra `J|G|V|E|P|C`, de 1 a 8 dígitos de número y 1 dígito verificador;
- rellena el número con ceros a la izquierda hasta 8 dígitos;
- devuelve `X-NNNNNNNN-N`.

No se verifica el dígito verificador con el algoritmo del SENIAT, para no rechazar un
RIF real por una variante del cálculo; basta con el formato y la unicidad. La unicidad
se impone con un índice único sobre `rif` (nulo permitido); el choque responde 409
`rif_in_use` con el nombre del proveedor que ya lo tiene.

**Alternativas:** validar el dígito verificador (riesgo de falsos rechazos sin valor
para el negocio).

## R6. Tasa BCV adelantada de la 1.3 (FR-012, FR-013, FR-025 a FR-028; RN-03, RN-15)

**Decisión:**

- Tabla `exchange_rate`, con `rate_type` (`BCV`) y una fila por `(rate_type,
  business_date)`. Corregir actualiza `rate`, `updated_by` y `updated_at`, y audita
  `exchange_rate.corrected` con el valor anterior y el nuevo. Las tasas no se borran
  (trigger).
- Búsqueda: `services/exchange_rates.py::applicable_rate(db, date)`, con la última
  tasa cuya `business_date <= date`. Responde `(rate, business_date)` o `None`.
- Compra en Bs, o con algún gasto en Bs, sin tasa aplicable: 409
  `exchange_rate_missing`.
- Compra en USD sin gastos en Bs: guarda la tasa si existe, solo como referencia.
- La compra copia `exchange_rate` y `exchange_rate_date`. Mientras es borrador se
  recalcula en cada `PUT` y en la confirmación (FR-012). Confirmada, es inmutable por
  R2, así que corregir una tasa no la toca (SC-009).
- Fecha futura (hora de Caracas, `domain/business_time.py`): se rechaza con 422 en la
  tasa y en la compra.

La etapa 1.3 reutiliza la tabla y el servicio para la venta y el aviso al abrir caja
(RF-18). En esta etapa el Vendedor no tiene acceso.

## R7. Esquemas por rol y fuga de costos (FR-009, FR-022, FR-033; principio IV)

**Decisión:**

- **Admin y Almacén** reciben la compra con el mismo esquema `Purchase`: costos de
  factura, gastos, reparto y costo final. Son datos de la compra, no del producto
  (excepción del principio IV, constitución 1.2.0).
- **Solo el Admin recibe:**
  - `cost_changes` en la respuesta de confirmar (costo antes y después por producto);
  - la vista previa de anulación (`GET /purchases/{id}/void-preview`);
  - los campos de costo del kardex, que ya se filtran con `movement_for_role`.
- **Vendedor:** 403 en proveedores, compras, gastos frecuentes y tasas.
- `test_no_cost_leak.py` se amplía: ninguna respuesta de compras, confirmación ni
  kardex al Almacén contiene `avg_cost_usd`, `cost_before_usd`, `cost_after_usd` ni
  `cost_changes`.

## R8. Alertas para el Admin (FR-018; RN-14)

**Decisión:** se crea ahora la tabla `alert` del modelo de datos (§3.1), y la usa solo
el tipo `purchase_void_cost`. Guarda en `details` el producto, la compra, el stock y
los costos.

- Endpoints de Admin: `GET /alerts?status=open|resolved` y
  `POST /alerts/{id}/resolve`.
- La pantalla `/pendientes/` suma la sección "Alertas", y `GET /inventory/summary`
  (Admin) suma `open_alerts`.
- Las etapas 1.3 y 1.5 agregan otros tipos (`negative_stock`, etc.) sin cambiar la
  tabla.

## R9. Gastos frecuentes (FR-032)

**Decisión:**

- Tabla `charge_template`, que solo el Admin crea, edita, desactiva y reactiva.
- El Almacén la lee (`GET /charge-templates`, solo los activos).
- Al elegir uno, la pantalla copia nombre, tipo, valor y moneda al gasto del borrador
  y guarda `charge_template_id` como referencia. La compra nunca lee la plantilla al
  calcular, así que editarla no cambia compras existentes.
- Nombre único entre las activas, sin distinguir mayúsculas.
- Audita `charge_template.created` y `charge_template.updated`.

## R10. Anulación (FR-017 a FR-019; RN-14)

**Decisión:** `services/purchases.py::void_purchase`, en una transacción. Lee la compra
`FOR UPDATE` y debe estar `confirmed`. Bloquea los productos en orden y, por cada línea:

- `post_movement` con `type='purchase_void'`, `quantity_delta = -quantity` y
  `allow_negative=True`;
- `costing.undo_purchase` con `landed_unit_cost_usd`; si devuelve `None`, se conserva
  el costo y se crea la alerta;
- auditoría `product.cost_updated` cuando el costo cambia.

Después inserta `purchase_void`, pasa la compra a `voided` y audita `purchase.voided`
con el motivo (mínimo 5 caracteres; si no, 422).

La vista previa `GET /purchases/{id}/void-preview` usa el mismo cálculo sin escribir
nada, y muestra por producto el stock y el costo resultantes y si genera alerta
(FR-019).

`cost_locked` no se desbloquea al anular (spec, Edge Cases). Si el costo había entrado
"sin promediar" (stock previo ≤ 0), deshacer con la fórmula es una aproximación que
RN-14 acepta: el resultado se valida igual y, si no es válido, se alerta.

## R11. Pantallas en el sitio estático (FR-024; R13 de la 1.1b)

**Decisión:** rutas sin parámetros dinámicos, con `?id=`:

| Ruta | Quién | Contenido |
|---|---|---|
| `/compras/` | Admin, Almacén | Lista con filtros (proveedor, fechas, estado, producto) y botón "Nueva compra" |
| `/compras/editar/?id=` | Admin, Almacén | Borrador: cabecera, líneas (buscador de productos de la 1.1b), sección plegable "Gastos", totales, "Guardar y calcular", "Confirmar", "Descartar" |
| `/compras/detalle/?id=` | Admin, Almacén | Compra confirmada o anulada; botón "Anular" (Admin) con la vista previa |
| `/proveedores/` | Admin, Almacén | Lista, alta y edición en diálogo |
| `/tasas/` | Admin | Cargar la tasa del día, corregir e histórico |
| `/configuracion/gastos/` | Admin | Gastos frecuentes (nueva pestaña de Configuración) |

El menú (`components/app-shell.tsx`) suma "Compras" y "Proveedores" (Admin y
Almacén) y "Tasa BCV" (Admin).

En `packages/shared/src/format.ts` se agregan:

- `formatVes` (`Bs 1.234,56`);
- `formatRate` (hasta 8 decimales sin ceros sobrantes);
- `formatPercent`.

Los tipos se regeneran con `pnpm api:types`.

## R12. Auditoría de la etapa (FR-023, SC-007; RF-46)

**Acciones nuevas** (grupo "Compras y tasas" en `audit-actions.ts`):

| Acción | Entidad | Detalle |
|---|---|---|
| `supplier.created`, `supplier.updated` | proveedor | Valores antes y después |
| `purchase.confirmed` | compra | Número, proveedor, totales y cantidad de líneas |
| `purchase.voided` | compra | Número y motivo |
| `product.cost_updated` | producto | Costo antes y después, compra y causa (`purchase` o `purchase_void`) |
| `exchange_rate.created`, `exchange_rate.corrected` | tasa | Fecha y valores |
| `charge_template.created`, `charge_template.updated` | gasto frecuente | Valores antes y después |
| `alert.resolved` | alerta | — |

Guardar o descartar borradores no se audita: no son acciones sensibles y no tocan
stock ni costo.

## R13. Rendimiento y límites (SC-003, SC-006, SC-011)

- Hasta 500 líneas y 20 gastos por compra (422 si se superan). El spec pide al menos
  200 líneas.
- La confirmación de 200 líneas hace unas 200 inserciones y actualizaciones en una
  transacción; se mide en la prueba de concurrencia y debe tardar menos de 5 s en
  Cloud Run.
- Índices:
  - `purchase (status, purchase_date DESC)`;
  - `purchase (supplier_id, purchase_date DESC)`;
  - `purchase_item (product_id)`, para filtrar compras por producto.
- La lista de compras se pagina como las demás (`page_size` máximo 100).
