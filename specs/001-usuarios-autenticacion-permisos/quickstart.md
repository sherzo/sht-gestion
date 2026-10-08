# Guía de validación: usuarios, autenticación y permisos

Escenarios para comprobar de punta a punta que la etapa 1.1a cumple la especificación.
Endpoints y errores: `contracts/api.md`. Tablas: `data-model.md`.

## Preparación local

```bash
docker compose up -d                      # Postgres 17
cd backend
cp .env.example .env                      # completar JWT_SECRET y SETUP_CODE (nuevos)
uv sync
uv run alembic upgrade head               # incluye 0002_usuarios_y_auditoria
uv run uvicorn app.main:app --reload      # http://localhost:8000
# en otra terminal, desde la raíz
pnpm install
pnpm dev:app                              # http://localhost:3000
```

Variables nuevas del backend: `JWT_SECRET`, `SETUP_CODE`, `REFRESH_COOKIE_SAMESITE`
(`lax` en local), `REFRESH_COOKIE_SECURE` (`false` en local). Detalle en R5 y
`docs/despliegue.md`.

## Pruebas automatizadas

```bash
cd backend
uv run ruff check . && uv run ruff format --check .
uv run pytest                             # con DATABASE_URL: incluye las pruebas db
pnpm typecheck && pnpm build              # desde la raíz
```

Deben pasar, como mínimo:

- Matriz de permisos completa: cada endpoint × (anónimo, Admin, Vendedor, Almacén,
  contraseña temporal) contra la tabla del contrato (SC-003).
- Cobertura de declaraciones: ninguna ruta sin `public`, `require_authenticated` o
  `require_roles` (FR-011).
- Bloqueos de contraseña, PIN e instalación tras 5 fallos (SC-006).
- Desactivación, cambio de rol y cierre de sesión efectivos en la siguiente petición
  (SC-004).
- Sesión que vence a las 12 horas aunque se renueve (SC-008), con el reloj simulado.
- Reutilización de un token de renovación ya rotado (fuera de los 30 s) revoca la
  sesión.
- Auditoría: cada acción de FR-020 crea su registro; ninguno contiene contraseñas ni
  PIN; `UPDATE` y `DELETE` sobre `audit_log` fallan en la base (SC-005).
- Una acción cuya auditoría falla no se realiza (FR-022).

## Escenarios manuales (app en el navegador)

| # | Pasos | Resultado esperado |
|---|---|---|
| 1 | Base vacía; abrir la app | Redirige a `/instalacion` |
| 2 | Instalar con un código incorrecto | Mensaje de código inválido; aparece en la auditoría al terminar la instalación |
| 3 | Instalar con el código correcto (`SETUP_CODE`) | Entra como Admin a `/`; `/instalacion` ya no está disponible |
| 4 | Admin crea un Vendedor y un usuario de Almacén con contraseña inicial | Aparecen en `/usuarios` como "contraseña temporal"; tiempo total < 2 min (SC-001) |
| 5 | Entrar como el Vendedor | Lo lleva a `/cambiar-clave` y no permite otra cosa hasta cambiarla (SC-009) |
| 6 | Vendedor cambia la contraseña | Llega a `/` con su nombre, rol y menú sin "Usuarios" ni "Auditoría" |
| 7 | Vendedor abre `/usuarios` escribiendo la ruta | Mensaje de permiso insuficiente; la API responde 403 |
| 8 | Contraseña incorrecta 5 veces | Mensaje genérico; al sexto intento, aviso de esperar 15 minutos (SC-006) |
| 9 | Con el Vendedor conectado en otra ventana, el Admin lo desactiva | En la siguiente acción del Vendedor aparece el diálogo de reingreso, no puede volver a entrar y termina en `/ingresar` (SC-004) |
| 10 | Admin intenta desactivarse o quitarse el rol siendo el único admin | Lo impide con un mensaje claro |
| 11 | Admin define su PIN en `/mi-cuenta` y lo prueba bien y mal | Acierto registra quién autorizó; 5 fallos bloquean 15 min aunque luego acierte |
| 12 | Admin abre `/auditoria` y filtra por usuario, acción y fechas | Ve todas las acciones anteriores, más recientes primero, con fecha `dd/mm/aaaa hh:mm` |
| 13 | Recargar la página con la sesión abierta | Sigue conectado sin pedir contraseña (renovación por cookie) |
| 14 | Cerrar sesión | Vuelve a `/ingresar`; el botón atrás no recupera la sesión |
| 15 | Repetir 4–12 en un teléfono (360 px) y en PC | Sin desplazamiento horizontal; contrastes de la guía (SC-007) |
| 16 | Con un formulario a medio llenar, hacer vencer la jornada (por ejemplo, revocando la sesión desde otra ventana con "Cerrar sesión") | Aparece el diálogo de reingreso sobre la página; al entrar con el mismo usuario, el formulario conserva lo escrito y la acción se completa |

## Producción (provisional, sin dominio propio)

1. Crear los secretos `jwt-secret` y `setup-code` (`docs/despliegue.md`) y desplegar.
2. Instalar desde `https://sht-gestion-app.pages.dev` con el código.
3. Medir el inicio de sesión con la instancia activa (SC-002 < 3 s) y anotar el arranque
   en frío (R13).
4. Probar en Chrome o Edge: en Safari la renovación falla hasta tener dominio propio
   (R5).
5. Reemplazar el valor del secreto `setup-code` por uno aleatorio una vez instalado (`docs/despliegue.md` §9.1); no se destruye, porque Cloud Run lo referencia.

SC-008 (12 horas sin volver a entrar) se valida en local o en Chrome/Edge hasta tener
dominio propio.
