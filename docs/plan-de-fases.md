# Plan de fases — SHT Gestión

| Campo | Valor |
|---|---|
| Versión | 1.0 |
| Fecha | 2026-10-07 |
| Estado | Vigente (etapa 1.0 terminada; 1.1a implementada, pendiente de integrar) |
| Documentos relacionados | `docs/PRD.md` §11, `docs/arquitectura.md`, `docs/modelo-de-datos.md`, `.specify/memory/constitution.md` |

> Detalla el orden de construcción resumido en el PRD (§11): qué entra en cada etapa,
> qué se entrega y cuándo se da por terminada. El alcance de cada requisito está en el
> PRD; aquí solo se asigna a una etapa.

## 1. Cómo se trabaja cada etapa

1. **Antes de empezar:** se responden las preguntas abiertas del PRD asignadas a la
   etapa (sección 4) y se reflejan en el PRD.
2. **Ciclo de Spec Kit:** `/speckit-specify` → `/speckit-clarify` → `/speckit-plan`
   (con su "Constitution Check") → `/speckit-tasks` → `/speckit-analyze` →
   `/speckit-implement`. Una etapa puede dividirse en varias specs si es grande.
3. **Rama por spec**, integrada a `main` al terminarla.

### Definición de terminado (todas las etapas)

Una etapa está terminada cuando:

- [ ] Todos sus requisitos funcionan en producción (o en pruebas, si ya existe ese
      ambiente).
