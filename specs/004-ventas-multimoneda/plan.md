# Implementation Plan: Ventas multimoneda, pagos mixtos, descuentos y apertura de caja (etapa 1.3)

**Branch**: `004-ventas-multimoneda` | **Date**: 2026-10-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/004-ventas-multimoneda/spec.md`

## Summary

Ventas en el mostrador (RF-18, RF-20 a RF-30, RN-01 a RN-07, RN-10, RN-11, RN-16). Lo
que entrega la etapa:

- **Equipos de mostrador** con serie (`A`, `B`…) que nunca se reutiliza y token propio
  (R3).
- **Apertura de caja** con fondo en Bs y USD, una abierta por equipo, adelantada de la
  1.4 (R7).
- **Cálculo de la venta** idéntico en el equipo y en el servidor:
  `domain/sale_math.py` y `packages/shared/src/money.ts`, con los mismos casos en JSON
  (R1).
- **Cola de salida real** (IndexedDB con Dexie) e idempotencia en
  `POST /sync/operations`. La venta ya tiene la forma que necesita la 1.5 (R4).
- **Venta** con cm→m, totales en USD y Bs, cliente opcional y pagos mixtos con vuelto.
  El servidor recalcula y, en una transacción, registra la venta, los pagos, las
  salidas de kardex, las alertas y la auditoría. Nunca rechaza una venta por razones
  de negocio: las registra con alerta (R4, R6).
- **Descuentos** por ítem o total, con autorización por PIN o solicitud ligada a la
  línea y al valor. Sin autorización válida, la venta va a revisión (R8).
- **Anulación** solo del Admin: reversos de kardex y espejo de cada pago (R10).
- **Inmutabilidad en la base** con triggers (R9).
- **Consulta de ventas**: el Vendedor solo ve las suyas de hoy y sin costos (R12).

Decisiones en [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.14 (backend); TypeScript con React 19 y Next.js 16 (frontend), igual que la 1.2

**Primary Dependencies**:
- Las existentes: FastAPI, SQLAlchemy 2, Alembic y psycopg 3; Next.js, Tailwind CSS v4, lucide-react y openapi-typescript.
- Nuevas, ya decididas en ADR-0003 y ADR-0004:
  - `decimal.js`, en `packages/shared`;
  - `dexie`, en `frontend`.

**Storage**:
- PostgreSQL 17. La migración `0006_ventas_y_caja` crea 10 tablas, triggers, el catálogo de métodos de pago, la fila `device_series` y las FK de `device_id`.
- IndexedDB en el equipo: identidad del equipo, contador de ventas y cola de salida.

**Testing**:
- pytest con `TestClient` y Postgres (marca `db`);
- pruebas de dominio sin base de datos con casos compartidos;
- `node --test` para `money.ts`, con los mismos casos (R2);
- ruff, `tsc` y el build de Next.js.

**Target Platform**: API en Cloud Run (Linux); app estática en Cloudflare Pages, para navegadores de PC, tablet y teléfono

**Project Type**: aplicación web (API + SPA estática) en monorepo

**Performance Goals**:
- venta típica en < 1 min (SC-001);
- búsqueda en < 1 s (SC-002);
- registro de una venta de 20 líneas en < 1 s;
- 10 reenvíos simultáneos dejan una venta (SC-004);
- 2 equipos × 50 ventas en paralelo sin números repetidos (SC-005);
- PIN aplicado en < 15 s (SC-011).

**Constraints**:
- planes gratuitos (RNF-03), sin servicios nuevos;
- espera de autorizaciones por consulta periódica, sin WebSockets;
- en esta etapa la venta funciona con conexión; la copia local y el modo sin conexión son de la 1.5;
- decimales como cadenas y mitad hacia arriba (ADR-0004);
- export estático sin rutas dinámicas;
- `1.234,56`, `dd/mm/aaaa` y `America/Caracas`.

**Scale/Scope**:
- datos: ~1.000 productos, 1–2 equipos, decenas de ventas al día, hasta 100 líneas, 10 pagos y 5 vueltos por venta;
- API: 14 endpoints nuevos y 4 ampliados;
- interfaz: 5 pantallas nuevas y Pendientes ampliada.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Puerta | Evaluación | Resultado |
|---|---|---|---|
| 1 | Decimales exactos y tasa de la operación (I) | Dominios de ADR-0004 en todas las columnas; `Decimal` y `decimal.js` con mitad hacia arriba en un único módulo por lado, con los mismos casos (R1). La venta y cada pago copian la tasa y su fecha, enviadas por el equipo (RN-05). cm→m antes de precio y stock | ✅ |
| 2 | Kardex e inmutabilidad (II) | Salidas y reversos solo por `post_movement` (`allow_negative` para ventas, RN-10); triggers sobre `sale`, `sale_item`, `payment` y `sale_void` (R9); anulación solo con movimientos y pagos nuevos (R10); descuentos con su autorizante (R8) y auditoría en la misma transacción (R15) | ✅ |
| 3 | Ventas sin conexión sin duplicar (III) | Toda venta y apertura pasa por la cola de salida con UUIDv7 del equipo; idempotencia por clave primaria con resultado guardado (R4); numeración por serie única por equipo (R5); el servidor nunca rechaza por negocio, registra y alerta (R6). La copia local y la sesión sin conexión quedan para la 1.5, como fija el plan de fases: la 1.3 no se usa para ventas reales (plan de fases §3) y el modo sin conexión completo es requisito de la 1.5 antes de vender en el mostrador | ✅ |
| 4 | Permisos en el servidor, sin costos filtrados (IV) | Matriz por endpoint (contrato) y token de equipo; el vendedor de la venta es el usuario de la sesión (R17); tasa distinta de la cargada con alerta (R6); `SaleSeller` sin costos ni márgenes; Vendedor limitado a sus ventas de hoy en el servidor (R12); Almacén sin acceso a ventas ni caja; PIN validado en el servidor y nunca en la cola (R8); `test_no_cost_leak.py` ampliado | ✅ |
| 5 | Alcance de la fase y respaldo del PRD (V) | RF-18, RF-20 a RF-30, RN-07 y RN-10 en el PRD v0.10. La apertura de caja adelantada está en el plan de fases. Fuera: cierre, egresos y cuadre (1.4), modo sin conexión (1.5), crédito y nota de entrega (Fase 2), IVA e IGTF (Fase 3; el modelo los permite) | ✅ |
| 6 | Presupuesto y simplicidad (VI) | Sin servicios nuevos. Dos dependencias pequeñas ya previstas en ADR. Consulta periódica en lugar de WebSockets; una tabla para PIN y solicitudes (R8); espejo de pagos para la anulación (R10); `node --test` en lugar de un framework de pruebas (R2) | ✅ |
| 7 | Pruebas de las reglas críticas (VII) | Conversión y redondeo USD↔Bs, pagos mixtos, vuelto y cm→m con casos compartidos en las dos suites; kardex y reversos; idempotencia y numeración concurrentes; permisos y fuga de costos (quickstart, tabla de pruebas) | ✅ |

**Re-evaluación tras el diseño (fase 1):** sin cambios. Ajustes de documentación que no
contradicen ninguna puerta; se reflejan al cerrar la etapa (lista en
[data-model.md](data-model.md) y en el quickstart):

- `payment_method` usa `code` como clave;
- una tabla `discount_authorization` reemplaza a `discount_request`;
- `payment.kind` suma `void_change`;
- `outbox_operation.status` usa `rejected` en lugar de `failed`;
- se corrige la ruta de los casos compartidos en ADR-0004;
- se cierran las preguntas pendientes de ADR-0003.

Ninguna puerta requiere justificación en "Complexity Tracking".

## Project Structure

### Documentation (this feature)

```text
specs/004-ventas-multimoneda/
├── plan.md              # Este archivo
├── research.md          # Fase 0: decisiones R1–R17
├── data-model.md        # Fase 1: tablas, reglas y triggers
├── quickstart.md        # Fase 1: guía de validación
├── contracts/
│   └── api.md           # Fase 1: endpoints, esquemas y matriz de permisos
├── checklists/
│   └── requirements.md  # Calidad de la especificación
└── tasks.md             # Fase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── main.py                     # registrar routers nuevos
│   ├── domain/
│   │   ├── money.py                # + validate_usd_discount, ves_to_usd, usd_to_ves
│   │   ├── sale_math.py            # compute_sale: líneas, descuentos, reparto, totales, pagos, vuelto (R1)
│   │   ├── customer_document.py    # cédula o RIF normalizado (R11)
│   │   └── series.py               # número → serie de letras (R3)
│   ├── db/models.py                # Device, CashSession, Customer, PaymentMethod, Sale, SaleItem,
│   │                               # Payment, SaleVoid, DiscountAuthorization, OutboxOperation
│   ├── services/
│   │   ├── devices.py              # registrar, revocar, autenticar por token (R3)
│   │   ├── sync.py                 # idempotencia y despacho de operaciones (R4)
│   │   ├── cash_sessions.py        # apertura (R7)
│   │   ├── sales.py                # registrar, anular, consultar (R5, R6, R10, R12)
│   │   ├── discounts.py            # autorizaciones por PIN y solicitud (R8)
│   │   ├── customers.py            # búsqueda y alta desde la venta (R11)
│   │   └── alerts.py               # tipos nuevos (R6)
│   └── api/
│       ├── deps.py                 # + CurrentDevice (cabecera X-Device-Token)
│       ├── sale_schemas.py         # SaleInput, SaleSeller, SaleAdmin, CashSession, Device
│       ├── devices.py              # /devices
│       ├── sync.py                 # /sync/operations
│       ├── customers.py            # /customers
│       ├── discount_authorizations.py
│       ├── sales.py                # /sales
│       ├── exchange_rates.py       # applicable abierto al Vendedor
│       └── product_schemas.py      # movimiento con enlace a la venta (FR-048)
├── migrations/versions/0006_ventas_y_caja.py
└── tests/
    ├── test_sale_math.py           # lee packages/shared/test-vectors/money.json
    ├── test_devices.py, test_cash_sessions.py, test_sync_idempotency.py
    ├── test_sales_create.py, test_sales_alerts.py, test_sales_numbering.py
    ├── test_discounts.py, test_sale_void.py, test_sale_immutability.py
    ├── test_sales_list.py, test_sales_performance.py
    ├── test_no_cost_leak.py        # + ventas
    ├── test_permissions_matrix.py  # + filas del contrato
    └── test_audit.py               # + acciones de R15

