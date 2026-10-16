# Guía de validación: caja, egresos, cierre y cuadre

Escenarios para comprobar de punta a punta que la etapa 1.4 cumple la especificación.

- Endpoints, errores y permisos: `contracts/api.md`.
- Tablas y reglas: `data-model.md`.
- Decisiones: `research.md`.

## Preparación local

```bash
docker compose up -d                      # Postgres 17
cd backend
uv sync                                   # sin dependencias nuevas
uv run alembic upgrade head               # incluye 0007_cierre_de_caja
uv run python -m uvicorn app.main:app --reload   # http://localhost:8000
# en otra terminal, desde la raíz
pnpm install                              # sin dependencias nuevas
pnpm api:types                            # regenera los tipos del OpenAPI
pnpm dev:app                              # http://localhost:3000
```

No hay variables de entorno ni secretos nuevos. Hacen falta:

- usuarios: el Admin, dos Vendedores y un Almacén;
- dos navegadores registrados como equipos (`A` y `B`);
- productos de prueba con precio;
- la tasa BCV de hoy, 36,50.

## Pruebas automatizadas

```bash
cd backend
uv run ruff check . && uv run ruff format --check .
uv run pytest                             # con DATABASE_URL: incluye las pruebas db
# desde la raíz
pnpm test                                 # casos compartidos de dinero y de caja
pnpm typecheck && pnpm build
```

Pruebas clave de la etapa (todas referencian su FR o RF):

| Prueba | Verifica |
|---|---|
| `test_cash_math.py` y `cash.test.ts` | Los mismos casos de `packages/shared/test-vectors/cash.json`: escenario de la US1, vuelto electrónico, anulación en la misma caja, devolución de otra caja, egreso anulado, caja vacía, contado en blanco y esperado negativo (FR-006, FR-007, SC-002, SC-003; sin base de datos) |
| `test_cash_outflows.py` | Egreso por la cola en Efectivo Bs y USD y por Pago móvil y Binance USDT con referencia; sin tope en los electrónicos; rechazos por referencia faltante, monto ≤ 0, motivo, caja cerrada o ajena y `insufficient_cash`; reenvío sin duplicar; anulación del Admin con caja abierta y rechazo con la caja cerrada; auditoría (FR-001 a FR-004, SC-004) |
| `test_cash_close.py` | Cierre por la cola: esperado del servidor, conteos y diferencias, observación obligatoria con diferencias, alertas `cash_difference` y `expected_mismatch`, segundo cierre rechazado, reenvío sin duplicar, apertura de una caja nueva tras el cierre, venta rechazada en la caja cerrada (FR-005 a FR-017, SC-004, SC-008) |
| `test_cash_close_admin.py` | Cierre del Admin desde otro navegador o de un equipo revocado, observación obligatoria, marca `closed_outside_device`, Vendedor rechazado; venta y egreso creados antes del cierre registrados con alerta `post_close_operation` y los creados después rechazados (FR-018, FR-019) |
| `test_sale_void_closed_session.py` | Anulación con la caja abierta (devolución en esa caja) y con la caja cerrada (devolución en la caja abierta del equipo del Admin, cierre intacto); `cash_session_required` sin equipo o sin caja abierta; detalle de la venta y de la caja original (FR-020 a FR-023, SC-006) |
| `test_cash_immutability.py` | `UPDATE` y `DELETE` directos sobre una caja cerrada, `cash_count` y `cash_outflow` fallan; anular un egreso con la caja cerrada falla en la base; una caja cerrada sin sus seis conteos no se confirma (FR-015, SC-005) |
| `test_cash_sessions_list.py` | Filtros del Admin y diferencias; el Vendedor solo ve la caja abierta de su equipo y sus cierres de hoy (hora de Caracas); 404 fuera de eso; Almacén rechazado (FR-024 a FR-026) |
| `test_cash_performance.py` | Detalle de una caja con 100 ventas en menos de 1 s (R14) |
| `test_no_cost_leak.py` | Endpoints de caja y cola sin costos ni márgenes para el Vendedor (SC-007) |
| `test_permissions_matrix.py` | Filas nuevas de la matriz del contrato (SC-007) |
| `test_audit.py` | Acciones de R12 (FR-027) |

## Escenarios manuales

1. **Esperado por método (US1, escenario 1)**:
   - Como Vendedor en `A`, abrir caja con 500,00 Bs y 20,00 USD.
   - Vender por 47,70 USD y cobrar 50,00 en Efectivo USD con vuelto de 2,30 USD en
     Efectivo USD.
   - Vender por 20,00 USD y cobrar 730,00 Bs por Pago móvil con referencia.
   - En Caja, el esperado es: Efectivo USD 67,70; Efectivo Bs 500,00; Pago móvil
     730,00 Bs; 0,00 en los demás.
