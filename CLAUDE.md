# SHT Gestión — Suministros Hidráulicos Turmero

Sistema web de inventario, compras, ventas multimoneda, caja y catálogo online (pedidos por WhatsApp) para un negocio pequeño de mangueras hidráulicas, conexiones, ferrules y ferretería en Venezuela.

**Estado:** Fase 1, etapa 1.0 (arquitectura). Aún no hay código.

**Stack:** backend FastAPI (Python) en Cloud Run · frontend Next.js (TypeScript, export estático, app instalable/PWA) en Cloudflare Pages · Supabase solo como Postgres y almacenamiento de fotos (sin Data API ni Supabase Auth). Detalle en `docs/arquitectura.md` y ADRs en `docs/decisiones/`.

## Documentación (fuente de verdad)

- `docs/PRD.md`: **qué** y **por qué**. Requisitos `RF-XX`, reglas `RN-XX`, no funcionales `RNF-XX`. Ante dudas de negocio, consultarlo.
- `docs/arquitectura.md`: **cómo** (stack, componentes, flujos, convenciones).
- `docs/modelo-de-datos.md`, `docs/plan-de-fases.md`: pendientes (etapa 1.0).
- `.specify/memory/constitution.md`: principios no negociables; cada plan pasa su "Constitution Check".
- `docs/decisiones/`: registro de decisiones técnicas (ADR).
- `CHANGELOG.md`: cambios por funcionalidad terminada.

## Reglas de trabajo

- Todo en **español**: UI, docs, commits y comentarios. Identificadores de código (tablas, columnas, Python, TypeScript, rutas de la API) en **inglés**, con el glosario de `docs/arquitectura.md` (ADR-0006).
- Referenciar `RF-XX` / `RN-XX` en tareas, commits y docs.
- Al terminar una funcionalidad: actualizar `docs/` y `CHANGELOG.md` (RNF-09).
- Cambios de alcance o reglas de negocio → primero en `docs/PRD.md`, no inventarlos en el código.
- No implementar nada de Fase 2/3 ni fuera de alcance sin pedirlo, pero el modelo de datos **no debe impedir** facturación fiscal (IVA/IGTF) futura.

## Reglas de negocio críticas

- **Moneda base USD** (RN-01): precios y costos se guardan en USD. Bs = USD × tasa BCV, redondeado a 2 decimales (RN-02).
- **Única tasa: BCV** (RN-03), cargada a diario por el admin con histórico. Si falta la del día, usar la última y mostrar su fecha (RF-18).
- **USDT, Zelle y efectivo USD = USD 1:1** (RN-04). Pago en Bs cubre `monto_bs ÷ tasa_venta` (RN-06).
- **Cada venta, pago y compra guarda su tasa**; los históricos nunca se recalculan (RN-05).
- **Stock solo cambia vía movimientos** de kardex (RN-08): compra, venta, reverso por anulación, ajuste ± con motivo obligatorio.
- **Registros cerrados son inmutables** (ventas, cierres de caja): se corrigen con anulaciones o movimientos nuevos (RN-12, RF-33).
- **Sin productos compuestos/kits** (RN-13): una manguera armada = varios ítems individuales en la venta.
- **Unidades:** `metro` (decimal, precisión de cm; el vendedor puede ingresar cm y se convierte a m) y `unidad` (entero). Mangueras siempre por metro (RF-05, RF-21). Usar tipos decimales exactos para dinero y cantidades, nunca float.
- **Costo:** promedio ponderado al registrar compras (RN-09). Compras en Bs guardan tasa y equivalente USD.
- **SKU automático** por categoría: `MAN-`, `CON-`, `FER-`, `FRT-` + correlativo de 4 dígitos (RF-02).
- **Descuentos del vendedor** requieren autorización del admin (PIN o aprobación), registrando quién autorizó (RN-07).
- **Pagos mixtos** con vuelto (método y moneda registrados). Métodos: Efectivo Bs, Pago móvil, Punto de venta, Efectivo USD, Zelle, Binance USDT; todos excepto efectivo exigen referencia (RF-24).
- **Venta requiere caja abierta** (RF-30). Cierre compara esperado vs. contado por método de pago.
- **Anular venta:** solo admin, con motivo; devuelve stock y revierte caja (RF-27).

## Roles (permisos verificados en el servidor, no solo en la UI)

- **Admin:** todo (precios, costos, márgenes, tasa, usuarios, anulaciones, autorizaciones).
- **Vendedor:** ventas y su caja; sin costos ni márgenes; reportes solo de sus ventas del día.
- **Almacén:** productos (sin precio de venta), compras, ajustes y conteos; reportes de inventario.
- **Público:** catálogo sin login; nunca exponer costos ni cantidades exactas (solo "Disponible"/"Agotado").
- Auditar acciones sensibles: precios, descuentos, anulaciones, ajustes, tasas (RF-46).

## Requisitos no funcionales clave

- **Offline (crítico):** el módulo de ventas funciona sin internet y sincroniza sin duplicar ventas; correlativos únicos entre equipos (RN-10, RN-11). Stock negativo tras sincronizar → se registra y alerta al admin.
- **Costo (RNF-03):** arranca en planes gratuitos; tope de 35–40 USD/mes; cada servicio pago se justifica en un ADR (~1.000 productos, pocos usuarios). El catálogo se regenera cada X horas, no en tiempo real.
- **Responsive** (PC, tablet, teléfono); búsqueda < 1 s; fluido en equipos modestos.
- **Localización:** formato `1.234,56`, fechas `dd/mm/aaaa`, zona horaria `America/Caracas`.
- Respaldo diario automático y exportación CSV/Excel.

## Plan Fase 1 (MVP)

1.0 arquitectura, modelo de datos y despliegue base · 1.1 usuarios, productos, inventario · 1.2 compras · 1.3 tasa BCV y ventas · 1.4 caja · 1.5 offline · 1.6 catálogo WhatsApp · 1.7 reportes.
Fase 2: crédito, nota de entrega, etiquetas. Fase 3: facturación fiscal.