packages/shared/
├── package.json                    # + decimal.js; script test (node --test)
├── test-vectors/money.json         # casos compartidos (R1)
└── src/
    ├── money.ts, money.test.ts     # computeSale, cmToMeters, validateQuantity (R1, R2)
    ├── uuid.ts                     # uuidv7() (R4)
    ├── api/schema.d.ts             # regenerado
    └── audit-actions.ts            # + grupo "Ventas y caja" (R15)

frontend/src/
├── lib/
│   ├── device/device-store.ts      # identidad, token y contador en IndexedDB (Dexie)
│   ├── outbox/outbox.ts            # cola de salida, envío en orden y reintentos (R4)
│   └── sales.ts                    # armado de la venta y llamadas
├── app/
│   ├── caja/page.tsx               # equipo y apertura de caja
│   ├── vender/page.tsx             # pantalla de venta
│   ├── ventas/page.tsx             # consulta
│   ├── ventas/detalle/page.tsx     # ?id=: detalle y anulación (Admin)
│   ├── configuracion/equipos/page.tsx   # Admin
│   ├── pendientes/page.tsx         # + solicitudes de descuento y alertas de venta
│   └── page.tsx                    # + accesos a Vender y Caja
└── components/
    ├── app-shell.tsx               # + Vender, Ventas, Caja; indicador de pendientes de envío
    └── sales/                      # líneas, descuentos, pagos y vuelto, totales, PIN, cliente, anulación
```

**Structure Decision**:

- Se mantienen el monorepo y la regla de dependencias del backend: `api → services →
  domain` y `services → db` (`docs/arquitectura.md` §2).
- El cálculo de la venta es dominio puro en los dos lados, con un solo archivo de
  casos.
- La identidad del equipo y la cola viven en `frontend/src/lib`. La 1.5 les suma el
  service worker y la copia local sin moverlas.
- El catálogo público no cambia en esta etapa.

## Complexity Tracking

Sin violaciones de la constitución que justificar.