2. **Egresos (US2)**:
   - Registrar un egreso de 5,00 USD en Efectivo USD con el motivo "Compra de
     botellones de agua": el esperado baja a 62,70.
   - Intentar un egreso sin motivo y otro de 100,00 USD en Efectivo USD: el primero no
     deja confirmar; el segundo se rechaza indicando el disponible.
   - Registrar un egreso de 300,00 Bs por Pago móvil con referencia (sin cobros por Pago
     móvil): se acepta y el esperado de Pago móvil queda en −300,00. Sin referencia, no
     deja confirmar.
   - Como Admin, anular el egreso con motivo: queda tachado como anulado, el esperado
     vuelve a 67,70 y la auditoría registra las dos acciones.
3. **Cierre con diferencia (US1)**:
   - Con una venta en otra pestaña sin red (queda pendiente en la cola), intentar
     cerrar: no deja y lista la operación pendiente. Restablecer la red y esperar a que
     se envíe.
   - Cerrar escribiendo 66,70 en Efectivo USD y el esperado en los demás: muestra
     −1,00 en Efectivo USD y exige una observación.
   - Confirmar: el cierre queda guardado, en Pendientes aparece la alerta de diferencia
     y Caja ofrece abrir una caja nueva.
   - Ir a Vender: pide abrir caja.
4. **Cierre sin diferencias**: abrir otra caja, hacer una venta y cerrar con los montos
   exactos. No pide observación ni crea alerta.
5. **Anulación con la caja cerrada (US3)**:
   - Abrir caja nueva en `A`. Como Admin en el navegador de `A`, anular la venta del
     escenario 1 (caja ya cerrada). El diálogo avisa que la devolución va a la caja
     abierta de `A`.
   - El stock vuelve; el cierre anterior conserva sus montos; la caja nueva muestra la
     devolución restando de Efectivo USD y Pago móvil.
   - Como Admin en un navegador que no es equipo, intentar anular otra venta de una caja
     cerrada: se rechaza indicando que debe hacerlo desde un equipo con caja abierta.
6. **Consulta (US4)**:
   - Como Admin, ir a Cajas y filtrar por fecha y equipo: las cajas con diferencias se
     ven resaltadas. Abrir el detalle: movimientos por método, pagos electrónicos con
     referencia y enlace a la venta, egresos, cuadre y ventas anuladas después del
     cierre.
   - Como Vendedor, ver solo la caja abierta de su equipo y sus cierres de hoy.
   - Como Almacén, no ve el menú y la API responde 403.
7. **Caja huérfana (US5)**:
   - Abrir caja en `B` y vender una vez. Revocar `B` desde Configuración > Equipos.
   - Como Admin en otro navegador, abrir el detalle de esa caja y usar "Cerrar esta
     caja" con lo contado y una observación. Queda cerrada, marcada como cerrada fuera
     del equipo.
   - Como Vendedor, la API rechaza el cierre de una caja de otro equipo (403).
8. **Día de prueba (SC-001, SC-002)**:
   - En una caja nueva, registrar 30 ventas que usen los seis métodos, con vuelto en
     varias, 2 anulaciones y 3 egresos.
   - Calcular a mano (hoja de cálculo) el esperado de cada método a partir de las
     ventas, el vuelto, las anulaciones y los egresos.
   - Medir el cierre completo, contando el efectivo y cotejando los pagos electrónicos
     con la lista de referencias: menos de 10 minutos y esperados idénticos al cálculo
     a mano.
9. **Pantallas**: recorrer Caja, el cierre, Cajas y su detalle en un teléfono de 360 px
   y en PC: sin desplazamiento horizontal, montos `1.234,56` en la moneda de cada
   método, fechas `dd/mm/aaaa` y hora de Caracas.

## Cierre de la etapa

- Actualizar (RNF-09):
  - `docs/modelo-de-datos.md`, con los cambios listados en `data-model.md`;
  - `docs/arquitectura.md`: flujo del cierre, servicios de caja, matriz por endpoint y
    glosario (`cash_count`, `post_close_operation`);
  - ADR-0003: tipos de operación de la caja y devolución en otra caja;
  - `docs/plan-de-fases.md`;
  - `CHANGELOG.md`.
- Probar en local la restauración del respaldo (plan de fases, definición de terminado).
- La etapa cierra como versión `0.5.0`.
