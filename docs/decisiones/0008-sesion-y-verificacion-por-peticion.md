# ADR-0008: Sesión de jornada y verificación en cada petición

- **Estado:** Aceptada
- **Fecha:** 2026-10-08
- **Requisitos relacionados:** RF-44, RF-45, RF-46, RNF-05, RNF-08; principios II, III y IV;
  complementa ADR-0005 (sigue vigente)

## Contexto

ADR-0005 fijó la autenticación: usuario y contraseña con Argon2id, JWT de acceso corto,
token de renovación rotativo en cookie `HttpOnly` y permisos por rol en cada endpoint. Al
especificar la etapa 1.1a (`specs/001-usuarios-autenticacion-permisos/`) aparecieron
decisiones que ADR-0005 no cubría:

- El dueño definió la sesión como una jornada de 12 horas, una contraseña temporal para
  los usuarios que crea el admin y una instalación protegida con código.
- La especificación exige que desactivar, cambiar el rol o cerrar sesión rijan desde la
  siguiente operación, no al vencer el token de 15 minutos.
- Todavía no hay dominio propio: la app (`*.pages.dev`) y la API (`*.run.app`) son sitios
  distintos y la cookie `SameSite=Strict` de ADR-0005 no viajaría.
- El bloqueo por intentos fallidos no debe revelar qué usuarios existen.

## Decisión

1. **Jornada en `user_session`.** Ingresar la contraseña crea una sesión que vence a las
   12 horas (`expires_at`). El token de renovación rota en cada uso pero nunca extiende
   ese plazo. Si reaparece un token ya rotado hace más de 30 segundos, se revoca la
   jornada entera; dentro de esos 30 segundos se tolera (dos pestañas que renuevan a la
   vez). El frontend serializa la renovación entre pestañas con la Web Locks API.
2. **Verificación en cada petición.** El JWT solo identifica usuario (`sub`) y sesión
   (`sid`). La API lee ambos de la base en cada petición, en una consulta, y aplica el
   rol de la base, no el del token. Rechaza usuarios inactivos, sesiones cerradas o
   vencidas y, salvo en una lista blanca, usuarios con contraseña temporal.
3. **Acceso declarado.** Cada endpoint declara `public()`, `require_authenticated()` o
   `require_roles(...)`; una prueba falla si alguna ruta no lo hace.
4. **Cookie según el ambiente.** `SameSite` y `Secure` son configurables: `lax` sin
   `Secure` en local; `none` con `Secure` en la producción provisional sin dominio propio;
   `strict` con `Secure` cuando exista el dominio (ADR-0005). Las peticiones que usan la
   cookie exigen `Content-Type: application/json`, que obliga a la consulta previa de CORS
   (protección CSRF).
5. **Instalación con código.** El primer admin solo se crea con la base vacía y el código
   del secreto `setup-code`, bajo un bloqueo transaccional. Cinco códigos incorrectos en
   15 minutos bloquean la instalación.
6. **Bloqueo por nombre desde la auditoría.** Los fallos de inicio de sesión se cuentan en
   `audit_log` por nombre de usuario normalizado, exista o no: cinco seguidos bloquean
   ese nombre 15 minutos con la misma respuesta. El PIN, que solo se verifica con
   sesión, usa contadores en `app_user`.

## Alternativas consideradas

- **Aceptar hasta 15 minutos de desfase** al desactivar o cambiar el rol: más simple, pero
  no cumple la especificación (SC-004).
- **Lista de tokens revocados:** también consulta la base y es más difícil de mantener.
- **Sesión deslizante** (cada renovación extiende el plazo): contradice la jornada de 12
  horas que definió el dueño.
- **Contadores de inicio de sesión en `app_user`:** el aviso de bloqueo revelaría qué
  usuarios existen.
- **Proxy de la API dentro de Cloudflare Pages** para tener un solo sitio sin dominio
  propio: agrega una pieza y uso del plan gratuito de Functions; el dominio propio ya es
  requisito antes del uso real (ADR-0005).

## Consecuencias

- Una consulta extra por petición, irrelevante con pocos usuarios.
- Mientras no haya dominio propio, Safari bloquea la cookie entre sitios: allí la sesión no
  se renueva y hay que volver a entrar cada 15 minutos. Producción sin dominio es solo para
  pruebas (ADR-0005); se prueba en Chrome o Edge.
- El secreto `setup-code` sigue referenciado por Cloud Run después de instalar: se
  reemplaza su valor, no se borra (`docs/despliegue.md` §9.1).
- La etapa 1.5 (sin conexión) parte de este diseño: el JWT da la identidad en el equipo y
  la jornada de 12 horas coincide con el límite de trabajo sin conexión de ADR-0005.
