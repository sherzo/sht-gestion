# 🔧 SHT Gestión

**Sistema de inventario, ventas y catálogo para Suministros Hidráulicos Turmero** 🇻🇪

Mangueras hidráulicas, conexiones, ferrules y ferretería ligera: todo bajo control, desde la computadora o el teléfono. 📱💻

> 🚧 **Estado:** Fase 1, etapa 1.0 (arquitectura y despliegue base). Hay un esqueleto del sistema, todavía sin funcionalidades de negocio.

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

- **Fase 1 (MVP)** 🚀 Todo lo anterior, construido en etapas de la 1.0 a la 1.7.
- **Fase 2** 📝 Crédito a clientes, nota de entrega impresa o en PDF y etiquetas con código de barras.
- **Fase 3** 🏛️ Facturación fiscal (IVA e IGTF).

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
cd backend && uv run ruff check . && uv run pytest
pnpm typecheck && pnpm build
```

## 📚 Documentación

- 📄 [`PRD.md`](docs/PRD.md): qué se construye y por qué.
- 🏗️ [`arquitectura.md`](docs/arquitectura.md): cómo se construye.
- 🗃️ [`modelo-de-datos.md`](docs/modelo-de-datos.md): tablas y reglas de los datos.
- 🗓️ [`plan-de-fases.md`](docs/plan-de-fases.md): qué entra en cada etapa.
- 🚀 [`despliegue.md`](docs/despliegue.md): configuración de los servicios y operación.
- 🧭 [`decisiones/`](docs/decisiones/): decisiones técnicas (ADR).

## 🤖 Hecho con Claude Code

Este proyecto se está diseñando y construyendo con la ayuda de **[Claude Code](https://claude.com/claude-code)**, el asistente de programación de Anthropic. 🧡

---

Hecho con ❤️ en Turmero, Venezuela.
