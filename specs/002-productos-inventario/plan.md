# Implementation Plan: Productos, categorías e inventario (etapa 1.1b)

**Branch**: `002-productos-inventario` | **Date**: 2026-10-08 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-productos-inventario/spec.md`

## Summary

Catálogo interno de productos e inventario con kardex (RF-01 a RF-12, RN-08, RN-09
costo inicial, RN-13, RN-18, RN-19). La API suma unidades, categorías con prefijo de SKU
y atributos configurables, productos con SKU automático por bloqueo de fila, precio con
historial y costo inicial solo para el Admin, fotos normalizadas a WebP en Supabase
Storage, búsqueda normalizada sin acentos, kardex de solo inserción impuesto con
triggers, ajustes con motivo (los negativos del Almacén esperan la aprobación del
Admin) y conteos físicos a ciegas que solo el Admin aplica. Las respuestas usan
esquemas por rol: el Vendedor no recibe costos ni el kardex y el Almacén no recibe
precio ni costo. La app interna suma las pantallas de productos, ficha, ajustes,
pendientes, conteos, stock bajo y configuración. Decisiones en [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.14 (backend); TypeScript 7 con React 19 y Next.js 16 (frontend)

**Primary Dependencies**: existentes (FastAPI, SQLAlchemy 2, Alembic, psycopg 3, argon2-cffi, PyJWT; Next.js, Tailwind CSS v4, lucide-react, openapi-typescript). Nuevas: `pillow` (normalizar fotos, R9), `httpx` (API de Supabase Storage, R9) y `python-multipart` (subida de fotos) en el backend; ninguna en el frontend

**Storage**: PostgreSQL 17 (Supabase en producción, Docker en local), migración `0004_productos_e_inventario` con datos iniciales; Supabase Storage, bucket público `product-photos` (disco local en desarrollo y pruebas)

**Testing**: pytest con `TestClient` y Postgres (marca `db`), pruebas de dominio sin base de datos; ruff; `tsc` y build de Next.js

**Target Platform**: API en Cloud Run (Linux); app estática en Cloudflare Pages, navegadores modernos de PC, tablet y teléfono

**Project Type**: aplicación web (API + SPA estática) en monorepo

**Performance Goals**: búsqueda < 1 s de punta a punta con 1.000 productos (SC-001), < 200 ms en el servidor; alta de producto < 1 min (SC-002); 20 altas simultáneas sin SKU repetido (SC-006)

**Constraints**: planes gratuitos (RNF-03): fotos ~100–200 KB en WebP para caber en 1 GB de Storage; sin extensiones de Postgres nuevas; export estático sin rutas dinámicas (R13); decimales como cadenas (ADR-0004); interfaz en español, `1.234,56`, `dd/mm/aaaa`, `America/Caracas`

**Scale/Scope**: ~1.000 productos, 4 categorías iniciales, < 10 usuarios; 35 endpoints nuevos; 11 pantallas nuevas y el inicio ampliado

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Puerta | Evaluación | Resultado |
|---|---|---|---|
| 1 | Decimales exactos y tasa de la operación (I) | Precio (`usd_amount`), costo (`usd_cost`) y cantidades (`quantity`) con los dominios de ADR-0004, `Decimal` en Python y cadenas en JSON; validación de decimales por unidad sin redondear (R3). No hay operaciones con tasa en esta etapa | ✅ |
| 2 | Kardex e inmutabilidad (II) | Stock solo por `post_movement`; triggers que verifican el saldo, actualizan el stock y rechazan su escritura directa; `stock_movement` y `product_price` de solo inserción; conteos y solicitudes inmutables al cerrarse; auditoría en la misma transacción (R2, R7, R8, R14) | ✅ |
| 3 | Ventas sin conexión sin duplicar (III) | No toca ventas. El stock negativo queda permitido en el modelo (RN-10) y la normalización de búsqueda se replicará en TypeScript para el mostrador sin conexión (R4) | ✅ No aplica |
| 4 | Permisos en el servidor, sin costos filtrados (IV) | Matriz por endpoint en `test_permissions_matrix.py`; esquemas por rol sin campos de costo (ni de precio para Almacén); prueba transversal `test_no_cost_leak.py`; conteo a ciegas por esquema; la clave de Storage solo en el servidor (R6, R8, R9) | ✅ |
| 5 | Alcance de la fase y respaldo del PRD (V) | RF-01 a RF-12 de la Fase 1; las aclaraciones ya están en el PRD v0.8 (RN-09, RN-18, RN-19, matriz). Sin kits (RN-13). Compras, ventas y catálogo público quedan en 1.2, 1.3 y 1.6. El modelo permite IVA por producto y listas de precios futuras | ✅ |
| 6 | Presupuesto y simplicidad (VI) | Sin servicios pagos; fotos dentro de Supabase Free con el criterio de ADR-0002; respaldo de fotos dentro del nivel gratuito de Cloud Storage; búsqueda sin extensiones ni motor externo (R4); tres dependencias de Python conocidas | ✅ |
| 7 | Pruebas de las reglas críticas (VII) | Kardex y reversos (saldo, inmutabilidad, trigger), validación de unidades, permisos por rol y fuga de costos con pruebas automatizadas que citan FR/RN (quickstart, tabla de pruebas) | ✅ |

**Re-evaluación tras el diseño (fase 1):** sin cambios. Dos ajustes de documentación que
no contradicen ninguna puerta: la búsqueda pasa de `tsvector` + trigram a texto
normalizado (R4) y se agrega `adjustment_request` al modelo (R7); ambos se reflejan en
`docs/modelo-de-datos.md` y `docs/arquitectura.md` al cerrar la etapa. Ninguna puerta
requiere justificación en "Complexity Tracking".

## Project Structure

### Documentation (this feature)

```text
specs/002-productos-inventario/
├── plan.md              # Este archivo
├── research.md          # Fase 0: decisiones R1–R16
├── data-model.md        # Fase 1: tablas, estados y triggers
├── quickstart.md        # Fase 1: guía de validación
├── contracts/
│   └── api.md           # Fase 1: endpoints, esquemas por rol y matriz de permisos
├── checklists/
│   └── requirements.md  # Calidad de la especificación
└── tasks.md             # Fase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── main.py                    # registrar routers nuevos; /media solo en local (R9)
│   ├── cli.py                     # + seed-demo-products N (solo local, SC-001)
│   ├── core/config.py             # PHOTO_STORAGE, SUPABASE_URL, SUPABASE_STORAGE_KEY, PHOTO_BUCKET
│   ├── domain/
│   │   ├── units.py               # validate_quantity por decimales (R3)
│   │   ├── attributes.py          # validación de atributos contra definiciones (R5)
│   │   ├── search.py              # normalize_text, build_search_text, tokens (R4)
│   │   └── sku.py                 # format_sku(prefix, number) (R1)
│   ├── db/models.py               # Unit, Category, AttributeDefinition, Product, ProductPrice,
│   │                              # ProductPhoto, StockMovement, AdjustmentRequest,
│   │                              # StockCount, StockCountLine
│   ├── services/
│   │   ├── catalog_config.py      # unidades, categorías, atributos
│   │   ├── products.py            # alta (SKU), edición, búsqueda, precio, costo, publicación
│   │   ├── photo_storage.py       # Supabase Storage y disco local (R9)
│   │   ├── photos.py              # validar, normalizar con Pillow, ordenar, quitar
│   │   ├── inventory.py           # post_movement, ajustes, solicitudes, stock bajo, resumen
│   │   └── stock_counts.py        # abrir, anotar, listo, devolver, aplicar, cancelar
│   └── api/
│       ├── product_schemas.py     # ProductAdmin/Seller/Warehouse, StockMovement, líneas a ciegas
│       ├── catalog_config.py      # /units, /categories, /attributes
│       ├── products.py            # /products y subrecursos
│       ├── inventory.py           # /inventory
│       └── stock_counts.py        # /stock-counts
├── migrations/versions/0004_productos_e_inventario.py   # tablas, triggers, datos iniciales
└── tests/
    ├── test_units_domain.py, test_attributes_domain.py, test_search_domain.py
    ├── test_sku.py, test_products.py, test_prices_costs.py, test_photos.py
    ├── test_stock_movements.py, test_adjustments.py, test_kardex.py, test_stock_counts.py
    ├── test_search.py, test_inventory_summary.py, test_catalog_config.py
    ├── test_no_cost_leak.py, test_search_performance.py
    ├── test_permissions_matrix.py # + filas de contracts/api.md
    └── test_audit.py              # + acciones de R14