- [ ] Pasa las 7 puertas del "Constitution Check" (constitución, sección "Flujo de
      trabajo y puertas de calidad").
- [ ] Las reglas críticas que toca tienen pruebas automatizadas y la CI está en verde
      (principio VII).
- [ ] Los permisos de sus endpoints están probados por rol (principio IV).
- [ ] `docs/` y `CHANGELOG.md` están actualizados (RNF-09).
- [ ] Se probó restaurar el respaldo diario en el ambiente local (ADR-0002).

## 2. Fase 1 (MVP)

### 1.0 — Arquitectura, modelo de datos y despliegue base

| | |
|---|---|
| **Alcance** | Constitución, arquitectura, ADRs, modelo de datos, este plan; esqueleto del repositorio y despliegue de una versión mínima |
| **Requisitos** | RNF-03, RNF-06, RNF-09 |
| **Entregables** | Documentación de la etapa (hecha); monorepo con `backend/`, `frontend/`, `catalog/`, `packages/shared/`; Docker Compose local; CI (lint + pruebas); API mínima (`/api/v1/health`) en Cloud Run conectada a Supabase; app y catálogo mínimos en Cloudflare Pages; primera migración Alembic con los dominios decimales; respaldo diario funcionando; alerta de presupuesto en Google Cloud |
| **Requiere del dueño** | Crear las cuentas de Google Cloud (con tarjeta y alerta de presupuesto), Supabase y Cloudflare |
| **Terminada cuando** | Un cambio integrado a `main` se despliega solo; la app abre en el teléfono y llama a la API; el respaldo de la noche anterior existe y se restaura en local |
| **Estado** | ✅ Terminada el 2026-10-07: API en Cloud Run, app y catálogo en Cloudflare Pages, despliegues automáticos al integrar en `main` y restauración probada con un respaldo lanzado a mano (el respaldo programado corre cada noche a las 03:00) |

### Guía de estilos base (previa a 1.1a)

✅ Terminada el 2026-10-07: paleta derivada del logo, tipografía, Tailwind CSS v4 con
tema compartido y logo en SVG (`docs/guia-de-estilos.md`, ADR-0007). Los componentes
de cada pantalla se definen en la etapa que los usa (guía, sección 9).

### 1.1 — Usuarios, productos e inventario

Se propone dividirla en dos specs:

**1.1a Usuarios, autenticación y permisos**

| | |
|---|---|
| **Requisitos** | RF-44, RF-45, RF-46, RNF-05, RNF-08 |
| **Entregables** | Inicio de sesión, renovación y cierre de sesión (ADR-0005); PIN del admin con límite de intentos; gestión de usuarios y roles; registro de auditoría; base de permisos por rol para todos los endpoints |
| **Terminada cuando** | Cada rol solo accede a lo que le permite la matriz del PRD (§4), verificado con pruebas en el servidor |
| **Estado** | 🚧 Implementada el 2026-10-08 en la rama `001-usuarios-autenticacion-permisos` (`specs/001-usuarios-autenticacion-permisos/`, ADR-0008). Falta: revisión de seguridad y de código, crear los secretos `jwt-secret` y `setup-code`, integrar a `main` y validar en producción |

**1.1b Productos, categorías e inventario**

| | |
|---|---|
| **Requisitos** | RF-01 a RF-12, RN-08, RN-13 |
| **Entregables** | Categorías con prefijo de SKU y atributos definibles; unidades; productos con SKU automático, atributos, fotos y publicación; histórico de precios; kardex; ajustes con motivo; alerta de stock bajo; conteo físico; búsqueda |
| **Terminada cuando** | El stock solo cambia por movimientos; Almacén no ve ni edita precios de venta y nadie salvo el admin ve costos; la búsqueda responde en menos de 1 s con 1.000 productos de prueba |

### 1.2 — Proveedores y compras

| | |
|---|---|
| **Requisitos** | RF-13 a RF-16, RN-05, RN-09, RN-14 |
| **Entregables** | Proveedores; compras en USD o Bs en borrador y confirmadas; costo promedio ponderado; anulación de compras por el admin |
| **Terminada cuando** | Las pruebas del costo promedio (incluida la anulación) pasan con los casos compartidos; una compra confirmada no puede modificarse ni en la base de datos |

### 1.3 — Tasa BCV, ventas multimoneda, pagos mixtos y descuentos

| | |
|---|---|
| **Requisitos** | RF-17, RF-18, RF-20 a RF-28, RN-01 a RN-07, RN-11, RN-15 |
| **Entregables** | Carga y corrección de la tasa; registro de equipos y series; pantalla de venta con totales en USD y Bs, cm→m, descuentos por ítem y total con autorización, pagos mixtos y vuelto; anulación de ventas; módulo de dinero en Python y TypeScript con los casos compartidos |
| **Nota** | Las ventas ya se envían por la **cola de salida** con clave de idempotencia (ADR-0003), aunque todavía se use solo con conexión. Así la etapa 1.5 no tiene que rehacer la venta |
| **Terminada cuando** | Una venta típica (3–5 productos, pago mixto) se registra en menos de 1 minuto; Python y TypeScript dan el mismo resultado en todos los casos compartidos; reenviar una venta no la duplica |

### 1.4 — Caja

| | |
|---|---|
| **Requisitos** | RF-29 a RF-33, RN-12, RN-16 |
| **Entregables** | Apertura con fondo inicial; una caja abierta por equipo; egresos; cierre con esperado por método, contado y diferencias; cierres inmutables |
| **Terminada cuando** | El cierre de un día de prueba se completa en menos de 10 minutos y cuadra con las ventas, el vuelto, las anulaciones y los egresos |

### 1.5 — Funcionamiento sin conexión

| | |
|---|---|
| **Requisitos** | RNF-01, RN-10, RN-11 |
| **Entregables** | Service worker y app instalable; copia local de productos, precios y tasa; apertura, venta, egresos y cierre de caja sin conexión; sesión sin conexión de hasta 12 horas; almacenamiento persistente; indicador de operaciones pendientes; alertas al sincronizar (stock negativo, precio o total distinto); actualización controlada de la app; ambiente de pruebas (staging) |
| **Terminada cuando** | Con el equipo real del mostrador: se corta internet, se venden y cierran ventas, se reconecta y todo llega sin duplicados; dos equipos de prueba vendiendo sin conexión a la vez no repiten números |

### 1.6 — Catálogo online y pedido por WhatsApp

| | |
|---|---|
| **Requisitos** | RF-34 a RF-38 |
| **Entregables** | Endpoint de datos públicos; build programado cada X horas; filtros y búsqueda; lista de pedido y botón de WhatsApp; fotos servidas desde el build |
| **Terminada cuando** | El catálogo nunca muestra costos ni cantidades (verificado con una prueba sobre el build); se regenera solo a la hora configurada |

### 1.7 — Reportes

| | |
|---|---|
| **Requisitos** | RF-39 a RF-43, RNF-06 (exportación CSV/Excel) |
| **Entregables** | Ventas por día o rango por método y moneda; stock bajo; valor del inventario; margen por producto y período (solo admin); más vendidos; exportación |
| **Terminada cuando** | Cada reporte respeta lo que puede ver cada rol (Vendedor: solo sus ventas del día; Almacén: solo inventario) |

## 3. Puesta en uso real

El negocio puede empezar a usar el sistema por partes, antes de terminar la Fase 1:

| Momento | Qué se usa | Requisitos previos |
|---|---|---|
| Al terminar 1.2 | Carga del inventario real: productos, stock inicial (por ajuste o conteo) y compras con costo | Dominio propio (ADR-0005); ambiente de pruebas creado (ADR-0002); decidir si se pasa a Supabase Pro |
| Al terminar 1.5 | Ventas y caja reales en el mostrador | Prueba completa sin conexión en el equipo real |
| Al terminar 1.6 | Catálogo público | Número de WhatsApp y frecuencia de regeneración definidos |

Las ventas reales no empiezan antes de la etapa 1.5, porque el principio III de la
constitución exige que el mostrador funcione sin internet.

## 4. Preguntas abiertas por etapa

Se responden antes de especificar la etapa indicada (PRD §10).

| Antes de | Pregunta |
|---|---|
| 1.1b | Medidas de mangueras y conexiones más comunes, para precargar atributos |
| 1.1b | ¿Precios distintos para mayoristas o talleres frecuentes? Afecta al modelo de datos (listas de precios), así que conviene decidirlo antes de crear los productos |
| 1.2 | Costo promedio cuando el stock previo es cero o negativo |
| 1.3 | Con conexión, ¿vender sin stock suficiente con advertencia o bloquear? |
| 1.3 | ¿Descuentos sin conexión? |
| 1.4 | Caja en la que se revierte el dinero al anular una venta de una caja ya cerrada |
| 1.6 | Número de WhatsApp del negocio y cada cuántas horas se regenera el catálogo |
| Fase 2 | Impresora de la nota de entrega: térmica o carta/media carta |

## 5. Fases posteriores

Se planifican en detalle al terminar la Fase 1.

| Fase | Contenido | Requisitos |
|---|---|---|
| 2 | Crédito y cuentas por cobrar; nota de entrega impresa o en PDF; etiquetas con código de barras | RF-47 a RF-54 |
| 3 | Facturación fiscal (IVA e IGTF), definida con el contador según la normativa vigente | RF-55 a RF-57, RN-17 |
