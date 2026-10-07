# Changelog

Cambios por funcionalidad terminada (RNF-09). Formato basado en
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/). Cada etapa terminada de la
Fase 1 cierra una versión: la 1.0 es `0.1.0`, la 1.1 será `0.2.0`, y así sucesivamente.

## [Sin publicar]

### Añadido

- Guía de estilos base (`docs/guia-de-estilos.md`, ADR-0007, RNF-02): paleta derivada
  del logo (azul `#03045E` y ámbar `#F7AA00`) con escalas, grises, colores de estado y
  tokens semánticos validados por contraste; tipografía Montserrat + Inter autoalojada;
  solo tema claro.
- Logo en SVG extraído del PDF original (`docs/marca/`): versiones vertical, horizontal,
  negativa, monocromática, isotipo e ícono de la app.
- Tailwind CSS v4 en la app y el catálogo con el tema compartido
  `packages/shared/styles/theme.css`; logo, favicon y color de la barra del navegador en
  ambas páginas mínimas.

## [0.1.0] — 2026-10-07 — Etapa 1.0: arquitectura, modelo de datos y despliegue base

### Añadido

- Producción en marcha: API en https://sht-api-wilmjh5geq-uk.a.run.app (Cloud Run), app
  interna en https://sht-gestion-app.pages.dev y catálogo en
  https://sht-gestion-catalogo.pages.dev (Cloudflare Pages), base de datos en Supabase.
  Respaldo diario cifrado en Cloud Storage y restauración probada en local (RNF-06).
- Monorepo con `backend/` (FastAPI, endpoints de salud, Alembic con los dominios
  decimales de ADR-0004, pruebas, Dockerfile), `frontend/` y `catalog/` (Next.js
  estático) y `packages/shared/`; Postgres local con Docker Compose.
- Workflows de GitHub Actions: CI, despliegue de la API en Cloud Run, despliegue de la
  app y el catálogo en Cloudflare Pages (crea los proyectos si no existen) y respaldo
  diario. Autenticación con Google Cloud sin claves (Workload Identity Federation).
- `docs/despliegue.md`: configuración real de Google Cloud, Supabase, Cloudflare y
  GitHub, particularidades de Windows y procedimiento de restauración.
- `docs/plan-de-fases.md`: alcance, entregables y criterios de terminado por etapa,
  puesta en uso real por partes y preguntas abiertas asignadas a cada etapa.
- `docs/modelo-de-datos.md`: tablas, dominios decimales, inmutabilidad impuesta en la
  base de datos y previsiones para la Fase 2 (crédito) y la Fase 3 (IVA/IGTF).
- `docs/arquitectura.md` y ADRs 0001–0006 en `docs/decisiones/`: stack FastAPI +
  Next.js estático/PWA + Supabase; hosting y presupuesto; ventas sin conexión con
  numeración por equipo; dinero y redondeo; autenticación propia; idioma de
  identificadores.
- Constitución del proyecto (`.specify/memory/constitution.md`): 7 principios, puertas
  del "Constitution Check" y reglas de gobernanza.
- Spec Kit inicializado con integración Claude.
- PRD y `CLAUDE.md` con el contexto del proyecto.

### Cambiado

- PRD v0.4: un solo equipo de mostrador al inicio (§2); presupuesto de infraestructura
  con tope de 35–40 USD/mes (RNF-03); nuevas preguntas abiertas surgidas de la
  arquitectura (§10).
- PRD v0.5: descuentos por ítem o total, en monto o porcentaje (RF-22); compras
  confirmadas inmutables y anulables solo por el admin (RN-14); corrección auditada de
  la tasa (RN-15); una caja por equipo (RN-16); precios con IVA incluido (RN-17).
- PRD v0.6: resumen y objetivos alineados con el presupuesto de RNF-03.
- ADR-0004: reglas de redondeo de descuentos y reparto del descuento total entre ítems.
- Constitución v1.0.0 → v1.1.0: el principio VI pasa a "Simplicidad y costo controlado"
  y remite al presupuesto de RNF-03.
- Arquitectura, modelo de datos y plan de fases pasan de borrador a versión 1.0 vigente.
- `CLAUDE.md` y `README.md` actualizados con el stack, el estado y cómo se trabaja.
