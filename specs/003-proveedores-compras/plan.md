# Implementation Plan: Proveedores, compras con gastos y tasa BCV (etapa 1.2)

**Branch**: `003-proveedores-compras` | **Date**: 2026-10-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-proveedores-compras/spec.md`

## Summary

Proveedores, compras y tasa BCV (RF-13 a RF-17, RN-03, RN-05, RN-09, RN-14, RN-15,
RN-20). Lo que entrega la etapa:

- **Proveedores** con RIF normalizado y único.
- **Tasa BCV adelantada de la 1.3:** carga y corrección auditada, histórico y tasa
  aplicable por fecha.
- **Gastos frecuentes**, que mantiene el Admin.
- **Compras en USD o Bs** que se guardan en borrador como un documento completo. El
  servidor recalcula todo con un módulo de dominio puro (`costing.py`):
  - gastos por porcentaje o monto fijo;
  - reparto por valor;
  - costo final por unidad;
  - promedio ponderado.
- **Confirmación** en una transacción: bloquea la compra y los productos en orden,
  genera los movimientos de kardex con el costo antes y después, bloquea el costo
  inicial y asigna un número sin huecos.
- **Inmutabilidad en la base:** los triggers impiden cambiar una compra confirmada, sus
  líneas y sus gastos.
- **Anulación** solo del Admin, con vista previa. Deshace el costo con el costo final
  y, si el resultado no es válido, conserva el costo y crea una alerta.
- **Fuga de costos:** el Almacén ve los costos de las compras, pero nunca el costo
  promedio.
- **Pantallas nuevas:** compras, proveedores, tasa BCV y gastos frecuentes.

Decisiones en [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.14 (backend); TypeScript con React 19 y Next.js 16 (frontend), igual que la 1.1b

**Primary Dependencies**: las existentes (FastAPI, SQLAlchemy 2, Alembic, psycopg 3; Next.js, Tailwind CSS v4, lucide-react, openapi-typescript). Ninguna nueva

**Storage**: PostgreSQL 17 (Supabase en producción, Docker en local). Migración `0005_proveedores_y_compras`: 8 tablas nuevas, triggers y la fila inicial de `sequence_counter`

**Testing**: pytest con `TestClient` y Postgres (marca `db`); pruebas de dominio sin base de datos con casos compartidos en JSON (R1); ruff; `tsc` y build de Next.js

**Target Platform**: API en Cloud Run (Linux); app estática en Cloudflare Pages, navegadores de PC, tablet y teléfono

**Project Type**: aplicación web (API + SPA estática) en monorepo

**Performance Goals**: confirmar una compra de 200 líneas en < 5 s (R13); 20 confirmaciones simultáneas sin números repetidos ni costos distintos al cálculo en serie (SC-006); compra de 10 líneas en < 5 min (SC-003)

**Constraints**:
- planes gratuitos (RNF-03), sin servicios nuevos;
- compras solo con conexión;
- decimales como cadenas y redondeo mitad hacia arriba en un único módulo (ADR-0004);
- export estático sin rutas dinámicas (R11);
- interfaz en español, `1.234,56`, `dd/mm/aaaa`, `America/Caracas`.

**Scale/Scope**:
- datos: ~1.000 productos, decenas de compras al mes, compras de hasta 500 líneas y 20
  gastos;
- API: 21 endpoints nuevos y 2 ampliados;
- interfaz: 6 pantallas nuevas y la de pendientes ampliada.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Puerta | Evaluación | Resultado |
|---|---|---|---|
| 1 | Decimales exactos y tasa de la operación (I) | Dominios de ADR-0004 en todas las columnas; `Decimal` y cadenas en JSON; redondeo solo en `costing.py` y `money.py` (R1). Cada compra copia la tasa y su fecha (R6) y queda inmutable al confirmarse; corregir una tasa no la altera (SC-009). Promedio ponderado al confirmar (RN-09) con el costo final (RN-20) | ✅ |
| 2 | Kardex e inmutabilidad (II) | Entradas y reversos solo por `post_movement`; triggers sobre `purchase`, `purchase_item`, `purchase_charge` y `purchase_void` (R2); anulación solo con movimientos nuevos; auditoría en la misma transacción (R12) | ✅ |
| 3 | Ventas sin conexión sin duplicar (III) | No toca ventas. El reverso por anulación admite stock negativo (RN-10). La tabla de tasas queda lista para la copia local de la 1.5 | ✅ No aplica |
| 4 | Permisos en el servidor, sin costos filtrados (IV) | Matriz por endpoint (contrato); el Vendedor sin acceso; el Almacén recibe costos de factura, gastos y costo final (excepción de la constitución 1.2.0), nunca el costo promedio ni el costo antes y después (R7); `test_no_cost_leak.py` ampliado | ✅ |
| 5 | Alcance de la fase y respaldo del PRD (V) | RF-13 a RF-17 y RN-20 en el PRD v0.9; adelantar la tasa está en el plan de fases. Fuera: reparto por peso, gastos después de confirmar, embarques y cuentas por pagar (§5.4) | ✅ |
| 6 | Presupuesto y simplicidad (VI) | Sin servicios ni dependencias nuevas. Un único calculador en el servidor (R4) en lugar de duplicarlo en TypeScript; correlativo con una fila de contador (R3); alertas con la tabla ya prevista en el modelo (R8) | ✅ |
| 7 | Pruebas de las reglas críticas (VII) | Costo promedio, reparto y costo final con casos compartidos; kardex y reversos; inmutabilidad por SQL directo; concurrencia; permisos y fuga de costos (quickstart, tabla de pruebas) | ✅ |

**Re-evaluación tras el diseño (fase 1):** sin cambios. Ajustes de documentación que no
contradicen ninguna puerta, a reflejar en `docs/modelo-de-datos.md` al cerrar la etapa
(lista en [data-model.md](data-model.md)):

- `purchase.status` suma `voided`;
- el número de compra se asigna al confirmar;
- nuevas `sequence_counter` y `alert`;
- `exchange_rate.updated_by`.

Ninguna puerta requiere justificación en "Complexity Tracking".

## Project Structure

### Documentation (this feature)

```text
specs/003-proveedores-compras/
├── plan.md              # Este archivo
├── research.md          # Fase 0: decisiones R1–R13
├── data-model.md        # Fase 1: tablas, estados y triggers
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
│   ├── main.py                    # registrar routers nuevos
│   ├── domain/
│   │   ├── money.py               # + round_usd, round_cost, ves_to_usd_cost (ROUND_HALF_UP)
│   │   ├── costing.py             # gastos, reparto, costo final, promedio y deshacer (R1)
│   │   └── rif.py                 # normalize_rif (R5)
│   ├── db/models.py               # Supplier, ExchangeRate, ChargeTemplate, Purchase,
│   │                              # PurchaseItem, PurchaseCharge, PurchaseVoid, Alert,
│   │                              # SequenceCounter
│   ├── services/
│   │   ├── inventory.py           # post_movement + cost_before_usd/cost_after_usd; resumen ampliado
│   │   ├── suppliers.py
│   │   ├── exchange_rates.py      # carga, corrección, applicable_rate (R6)
│   │   ├── charge_templates.py
│   │   ├── purchases.py           # borrador, confirmar, anular, vista previa (R3, R4, R10)
│   │   └── alerts.py              # crear y resolver (R8)
│   └── api/
│       ├── purchase_schemas.py    # Purchase, PurchaseInput, resúmenes, cost_changes solo Admin
│       ├── suppliers.py           # /suppliers
│       ├── exchange_rates.py      # /exchange-rates
│       ├── charge_templates.py    # /charge-templates
│       ├── purchases.py           # /purchases
│       ├── alerts.py              # /alerts
│       └── product_schemas.py     # movimiento con enlace a la compra (FR-021)
├── migrations/versions/0005_proveedores_y_compras.py
└── tests/
    ├── cases/costing_cases.json
    ├── test_costing_domain.py, test_rif_domain.py
    ├── test_suppliers.py, test_exchange_rates.py, test_charge_templates.py
    ├── test_purchases_draft.py, test_purchases_confirm.py, test_purchases_concurrency.py
    ├── test_purchase_void.py, test_purchase_immutability.py, test_alerts.py
    ├── test_no_cost_leak.py       # + compras, confirmación y kardex de compras
    ├── test_permissions_matrix.py # + filas del contrato
    └── test_audit.py              # + acciones de R12

