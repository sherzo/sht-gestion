# Guía de validación: proveedores, compras con gastos y tasa BCV

Escenarios para comprobar de punta a punta que la etapa 1.2 cumple la especificación.

- Endpoints, errores y permisos: `contracts/api.md`.
- Tablas y estados: `data-model.md`.
- Decisiones: `research.md`.

## Preparación local

```bash
docker compose up -d                      # Postgres 17
cd backend
uv sync                                   # sin dependencias nuevas
uv run alembic upgrade head               # incluye 0005_proveedores_y_compras
uv run python -m uvicorn app.main:app --reload   # http://localhost:8000
# en otra terminal, desde la raíz
pnpm install
pnpm api:types                            # regenera los tipos del OpenAPI
pnpm dev:app                              # http://localhost:3000
```

No hay variables de entorno ni secretos nuevos. Usuarios de prueba: el Admin, un
Vendedor y un Almacén de las etapas anteriores, y productos de prueba (por ejemplo,
`seed-demo-products`).

## Pruebas automatizadas

```bash
cd backend
uv run ruff check . && uv run ruff format --check .
uv run pytest                             # con DATABASE_URL: incluye las pruebas db
# desde la raíz
pnpm typecheck && pnpm build
```

Pruebas clave de la etapa (todas referencian su FR o RN):

| Prueba | Verifica |
|---|---|
| `test_costing_domain.py` | Casos compartidos de `tests/cases/costing_cases.json`: promedio con stock positivo, cero, negativo y sin costo; Bs; gastos por porcentaje y fijos; reparto con residuo y empate; costo final; anulación válida e inválida (FR-011, FR-015, FR-018, FR-030, FR-031, SC-001, SC-010; sin base de datos) |
| `test_rif_domain.py` | Normalización y formato del RIF (FR-002) |
| `test_suppliers.py` | Alta, edición, RIF único, desactivar y reactivar (FR-001 a FR-003) |
| `test_exchange_rates.py` | Carga, duplicado, corrección auditada, fecha futura, tasa aplicable con días sin tasa (FR-025 a FR-028) |
| `test_charge_templates.py` | Alta, nombre único, desactivar, copia a la compra sin vínculo (FR-032) |
| `test_purchases_draft.py` | Crear, guardar entero, recalcular, avisos, descartar, validaciones por unidad, producto repetido, límites (FR-004 a FR-007, FR-029) |
| `test_purchases_confirm.py` | Movimientos, costo con y sin gastos, número sin huecos, `cost_locked`, revalidación de inactivos y de tasa, doble confirmación (FR-008 a FR-015) |
| `test_purchases_concurrency.py` | 20 confirmaciones simultáneas del mismo producto (FR-014, SC-006) |
| `test_purchase_void.py` | Reverso, costo deshecho con el costo final, resultado inválido con alerta, vista previa, una sola vez, motivo (FR-017 a FR-019) |
| `test_purchase_immutability.py` | `UPDATE` y `DELETE` directos en SQL sobre compras confirmadas, líneas, gastos y anulaciones fallan; corregir una tasa no cambia compras confirmadas (FR-016, SC-002, SC-009) |
| `test_alerts.py` | Listado y resolución de alertas (FR-018) |
| `test_no_cost_leak.py` | Sin `avg_cost_usd`, `cost_before_usd`, `cost_after_usd` ni `cost_changes` para el Almacén en compras, confirmación y kardex (FR-022, SC-005) |
| `test_permissions_matrix.py` | Filas nuevas de la matriz del contrato (SC-005) |
| `test_audit.py` | Acciones de R12 con valores antes y después (FR-023, SC-007) |

## Escenarios manuales

1. **Proveedores (US1):** como Almacén, crear "Hidráulica Aragua" con RIF
   `j123456789`: queda `J-12345678-9`. Crear otro con `J-12345678-9`: se rechaza
   indicando el nombre. Crear "Proveedor China" sin RIF. Desactivar "Hidráulica
   Aragua": ya no aparece al crear una compra.
