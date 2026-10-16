# Implementation Plan: Caja: egresos, cierre y cuadre (etapa 1.4)

**Branch**: `005-cierre-caja` | **Date**: 2026-10-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/005-cierre-caja/spec.md`

## Summary

Caja del mostrador de la apertura al cierre (RF-27, RF-31 a RF-33, RN-12, RN-16). Lo que
entrega la etapa:

- **Esperado por método** idéntico en el equipo y en el servidor:
  `domain/cash_math.py` y `packages/shared/src/cash.ts`, con los mismos casos en JSON
  (R1).
- **Egresos** en efectivo con motivo, por la cola de salida, con tope en el efectivo
  esperado y sin autorización. Solo el Admin los anula, y solo con la caja abierta (R3).
- **Cierre** por la cola desde el equipo de la caja: contado o verificado por método,
  diferencias, observación obligatoria con diferencias, recálculo en el servidor y
  alertas (R4).
- **Cierre del Admin** de una caja de otro equipo o de un equipo revocado (R6).
  Operaciones creadas antes de ese cierre se registran igual, con alerta (R7).
- **Anulación con la caja cerrada**: la devolución va a la caja abierta del equipo desde
  el que anula el Admin y el cierre original no cambia (R8).
- **Inmutabilidad en la base**: caja cerrada, `cash_count` y egresos, con triggers (R2).
- **Consulta de cajas**: el Admin ve todas con filtros; el Vendedor, la caja abierta de
  su equipo y sus cierres de hoy (R9).

Decisiones en [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.14 (backend); TypeScript con React 19 y Next.js 16 (frontend), igual que la 1.3

**Primary Dependencies**: las existentes (FastAPI, SQLAlchemy 2, Alembic, psycopg 3; Next.js, Tailwind CSS v4, lucide-react, openapi-typescript, `decimal.js`, `dexie`). Sin dependencias nuevas

**Storage**:
- PostgreSQL 17. La migración `0007_cierre_de_caja`:
  - amplía `cash_session` con las columnas de cierre;
  - crea `cash_outflow` y `cash_count`;
  - agrega los triggers de inmutabilidad y tres tipos de alerta.
- IndexedDB en el equipo: la cola de salida suma dos tipos de operación, sin cambiar el
  esquema local.

**Testing**:
- pytest con `TestClient` y Postgres (marca `db`);
- pruebas de dominio sin base con casos compartidos (`cash.json`);
- `node --test` para `cash.ts`, con los mismos casos;
- ruff, `tsc` y el build de Next.js.

**Target Platform**: API en Cloud Run (Linux); app estática en Cloudflare Pages, para navegadores de PC, tablet y teléfono

**Project Type**: aplicación web (API + SPA estática) en monorepo

**Performance Goals**:
- cierre de un día de prueba en < 10 min (SC-001);
- detalle de una caja con 100 ventas en < 1 s (R14);
- 10 reenvíos del mismo egreso o cierre dejan uno (SC-004).

**Constraints**:
- planes gratuitos (RNF-03), sin servicios nuevos;
- en esta etapa el cierre funciona con conexión, pero egresos y cierre viajan por la cola
  para la 1.5;
- decimales como cadenas y mitad hacia arriba (ADR-0004);
- export estático sin rutas dinámicas;
- `1.234,56`, `dd/mm/aaaa` y `America/Caracas`.

**Scale/Scope**:
- datos: 1–2 equipos, una o dos cajas al día, decenas de ventas y unos pocos egresos por
  caja;
- API: 4 endpoints nuevos (`GET /cash-sessions`, `GET /cash-sessions/{id}`,
  `POST /cash-sessions/{id}/close`, `POST /cash-outflows/{id}/void`), 2 tipos de
  operación de cola y 4 endpoints ampliados (`POST /sales/{id}/void`, `GET /alerts`,
  `GET /devices/current`, `sale.create`);
- interfaz: Caja ampliada, 3 pantallas nuevas (cierre, Cajas y su detalle), diálogo de
  anulación y Pendientes ampliados.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Puerta | Evaluación | Resultado |
|---|---|---|---|
| 1 | Decimales exactos y tasa de la operación (I) | Montos `numeric(16, 2)` en la moneda de cada método; `Decimal` y `decimal.js` en un módulo puro por lado con los mismos casos (R1). El cuadre no convierte monedas ni usa la tasa del día: cada método se cuadra en su moneda y los pagos conservan su tasa (RN-05) | ✅ |
| 2 | Kardex e inmutabilidad (II) | Sin cambios de stock nuevos: la anulación reutiliza `post_movement` (1.3). Caja cerrada, `cash_count` y egresos protegidos con triggers, también ante SQL directo; correcciones solo con movimientos nuevos: anulación de egreso con la caja abierta, egreso nuevo, devolución en la caja abierta (R2, R3, R8; RF-33, RN-12). Auditoría en la misma transacción (R12) | ✅ |
| 3 | Ventas sin conexión sin duplicar (III) | Egreso y cierre viajan por la cola con UUIDv7 e idempotencia de la 1.3 (R3, R4). El esperado se calcula igual en el equipo (R1), listo para la 1.5. Una venta creada antes de un cierre hecho en otro lugar se registra con alerta, nunca se pierde (R7). El modo sin conexión completo sigue en la 1.5, como fija el plan de fases | ✅ |
| 4 | Permisos en el servidor, sin costos filtrados (IV) | Matriz por endpoint y operación (R10, contrato); el Vendedor limitado a la caja de su equipo y sus cierres de hoy en el servidor (R9); Almacén sin acceso; la caja no contiene costos y `test_no_cost_leak.py` se amplía | ✅ |
| 5 | Alcance de la fase y respaldo del PRD (V) | RF-27 (PRD v0.11), RF-31 a RF-33, RN-12, RN-16; decisiones de `/speckit-clarify` dentro del PRD (RF-32 solo egresos). Fuera: ingresos o cambios de moneda en la gaveta (Clarifications), reporte de ventas por método (RF-39, etapa 1.7), impresión del cierre (Fase 2), modo sin conexión (1.5) | ✅ |
| 6 | Presupuesto y simplicidad (VI) | Sin servicios ni dependencias nuevas. Dos tablas y columnas en `cash_session`; reutiliza la cola, el espejo de pagos y las alertas. El cierre del Admin es un endpoint directo y no pasa por la cola (R6). Sin categorías de egreso ni cierre automático | ✅ |
| 7 | Pruebas de las reglas críticas (VII) | Cuadre de caja con casos compartidos en las dos suites (R1); idempotencia del egreso y del cierre; inmutabilidad en la base; permisos por rol; anulación con la caja cerrada (quickstart, tabla de pruebas) | ✅ |

**Re-evaluación tras el diseño (fase 1):** sin cambios. Ajustes de documentación que no
contradicen ninguna puerta y se reflejan al cerrar la etapa (lista en
[data-model.md](data-model.md) y en el quickstart):

- `cash_outflow` y `cash_count` usan `payment_method_code` en lugar de
  `payment_method_id` (la clave del catálogo es `code` desde la 1.3);
- `cash_count` suma `device_expected_amount`;
- la devolución de una anulación puede ir a otra caja, deducida de `payment`;
- ADR-0003 suma los tipos de operación de la caja.

Ninguna puerta requiere justificación en "Complexity Tracking".

## Project Structure

### Documentation (this feature)

```text
specs/005-cierre-caja/
├── plan.md              # Este archivo
├── research.md          # Fase 0: decisiones R1–R14
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
│   │   └── cash_math.py            # compute_reconciliation: esperado y diferencias (R1)
│   ├── db/models.py                # CashSession (cierre), CashOutflow, CashCount
│   ├── services/
│   │   ├── cash_sessions.py        # + cierre por la cola y del Admin, consulta, detalle (R4, R6, R9)
│   │   ├── cash_outflows.py        # registrar y anular egresos (R3)
│   │   ├── sales.py                # venta tardía en caja cerrada (R7); devolución en otra caja (R8)
│   │   └── alerts.py               # create_cash_session_alert y tipos nuevos (R11)
│   └── api/
│       ├── cash_schemas.py         # CashSessionSummary, CashSessionDetail, ReconciliationRow, CashOutflow
│       ├── cash_sessions.py        # /cash-sessions
│       ├── cash_outflows.py        # /cash-outflows/{id}/void
│       ├── sync.py                 # + cash_outflow.create y cash_session.close
│       ├── sales.py                # void con X-Device-Token opcional
│       ├── sale_schemas.py         # void.refund_cash_session; Device.open_cash_session ampliado
│       └── alerts.py               # enlace a la caja
├── migrations/versions/0007_cierre_de_caja.py
└── tests/
    ├── test_cash_math.py           # lee packages/shared/test-vectors/cash.json
    ├── test_cash_outflows.py, test_cash_close.py, test_cash_close_admin.py
    ├── test_sale_void_closed_session.py, test_cash_immutability.py
    ├── test_cash_sessions_list.py, test_cash_performance.py
    ├── test_no_cost_leak.py        # + caja
    ├── test_permissions_matrix.py  # + filas del contrato
    └── test_audit.py               # + acciones de R12

