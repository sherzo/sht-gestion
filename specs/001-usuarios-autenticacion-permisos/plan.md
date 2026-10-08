# Implementation Plan: Usuarios, autenticación y permisos (etapa 1.1a)

**Branch**: `001-usuarios-autenticacion-permisos` | **Date**: 2026-10-07 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-usuarios-autenticacion-permisos/spec.md`

## Summary

Identidad, sesiones, permisos por rol y auditoría para todo el sistema (RF-44, RF-45,
RF-46, RNF-05, RNF-08). La API (FastAPI) agrega instalación protegida con código,
inicio de sesión con usuario y contraseña (Argon2id), JWT de 15 minutos más token de
renovación rotativo en cookie dentro de una jornada de 12 horas, contraseñas temporales,
PIN del admin con bloqueo, gestión de usuarios y un registro de auditoría inmutable. Los
permisos se declaran por endpoint y se verifican en cada petición contra la base de
datos; una prueba impide rutas sin declaración. La app interna (Next.js estático) suma
las pantallas de instalación, ingreso, inicio con menú por rol, cambio de contraseña,
mi cuenta (PIN), usuarios y auditoría, con los primeros componentes de la guía de
estilos. Decisiones en [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.14 (backend); TypeScript 7 con React 19 y Next.js 16 (frontend)

**Primary Dependencies**: existentes (FastAPI, SQLAlchemy 2, Alembic, psycopg 3, pydantic-settings; Next.js, Tailwind CSS v4). Nuevas: `argon2-cffi`, `PyJWT` (backend); `lucide-react` (app) y `openapi-typescript` (desarrollo, raíz del monorepo)

**Storage**: PostgreSQL 17 (Supabase en producción, Docker en local); migración `0002_usuarios_y_auditoria`

**Testing**: pytest con `TestClient` y Postgres (marca `db`); ruff; `tsc` y build de Next.js para el frontend

**Target Platform**: API en Cloud Run (Linux); app estática en Cloudflare Pages, navegadores modernos de PC, tablet y teléfono

**Project Type**: aplicación web (API + SPA estática) en monorepo

**Performance Goals**: inicio de sesión < 3 s con la instancia activa (SC-002); verificación de permisos con una sola consulta por petición

**Constraints**: planes gratuitos (RNF-03); sin SSR (export estático); dominio propio pendiente, así que la cookie usa `SameSite=None` provisionalmente (R5); interfaz en español, `dd/mm/aaaa`, `America/Caracas`

**Scale/Scope**: menos de 10 usuarios, 1–2 equipos de mostrador; 15 endpoints nuevos; 7 pantallas

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Puerta | Evaluación | Resultado |
|---|---|---|---|
| 1 | Decimales exactos y tasa de la operación (I) | La etapa no maneja dinero ni cantidades | ✅ No aplica |
| 2 | Kardex e inmutabilidad (II) | No toca stock. `audit_log` es de solo inserción, impuesto en la base con trigger y sin `DELETE`/`TRUNCATE` para `sht_api`; la auditoría va en la misma transacción que la acción (R10) | ✅ |
| 3 | Ventas sin conexión sin duplicar (III) | No toca ventas. El diseño de sesión (JWT con identidad, jornada de 12 horas) es el que ADR-0005 validó para la etapa 1.5; la verificación por petición solo aplica a peticiones que llegan al servidor | ✅ |
| 4 | Permisos en el servidor, sin costos filtrados (IV) | Declaración obligatoria por endpoint con prueba de cobertura, matriz probada por rol, rol leído de la base en cada petición, Argon2id para contraseña y PIN (R1, R3, R9). Sin datos de costo en esta etapa | ✅ |
| 5 | Alcance de la fase y respaldo del PRD (V) | RF-44 a RF-46 de la Fase 1. Las aclaraciones (12 horas, contraseña temporal, código de instalación) se incorporan al PRD v0.7 en esta misma etapa (R14). Sesión sin conexión, equipos y descuentos quedan en 1.3/1.5 | ✅ |
| 6 | Presupuesto y simplicidad (VI) | Sin servicios nuevos; dos secretos más en Secret Manager (dentro del nivel gratuito); bloqueos con columnas, sin servicio de rate limiting; sin ejecutor de pruebas del frontend todavía | ✅ |
| 7 | Pruebas de las reglas críticas (VII) | Permisos por rol en el servidor: matriz completa, cobertura de declaraciones, bloqueos, revocación inmediata y auditoría; pruebas con referencia a RF/FR | ✅ |

**Re-evaluación tras el diseño (fase 1):** sin cambios. `user_session` (R4) amplía el
modelo de ADR-0005 sin contradecirlo; se documenta en `docs/modelo-de-datos.md`.
Ninguna puerta requiere justificación en "Complexity Tracking".

## Project Structure

### Documentation (this feature)

```text
specs/001-usuarios-autenticacion-permisos/
├── plan.md              # Este archivo
├── research.md          # Fase 0: decisiones R1–R14
├── data-model.md        # Fase 1: tablas y acciones auditadas
├── quickstart.md        # Fase 1: guía de validación
├── contracts/
│   └── api.md           # Fase 1: endpoints, errores y matriz de permisos
├── checklists/
│   └── requirements.md  # Calidad de la especificación
└── tasks.md             # Fase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── main.py                    # registrar routers nuevos y manejo de errores en español
│   ├── cli.py                     # reset-password <usuario> (R8)
│   ├── core/
│   │   ├── config.py              # JWT_SECRET, SETUP_CODE, cookie, parámetros de Argon2
│   │   ├── security.py            # hash de contraseña/PIN, JWT, tokens de renovación
│   │   └── errors.py              # ApiError {code, message}
│   ├── domain/
│   │   ├── roles.py               # Role (admin, seller, warehouse)
│   │   ├── business_time.py       # fecha de negocio en America/Caracas (arquitectura §4.2)
│   │   └── lockout.py             # regla de 5 intentos / 15 minutos
│   ├── db/
│   │   ├── session.py             # (existe) + dependencia de sesión por petición
│   │   ├── base.py                # DeclarativeBase y metadatos para Alembic
│   │   └── models.py              # AppUser, UserSession, RefreshToken, AuditLog
│   ├── services/
│   │   ├── audit.py               # record_audit, consulta con filtros
│   │   ├── auth.py                # instalación, login, renovación, logout, contraseña
│   │   ├── pin.py                 # definir y verificar PIN
│   │   └── users.py               # alta, edición, rol, (des)activación, restablecer
│   └── api/
│       ├── deps.py                # public, require_authenticated, require_roles, current_user
│       ├── health.py              # (existe) + declaración public
│       ├── setup.py
│       ├── auth.py
│       ├── users.py
│       └── audit.py
├── migrations/versions/0002_usuarios_y_auditoria.py
└── tests/
    ├── conftest.py                # base de pruebas, limpieza entre pruebas, usuarios por rol
    ├── test_permissions_matrix.py # SC-003
    ├── test_route_declarations.py # FR-011
    ├── test_setup.py
    ├── test_auth_session.py       # login, bloqueo, refresh, 12 h, logout, reutilización
    ├── test_password.py           # temporal, cambio, restablecimiento
    ├── test_pin.py
    ├── test_users.py
    └── test_audit.py              # registros, inmutabilidad, filtros, atomicidad