2. **Tasa (US6):** como Admin, en **Tasa BCV**, cargar 36,50 para hoy; intentar
   cargarla otra vez: el sistema ofrece corregirla. Corregir a 36,55: la auditoría
   muestra 36,50 → 36,55. Como Almacén, la pantalla no aparece en el menú y la API
   responde 403.
3. **Compra en USD (US2):** con un producto con stock 10 m y costo inicial 2,00, como
   Almacén crear una compra de 30 m a 3,00 USD, guardar, salir y volver: el borrador
   sigue ahí y el stock no se movió. Confirmar: recibe `C-000001`, el stock es 40 m y,
   como Admin, la ficha muestra costo 2,750000 y el kardex la entrada con costo antes y
   después. Como Almacén, el kardex no muestra costos y la respuesta de confirmar no
   trae `cost_changes`. El costo inicial ya no se puede editar.
4. **Importación con gastos (US7):** crear como Admin los gastos frecuentes
   "Comisión de compra" (10 %) y "Envío China–Venezuela" (monto fijo en USD). Como
   Almacén, compra en USD de "Proveedor China":
   - líneas: 60 u. a 10,00 y 40 u. a 10,00;
   - gastos: elegir la comisión, el envío con 250,00 y escribir a mano "Entrega al
     local" por 3.650,00 Bs.

   "Guardar y calcular": gastos 450,00 USD, reparto 270,00 y 180,00, y costo final
   14,500000 en ambas líneas. Confirmar y comprobar como Admin que el costo de los
   productos con stock 0 pasó a 14,500000.
5. **Compra en Bs (US3):** compra en Bs de 10 u. a 365,00 Bs con tasa 36,50: costo
   10,000000 USD, total 3.650,00 Bs y 100,00 USD. Con una fecha sin tasa, usa la del
   día anterior y muestra su fecha. Con una fecha anterior a todas las tasas, no se
   puede guardar.
6. **Anulación (US4):** como Admin, abrir la compra del escenario 3 y "Anular": la
   vista previa muestra stock 10 m y costo 2,000000. Anular sin motivo: no se puede;
   con motivo: el stock vuelve a 10 m y el kardex muestra el reverso. Vender o ajustar
   hasta dejar menos stock que lo comprado en otra compra y anularla: la vista previa
   avisa, el costo se conserva y aparece una alerta en **Pendientes**; marcarla como
   revisada.
7. **Inmutabilidad (SC-002):** en `psql`, intentar
   `UPDATE purchase_item SET quantity = 1` y `DELETE FROM purchase_charge` sobre una
   compra confirmada: ambos fallan con el mensaje del trigger.
8. **Consulta (US5):** filtrar las compras por proveedor, rango de fechas, estado
   "anulada" y por un producto. Desde el kardex del producto, abrir la compra
   enlazada.
9. **Vendedor:** el menú no muestra Compras, Proveedores ni Tasa BCV, y la API responde
   403 en `/suppliers`, `/purchases`, `/charge-templates` y `/exchange-rates`.
10. **Pantallas (FR-024, SC-008):** recorrer las pantallas en un teléfono de 360 px y
    en PC: sin desplazamiento horizontal, `1.234,56`, `Bs 3.650,00`, fechas
    `dd/mm/aaaa`. Medir que una compra de 10 líneas se registra en menos de 5 minutos
    (SC-003) y que agregar los gastos de una importación toma menos de 1 minuto
    (SC-011).

## Cierre de la etapa

- `docs/modelo-de-datos.md` (cambios listados en `data-model.md`),
  `docs/arquitectura.md` (servicios de compras y tasa, alertas, matriz por endpoint) y
  `CHANGELOG.md` actualizados (RNF-09).
- Restauración del respaldo probada en local (plan de fases, definición de terminado).
- Puesta en uso real tras la 1.2 (plan de fases §3): carga del inventario real con
  conteo y compras, dominio propio, ambiente de pruebas y decidir si se pasa a
  Supabase Pro.