frontend/src/
├── app/
│   ├── page.tsx                   # + tarjetas de stock bajo y pendientes (R11)
│   ├── productos/page.tsx         # búsqueda con filtros
│   ├── productos/nuevo/page.tsx
│   ├── productos/ficha/page.tsx   # ?id=: datos, fotos, precio/costo (Admin), kardex
│   ├── inventario/ajuste/page.tsx
│   ├── inventario/stock-bajo/page.tsx
│   ├── inventario/conteos/page.tsx
│   ├── inventario/conteo/page.tsx # ?id=: anotar (a ciegas para Almacén) y revisar (Admin)
│   ├── inventario/mis-solicitudes/page.tsx
│   ├── pendientes/page.tsx        # Admin: ajustes por aprobar y conteos listos
│   ├── configuracion/categorias/page.tsx
│   └── configuracion/unidades/page.tsx
├── components/
│   ├── app-shell.tsx              # + entradas de menú por rol
│   ├── products/                  # buscador, tarjeta, formulario, galería, kardex
│   └── ui/                        # + DecimalInput, StatusChip, Tabs
└── lib/photos/resize.ts           # reducir a 1.600 px JPEG antes de subir (R9)

packages/shared/src/
├── api/schema.d.ts                # regenerado
├── format.ts                      # + formatDecimal, formatQuantity, parseDecimalInput (R13)
└── audit-actions.ts               # + acciones y grupos de R14

.github/workflows/
├── deploy-api.yml                 # + secreto SUPABASE_STORAGE_KEY y variables de fotos
└── backup.yml                     # + rclone del bucket de fotos a Cloud Storage (R9)
```

**Structure Decision**: se mantiene el monorepo y la regla de dependencias del backend
`api → services → domain`, `services → db` (`docs/arquitectura.md` §2). Las reglas
puras (unidades, atributos, búsqueda, SKU) van en `domain/` para probarse sin base de
datos. El catálogo público no cambia en esta etapa (1.6).

## Complexity Tracking

Sin violaciones de la constitución que justificar.