frontend/src/
├── app/
│   ├── compras/page.tsx           # lista con filtros
│   ├── compras/editar/page.tsx    # ?id=: borrador con líneas, gastos y totales
│   ├── compras/detalle/page.tsx   # ?id=: confirmada o anulada; anular (Admin)
│   ├── proveedores/page.tsx
│   ├── tasas/page.tsx             # Admin
│   ├── configuracion/gastos/page.tsx   # Admin
│   ├── pendientes/page.tsx        # + alertas
│   └── page.tsx                   # + tarjetas de borradores y alertas
├── components/
│   ├── app-shell.tsx              # + Compras, Proveedores, Tasa BCV
│   └── purchases/                 # tabla de líneas, sección de gastos, totales, diálogo de anulación
└── (buscador de productos de components/products, reutilizado)

packages/shared/src/
├── api/schema.d.ts                # regenerado
├── format.ts                      # + formatVes, formatRate, formatPercent
└── audit-actions.ts               # + grupo "Compras y tasas" (R12)
```

**Structure Decision**:

- Se mantiene el monorepo y la regla de dependencias del backend `api → services →
  domain`, `services → db` (`docs/arquitectura.md` §2).
- Los cálculos de dinero de la etapa van en `domain/costing.py` para probarse sin base
  de datos con casos compartidos.
- La tasa vive en su propio servicio, que reutilizará la 1.3.
- El catálogo público y el mostrador no cambian en esta etapa.

## Complexity Tracking

Sin violaciones de la constitución que justificar.
