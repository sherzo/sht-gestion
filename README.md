# 🔧 SHT Gestión

**Sistema de inventario, ventas y catálogo para Suministros Hidráulicos Turmero** 🇻🇪

Mangueras hidráulicas, conexiones, ferrules y ferretería ligera: todo bajo control, desde la computadora o el teléfono. 📱💻

> 🚧 **Estado:** en planificación (Fase 1, etapa 1.0). Aún no hay código.

---

## 🎯 ¿Qué problema resuelve?

Un negocio que está comenzando, sin sistema ni códigos de producto, que vende en dólares pero cobra en varias monedas y métodos usando la tasa BCV. SHT Gestión busca:

- 📦 Saber en todo momento cuánto stock hay de cada producto y su historial.
- 🧾 Registrar ventas rápidas en mostrador, con precios en **USD y Bs** y **pagos mixtos**.
- 💵 Cuadrar la caja diaria por método de pago sin cálculos manuales.
- 🚚 Registrar compras y proveedores para conocer los márgenes.
- 🛒 Mostrar un catálogo online que genere pedidos por **WhatsApp**.
- 💸 Operar con un costo de infraestructura **cercano a cero**.

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

## 📚 Documentación

- 📄 [`PRD.md`](docs/PRD.md): qué se construye y por qué.
- 🏗️ `docs/arquitectura.md`, `docs/modelo-de-datos.md` y `docs/plan-de-fases.md`: en preparación.

## 🤖 Hecho con Claude Code

Este proyecto se está diseñando y construyendo con la ayuda de **[Claude Code](https://claude.com/claude-code)**, el asistente de programación de Anthropic. 🧡

---

Hecho con ❤️ en Turmero, Venezuela.
