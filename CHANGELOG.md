# Changelog

Cambios por funcionalidad terminada (RNF-09). Formato basado en
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## [Sin publicar]

### Añadido

- Despliegue base (etapa 1.0): monorepo con `backend/` (FastAPI, endpoints de salud,
  Alembic con los dominios decimales de ADR-0004, pruebas, Dockerfile), `frontend/` y
  `catalog/` (Next.js estático) y `packages/shared/`; Postgres local con Docker Compose;
  workflows de CI, despliegue de la API en Cloud Run, despliegue web en Cloudflare
  Pages y respaldo diario cifrado (RNF-06); guía `docs/despliegue.md`.
- Plan de fases (etapa 1.0): `docs/plan-de-fases.md` con alcance, entregables y
  criterios de terminado por etapa, puesta en uso real por partes y preguntas abiertas
  asignadas a cada etapa.
- Modelo de datos (etapa 1.0): `docs/modelo-de-datos.md` con tablas, dominios
  decimales, reglas de inmutabilidad en la base de datos y previsiones para la Fase 2
  (crédito) y la Fase 3 (IVA/IGTF).
- Arquitectura base (etapa 1.0): `docs/arquitectura.md` y ADRs 0001–0006 en
  `docs/decisiones/` (stack FastAPI + Next.js estático/PWA + Supabase; hosting en Cloud
  Run y Cloudflare Pages; ventas sin conexión con numeración por equipo; dinero y
  redondeo; autenticación propia; idioma de identificadores).
- Constitución del proyecto (`.specify/memory/constitution.md`): 7 principios derivados
  de `docs/PRD.md` y `CLAUDE.md`, puertas del "Constitution Check" y reglas de
  gobernanza (etapa 1.0).
- Spec Kit inicializado con integración Claude (etapa 1.0).
- PRD y `CLAUDE.md` con el contexto del proyecto.

### Cambiado

- PRD v0.4: un solo equipo de mostrador al inicio (§2); presupuesto de infraestructura
  con tope de 35–40 USD/mes (RNF-03); nuevas preguntas abiertas surgidas de la
  arquitectura (§10).
- PRD v0.5: descuentos por ítem o total, en monto o porcentaje (RF-22); compras
  confirmadas inmutables y anulables solo por el admin (RN-14); corrección auditada de
  la tasa (RN-15); una caja por equipo (RN-16); precios con IVA incluido (RN-17).
- ADR-0004: reglas de redondeo de descuentos y reparto del descuento total entre ítems.
- Constitución v1.0.0 → v1.1.0: el principio VI pasa a "Simplicidad y costo controlado"
  y remite al presupuesto de RNF-03.
- `CLAUDE.md`: stack, idioma de identificadores y presupuesto actualizados.
