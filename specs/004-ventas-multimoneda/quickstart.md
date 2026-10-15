# Guía de validación: ventas multimoneda, pagos mixtos, descuentos y apertura de caja

Escenarios para comprobar de punta a punta que la etapa 1.3 cumple la especificación.

- Endpoints, errores y permisos: `contracts/api.md`.
- Tablas y reglas: `data-model.md`.
- Decisiones: `research.md`.

## Preparación local

```bash
docker compose up -d                      # Postgres 17
cd backend
uv sync                                   # sin dependencias nuevas en Python
uv run alembic upgrade head               # incluye 0006_ventas_y_caja
uv run python -m uvicorn app.main:app --reload   # http://localhost:8000
# en otra terminal, desde la raíz
pnpm install                              # suma decimal.js y dexie
pnpm api:types                            # regenera los tipos del OpenAPI
pnpm dev:app                              # http://localhost:3000
```

No hay variables de entorno ni secretos nuevos. Hacen falta:

- usuarios: el Admin con PIN configurado, dos Vendedores y un Almacén;
- productos de prueba con precio, al menos uno por metro y uno por unidad
  (`seed-demo-products`);
- la tasa BCV de hoy, 36,50.

## Pruebas automatizadas

```bash
cd backend
uv run ruff check . && uv run ruff format --check .
uv run pytest                             # con DATABASE_URL: incluye las pruebas db
# desde la raíz
pnpm test                                 # casos compartidos de dinero en TypeScript
pnpm typecheck && pnpm build
```

Pruebas clave de la etapa (todas referencian su FR o RN):

| Prueba | Verifica |
|---|---|
| `test_sale_math.py` y `money.test.ts` | Los mismos casos de `packages/shared/test-vectors/money.json`: líneas por metro y unidad, cm→m, cantidades rechazadas, descuentos y reparto con residuo, Bs del total, pagos mixtos, saldo exacto en Bs, vueltos, sobrepago y bordes x,xx5 (FR-011, FR-013, FR-020, FR-021, FR-035 a FR-038, FR-040, SC-003; sin base de datos) |
| `test_devices.py` | Registro con serie `A`, `B`…, serie nunca reutilizada tras revocar, token, `GET /devices/current`, equipo revocado (FR-001 a FR-004) |
| `test_cash_sessions.py` | Apertura por la cola, una abierta por equipo, sin tasa, fondo ≥ 0, Almacén rechazado (FR-005 a FR-008) |
| `test_sync_idempotency.py` | Reenvío devuelve lo mismo; 10 envíos simultáneos dejan una venta; rechazos guardados y repetidos; tipo desconocido (FR-017, SC-004) |
| `test_sales_create.py` | Venta completa en una transacción: líneas, pagos, kardex, tasa copiada, número, cliente nuevo o existente o por documento repetido, validaciones estructurales, `sequence_conflict` (FR-010 a FR-019, FR-033 a FR-039) |
| `test_sales_alerts.py` | Stock negativo, precio distinto, total distinto y tasa distinta de la cargada: venta registrada con su alerta (FR-030 a FR-032, SC-009) |
| `test_discounts.py` | Autorización por PIN y por solicitud, bloqueo del PIN, vínculo por línea, tipo, valor y base, uso único, Admin sin autorización, venta sin autorización marcada para revisión (FR-020 a FR-029) |
| `test_sales_numbering.py` | Dos equipos con 50 ventas cada uno en paralelo, sin números repetidos (SC-005) |
| `test_sale_void.py` | Reversos de kardex, espejo de pagos y vueltos, una sola vez, motivo, solo Admin (FR-041 a FR-043, SC-008) |
| `test_sale_immutability.py` | `UPDATE` y `DELETE` directos sobre ventas, líneas, pagos y anulaciones fallan; transiciones válidas de autorizaciones y equipos (FR-044, SC-010) |
| `test_sales_list.py` | Filtros del Admin, el Vendedor solo ve sus ventas de hoy (hora de Caracas), 404 en ventas ajenas (FR-045, FR-046) |
| `test_sales_performance.py` | Venta de 20 líneas registrada en menos de 1 s (R16) |
| `test_no_cost_leak.py` | Sin `unit_cost_usd`, `margin_usd` ni `cost_usd` para el Vendedor en ventas, cola y anulación (SC-006) |
| `test_permissions_matrix.py` | Filas nuevas de la matriz del contrato (SC-007) |
| `test_audit.py` | Acciones de R15 (FR-050) |

## Escenarios manuales

