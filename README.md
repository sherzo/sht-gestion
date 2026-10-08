# 🔧 SHT Gestión

[![CI](https://github.com/sherzo/sht-gestion/actions/workflows/ci.yml/badge.svg)](https://github.com/sherzo/sht-gestion/actions/workflows/ci.yml)

**Sistema de inventario, ventas y catálogo para Suministros Hidráulicos Turmero** 🇻🇪

Mangueras hidráulicas, conexiones, ferrules y ferretería ligera: todo bajo control, desde la computadora o el teléfono. 📱💻

> 🚀 **Estado:** Fase 1. La etapa 1.0 (arquitectura, modelo de datos y despliegue base) está terminada y en producción. Siguiente: etapa 1.1a, usuarios, inicio de sesión y permisos.

---

## 🎯 ¿Qué problema resuelve?

Un negocio que está comenzando, sin sistema ni códigos de producto, que vende en dólares pero cobra en varias monedas y métodos usando la tasa BCV. SHT Gestión busca:

- 📦 Saber en todo momento cuánto stock hay de cada producto y su historial.
- 🧾 Registrar ventas rápidas en mostrador, con precios en **USD y Bs** y **pagos mixtos**.
- 💵 Cuadrar la caja diaria por método de pago sin cálculos manuales.
- 🚚 Registrar compras y proveedores para conocer los márgenes.
- 🛒 Mostrar un catálogo online que genere pedidos por **WhatsApp**.
- 💸 Operar con un costo de infraestructura bajo: arranca gratis, con un tope de 35–40 USD/mes.

## ✨ Funcionalidades principales (Fase 1)

| | Módulo | Descripción |
|---|---|---|
| 📦 | Productos e inventario | SKU automático por categoría, atributos técnicos, venta por metro (con precisión de centímetro) o por unidad, kardex de movimientos y alertas de stock bajo. |
| 🚚 | Compras | Proveedores, compras en USD o Bs y costo promedio ponderado. |
| 💱 | Tasa BCV | Carga diaria de la tasa oficial con histórico. |
| 🧾 | Ventas | Pagos mixtos (Efectivo Bs, Pago móvil, Punto de venta, Efectivo USD, Zelle, USDT), vuelto y descuentos autorizados por el admin. |
| 💰 | Caja | Apertura, egresos, cierre y cuadre por método de pago. |
| 📴 | Modo sin conexión | El módulo de ventas sigue funcionando sin internet y sincroniza al reconectar. |
| 🌐 | Catálogo online | Página pública con precios en USD y Bs, disponibilidad y pedido por WhatsApp. |
| 👥 | Usuarios y roles | Administrador, Vendedor y Almacén, con auditoría de acciones sensibles. |
| 📊 | Reportes | Ventas por método de pago, stock bajo, valor del inventario, márgenes y más vendidos. |

## 🗺️ Hoja de ruta

- **Fase 1 (MVP)** 🚀 Todo lo anterior, construido en etapas de la 1.0 a la 1.7 ([plan de fases](docs/plan-de-fases.md)).
- **Fase 2** 📝 Crédito a clientes, nota de entrega impresa o en PDF y etiquetas con código de barras.
- **Fase 3** 🏛️ Facturación fiscal (IVA e IGTF).

## 🌐 En producción

| | Enlace |
|---|---|
| 🧾 App interna (vendedor, almacén y admin) | https://sht-gestion-app.pages.dev |
| 🛒 Catálogo público | https://sht-gestion-catalogo.pages.dev |

Por ahora ambos son páginas mínimas: las funcionalidades llegan etapa por etapa.

## 🧱 Stack

| Pieza | Tecnología | Dónde corre |
|---|---|---|
| API | Python + FastAPI | Google Cloud Run |
| App interna (instalable, funciona sin conexión) | Next.js estático + TypeScript | Cloudflare Pages |
| Catálogo público | Next.js estático | Cloudflare Pages |
| Base de datos y fotos | Postgres y Storage | Supabase |

```
backend/           API FastAPI, migraciones Alembic y pruebas
frontend/          app interna
catalog/           catálogo público
packages/shared/   TypeScript compartido
docs/              documentación y decisiones (ADR)
```

## 💻 Desarrollo local

Requisitos: Python 3.14 con [uv](https://docs.astral.sh/uv/), Node 24 con pnpm y Docker Desktop.

```bash
# Base de datos
docker compose up -d

# API (http://localhost:8000, documentación en /docs)
# .env incluye JWT_SECRET, SETUP_CODE (código de /instalacion) y la cookie de sesión.
cd backend
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload

# App interna (http://localhost:3000) y catálogo (http://localhost:3001)
pnpm install
cp frontend/.env.example frontend/.env.local
pnpm dev:app
pnpm dev:catalog
```

Pruebas y verificaciones:

```bash
# Las pruebas `db` vacían las tablas: usar una base dedicada, p. ej. sht_test.
cd backend && uv run ruff check . && DATABASE_URL=postgresql+psycopg://sht:sht@localhost:5432/sht_test uv run pytest
pnpm typecheck && pnpm build
pnpm api:types   # regenera los tipos de la API en packages/shared tras cambiar el backend
```

> 🪟 **En Windows:** los comandos funcionan igual en PowerShell (`cp` es un alias de `Copy-Item`). Después de instalar una herramienta nueva, reinicia por completo VS Code (o la aplicación desde la que abres la terminal) para que la encuentre. Más particularidades en [`despliegue.md`](docs/despliegue.md#2-herramientas-locales).

## 🚀 Cómo se despliega

- Integrar un cambio en `main` lo despliega solo: la API en Cloud Run si cambió `backend/`, y la app y el catálogo en Cloudflare Pages si cambió el frontend. Antes, la CI corre el lint, las migraciones y las pruebas.
- Cada noche se guarda un respaldo cifrado de la base de datos (30 días de historial).
- Configuración de los servicios, secretos y restauración de respaldos: [`docs/despliegue.md`](docs/despliegue.md).

## 🤝 Cómo se trabaja

- **Reglas no negociables:** la [constitución](.specify/memory/constitution.md) (dinero exacto, trazabilidad, ventas sin conexión, permisos en el servidor, costo controlado, pruebas de las reglas críticas).
- **Una etapa a la vez, con [Spec Kit](https://github.com/github/spec-kit):** especificar → aclarar → planificar → tareas → analizar → implementar. Las reglas de negocio se cambian primero en el [PRD](docs/PRD.md).
- **Una rama por cambio**, integrada a `main` al terminar; commits en español que citan los requisitos (`RF-XX`, `RN-XX`).
- Al terminar cada funcionalidad se actualizan `docs/` y el [`CHANGELOG`](CHANGELOG.md).

## 📚 Documentación

- 📄 [`PRD.md`](docs/PRD.md): qué se construye y por qué.
- 🏗️ [`arquitectura.md`](docs/arquitectura.md): cómo se construye.
- 🗃️ [`modelo-de-datos.md`](docs/modelo-de-datos.md): tablas y reglas de los datos.
- 🗓️ [`plan-de-fases.md`](docs/plan-de-fases.md): qué entra en cada etapa.
- 🚀 [`despliegue.md`](docs/despliegue.md): configuración de los servicios y operación.
- 🧭 [`decisiones/`](docs/decisiones/): decisiones técnicas (ADR).
- 📝 [`CHANGELOG.md`](CHANGELOG.md): qué cambió en cada etapa.

## 🤖 Hecho con Claude Code

Este proyecto se está diseñando y construyendo con la ayuda de **[Claude Code](https://claude.com/claude-code)**, el asistente de programación de Anthropic. 🧡

---

Hecho con ❤️ en Turmero, Venezuela.