packages/shared/
├── test-vectors/cash.json          # casos compartidos del cuadre (R1)
└── src/
    ├── cash.ts, cash.test.ts       # computeReconciliation (R1)
    ├── index.ts                    # exporta cash
    ├── api/schema.d.ts             # regenerado
    └── audit-actions.ts            # + acciones de caja (R12)

frontend/src/
├── lib/
│   ├── cash.ts                     # detalle de la caja, cuadre, egreso y cierre por la cola
│   └── outbox/outbox.ts            # waitsForOwner incluye egreso y cierre; pendientes por caja
├── app/
│   ├── caja/page.tsx               # caja abierta con esperado, egresos, cierre y aviso de otro día
│   ├── caja/cierre/page.tsx        # conteo por método, diferencias y observación (R4)
│   ├── cajas/page.tsx              # Admin: consulta con filtros
│   ├── cajas/detalle/page.tsx      # ?id=: detalle, anular egreso, cerrar desde otro equipo
│   ├── pendientes/page.tsx         # + alertas de caja
│   └── vender/page.tsx             # aviso de caja abierta desde otro día
└── components/
    ├── app-shell.tsx               # + Cajas (Admin)
    ├── cash/                       # tabla del cuadre, diálogo de egreso, lista de movimientos
    └── sales/void-sale-dialog.tsx  # caja que recibe la devolución (R8)
```

**Structure Decision**:

- Se mantienen el monorepo y la regla de dependencias del backend: `api → services →
  domain` y `services → db` (`docs/arquitectura.md` §2).
- El cuadre es dominio puro en los dos lados, con un solo archivo de casos, como el
  cálculo de la venta.
- Los egresos tienen su propio servicio. El cierre y la consulta amplían
  `cash_sessions.py`, que ya tiene la apertura.
- El catálogo público no cambia en esta etapa.

## Complexity Tracking

Sin violaciones de la constitución que justificar.