1. **Equipo y caja (US1)**:
   - Como Admin, en el navegador del mostrador, ir a Caja y registrar "Mostrador
     principal": recibe la serie `A`.
   - En otro navegador, registrar "Tablet" (`B`), revocarla desde Configuración >
     Equipos y registrar otro: recibe `C`.
   - Como Vendedor, abrir caja en `A` con 500,00 Bs y 20,00 USD.
   - Intentar abrir otra en `A`: se rechaza indicando quién la tiene abierta.
   - Borrar la tasa de hoy en una base de prueba: al abrir caja aparece el aviso con la
     fecha de la última tasa.
2. **Venta con un pago (US2)**:
   - Con tasa 36,50, vender 2 conexiones a 3,25 y `30 cm` de manguera a 4,00 USD/m.
     Se ven subtotales 6,50 y 1,20, total 7,70 USD y 281,05 Bs.
   - Probar `1,5` en una conexión y `30,5 cm` en la manguera: se rechazan.
   - Cobrar 7,70 en Efectivo USD y confirmar: número `A-000001`, dos salidas en el
     kardex y 0,30 m descontados.
   - Empezar otra venta y, como Admin desde otro navegador, corregir la tasa de hoy.
     Sin pagos, la pantalla avisa y pide actualizarla antes del primer pago; con un
     pago registrado, la venta conserva su tasa (FR-014).
3. **Reintento (FR-017)**: con las herramientas del navegador sin red, confirmar una
   venta. Queda "Ventas pendientes de envío: 1". Al volver la red se envía sola y
   aparece una sola vez en Ventas.
4. **Pagos mixtos y vuelto (US3)**:
   - Venta de 50,00 USD: pagar 20,00 en Efectivo USD.
   - Pagar 730,00 Bs por Pago móvil: sin referencia se rechaza, con referencia cubre
     20,00 USD.
   - Pagar 10,00 por Zelle con referencia: falta 0,00.
   - Otra venta de 7,70 pagada con 10,00 USD: dar el vuelto en Efectivo Bs, 83,95 Bs.
   - Pagar el saldo exacto en Bs que sugiere la pantalla: queda en cero.
5. **Descuentos (US4)**:
   - Como Vendedor, 10 % a una línea de 20,00: pide autorización. Con el PIN del Admin
     queda en 18,00 y el detalle muestra quién autorizó.
   - Pedir 5,00 USD sobre el total por solicitud. El Admin la aprueba desde Pendientes
     en otro navegador y el vendedor la ve aprobada en segundos.
   - Pedir 10 % por solicitud y que el Admin la apruebe con 5 %: la línea queda con 5 %
     y el detalle muestra el valor pedido y el aprobado.
   - Cambiar la línea después de autorizar: pide autorización de nuevo.
   - Probar un PIN incorrecto 5 veces: queda bloqueado.
   - Como Admin, vender con descuento sin pedir nada.
6. **Venta sin stock (US5)**: con un producto con stock 2, vender 3. Aparece la
   advertencia, la venta se confirma, el stock queda en −1 y en Pendientes aparece la
   alerta de stock negativo.
7. **Descuento sin autorización (FR-028)**: enviar con `curl` una venta de Vendedor con
   descuento y sin `authorization_id`. Se registra marcada para revisión y aparece la
   alerta. Marcarla como revisada: la venta no cambia.
8. **Anulación (US6)**: como Admin, anular `A-000001` con un motivo. El stock vuelve,
   el kardex muestra los reversos con enlace a la venta, el detalle muestra las
   devoluciones y la auditoría registra el motivo. Intentarlo como Vendedor: no ve la
   opción y la API devuelve 403.
9. **Consulta (US7)**: con ventas de dos vendedores en dos días, el Admin filtra por
   fecha y vendedor y ve costos y márgenes. Cada Vendedor ve solo sus ventas de hoy,
   sin costos.
10. **Pantallas y tiempos (FR-051, SC-001, SC-011)**:
    - Recorrer `/caja`, `/vender`, `/ventas` y Pendientes en un teléfono de 360 px y en
      PC: sin desplazamiento horizontal, montos `1.234,56` y fechas `dd/mm/aaaa`.
    - Medir que una venta de 3 a 5 productos con un tramo en cm y pago mixto toma
      menos de 1 minuto (SC-001).
    - Medir que un descuento por PIN se aplica en menos de 15 s (SC-011).

## Cierre de la etapa

- `docs/modelo-de-datos.md` (cambios listados en `data-model.md`),
  `docs/arquitectura.md` (flujo 3.1 con la cola real, servicios de ventas, caja,
  equipos y descuentos, matriz por endpoint, glosario), ADR-0003 (preguntas
  resueltas), ADR-0004 (ruta de los casos compartidos), `docs/guia-de-estilos.md`
  (pantalla de venta) y `CHANGELOG.md` actualizados (RNF-09).
- Restauración del respaldo probada en local (plan de fases, definición de terminado).
- La etapa cierra como versión `0.4.0`. Las ventas reales empiezan con la 1.5 (plan de
  fases §3).
