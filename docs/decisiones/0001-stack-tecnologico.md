# ADR-0001: Stack tecnológico

- **Estado:** Aceptada
- **Fecha:** 2026-10-05
- **Requisitos relacionados:** RNF-01, RNF-02, RNF-03, RNF-04, RNF-05; principios I, III, IV y VI

## Contexto

El sistema necesita:

- una aplicación web que funcione en PC, tablet y teléfono y que, en el módulo de ventas,
  siga operando sin internet (RNF-01, RNF-02);
- reglas de negocio con aritmética decimal exacta (principio I);
- permisos verificados en el servidor (RNF-05);
- un catálogo público regenerado cada X horas (RF-38);
- costo de infraestructura dentro del presupuesto de RNF-03.

El dueño del proyecto prefiere Python con FastAPI para el backend, Next.js para el
frontend y Supabase (Postgres) como base de datos.

## Decisión

**Backend: Python + FastAPI**

- Toda la lógica de negocio (ventas, kardex, costo promedio, caja, permisos) vive en el
  backend y es la autoridad final.
- Herramientas: `uv` (dependencias y entorno), Pydantic v2 (validación), SQLAlchemy 2
  (acceso a datos), Alembic (migraciones), pytest (pruebas).
- La versión de Python es la estable vigente al iniciar el código y se fija en el
  repositorio.
- Se empaqueta como imagen de contenedor (ver ADR-0002).

**Frontend: Next.js + TypeScript como sitio estático (`output: 'export'`)**

- Es una app instalable (PWA): manifiesto + service worker con Serwist para precargar la
  aplicación y funcionar sin conexión.
- No se usan funciones de servidor de Next.js (SSR, server actions, API routes): no
  funcionan sin conexión y requerirían un servidor adicional.
- Datos locales en IndexedDB mediante Dexie (ver ADR-0003).
- Aritmética decimal exacta con `decimal.js` (ver ADR-0004).
- Los tipos de la API se generan desde el OpenAPI de FastAPI con `openapi-typescript`.

**Catálogo público: proyecto Next.js estático separado**

- Se construye y publica aparte de la app interna. Si compartieran build, regenerar el
  catálogo cada X horas publicaría también una versión nueva de la app interna y
  forzaría actualizaciones del service worker en el mostrador.
- Obtiene sus datos en el momento del build desde un endpoint de solo lectura que
  devuelve únicamente campos públicos (RF-35).

**Base de datos: Supabase como Postgres administrado + Storage para fotos**

- Se usa Postgres (tipos `NUMERIC` exactos, transacciones, bloqueos de fila) y Storage.
- **No** se usan la Data API (PostgREST), Supabase Auth ni Realtime. La Data API se
  desactiva para que el único acceso a los datos sea a través de FastAPI.
- FastAPI se conecta con un rol de Postgres propio con permisos mínimos, no con el rol
  administrador.

**Organización del repositorio: monorepo**

```
backend/            FastAPI, migraciones Alembic, pruebas
frontend/           app interna (Next.js, PWA)
catalog/            catálogo público (Next.js estático)
packages/shared/    código TypeScript compartido (dinero, tipos generados)
shared/test-vectors/  casos de prueba JSON compartidos por Python y TypeScript
docs/               documentación
.github/workflows/  CI, despliegues, respaldo y regeneración del catálogo
```

`frontend/`, `catalog/` y `packages/shared/` forman un workspace de pnpm.

## Alternativas consideradas

- **PWA + Supabase sin backend propio** (lógica en funciones de Postgres y RLS): menos
  piezas que alojar, pero la lógica de negocio en SQL es más difícil de probar y mantener,
  y aumenta la dependencia de Supabase.
- **Backend en Cloudflare Workers + D1 (SQLite):** gratuito y rápido, pero sin tipo
  decimal exacto y con autenticación y API por construir igual.
- **App de escritorio en el mostrador (Tauri/Electron + SQLite):** la más robusta sin
  conexión, pero la administración y el catálogo igual necesitan la nube; duplica el
  trabajo.
- **Next.js con servidor (SSR):** descartado porque las páginas generadas en el servidor
  no cargan sin conexión y exigirían hosting de Node.js.

## Consecuencias

**Positivas**

- Reglas de negocio en Python, legibles y fáciles de probar.
- Una sola puerta de entrada a los datos (FastAPI), coherente con el principio IV.
- Contrato tipado entre frontend y backend generado automáticamente.
- Baja dependencia de Supabase: migrar a otro Postgres es cambiar la cadena de conexión
  y el almacenamiento de fotos.

**Negativas y riesgos**

- Dos lenguajes. El cálculo de una venta se hace en TypeScript (sin conexión) y en
  Python (autoridad). Se mitiga con casos de prueba compartidos (ADR-0004).
- Hay un servidor más que alojar y mantener (ADR-0002).
- La autenticación es propia y hay que construirla bien (ADR-0005).
