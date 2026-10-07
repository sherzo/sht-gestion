# Changelog

Cambios por funcionalidad terminada (RNF-09). Formato basado en
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## [Sin publicar]

### Añadido

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
- Constitución v1.0.0 → v1.1.0: el principio VI pasa a "Simplicidad y costo controlado"
  y remite al presupuesto de RNF-03.
- `CLAUDE.md`: stack, idioma de identificadores y presupuesto actualizados.