frontend/src/
├── app/
│   ├── layout.tsx                 # + AuthProvider
│   ├── page.tsx                   # inicio: nombre, rol, menú (reemplaza la página de 1.0)
│   ├── instalacion/page.tsx
│   ├── ingresar/page.tsx
│   ├── cambiar-clave/page.tsx
│   ├── mi-cuenta/page.tsx         # contraseña y PIN
│   ├── usuarios/page.tsx          # lista, filtros y diálogos de alta/edición
│   └── auditoria/page.tsx
├── components/
│   ├── ui/                        # Button, Field, Alert, Dialog, DataTable
│   ├── app-shell.tsx              # barra superior y menú por rol
│   └── require-auth.tsx           # guardia de ruta (solo oculta; el servidor protege)
└── lib/
    ├── api/client.ts              # fetch con token, renovación única y reintento
    └── auth/                      # contexto de sesión, Web Locks para renovar

packages/shared/src/
├── api/schema.d.ts                # tipos generados del OpenAPI
├── format.ts                      # formatDateTime (dd/mm/aaaa hh:mm, America/Caracas)
├── audit-actions.ts               # etiquetas en español de las acciones
└── roles.ts                       # etiquetas en español de los roles

.github/workflows/deploy-api.yml   # --set-secrets JWT_SECRET y SETUP_CODE, variables de cookie
```

**Structure Decision**: se mantiene el monorepo de la etapa 1.0 y la regla de
dependencias del backend `api → services → domain`, `services → db`
(`docs/arquitectura.md` §2). El catálogo no cambia en esta etapa.

## Complexity Tracking

Sin violaciones de la constitución que justificar.
