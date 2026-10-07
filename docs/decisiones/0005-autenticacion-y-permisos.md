# ADR-0005: Autenticación y permisos

- **Estado:** Aceptada
- **Fecha:** 2026-10-05
- **Requisitos relacionados:** RF-22, RF-44, RF-45, RF-46, RNF-05, RNF-08, RN-07; principios II y IV

## Contexto

El PRD pide inicio de sesión con usuario y contraseña, un PIN de admin para autorizar
descuentos y permisos por rol verificados en el servidor (RF-44, RNF-05). El módulo de
ventas debe seguir operando si se cae internet con la sesión abierta (RNF-01). La app y
la API se sirven desde dominios distintos (Cloudflare Pages y Cloud Run).

## Decisión

### Credenciales

- Usuario + contraseña, gestionados por FastAPI. No se usa Supabase Auth: está orientado
  a correo y teléfono, y aquí los usuarios son nombres de usuario creados por el admin
  (RF-45).
- Contraseñas y PIN del admin se guardan con **Argon2id**.
- El PIN tiene pocos dígitos y es fácil de adivinar por fuerza bruta. Por eso se limita
  en el servidor: tras 5 intentos fallidos se bloquea temporalmente y cada intento queda
  auditado.

### Sesión

- **Token de acceso:** JWT de vida corta (~15 minutos), enviado en la cabecera
  `Authorization` y guardado solo en memoria.
- **Token de renovación:** opaco, de un solo uso (rota en cada renovación), guardado en
  la base de datos como hash y revocable. Viaja en una cookie `HttpOnly`, `Secure`,
  `SameSite=Strict`.
- Para que esa cookie funcione en todos los navegadores (Safari bloquea las cookies entre
  sitios distintos), **producción usa un dominio propio**, por ejemplo
  `app.<dominio>` y `api.<dominio>`. Mientras no exista, producción solo se usa para
  pruebas (ADR-0002).
- Desactivar un usuario revoca sus tokens de renovación.

### Sesión sin conexión

- Si se cae internet con la sesión abierta, el vendedor sigue vendiendo con la identidad
  de la última sesión válida, hasta un máximo configurable (propuesta: 12 horas desde la
  última validación con el servidor).
- Cada operación de la cola guarda el usuario que la creó y el equipo. Al reconectar,
  la cola se envía con una sesión válida. Si el usuario fue desactivado mientras tanto,
  las ventas se registran igual (ya ocurrieron) y se genera una alerta para el admin.
- Iniciar sesión por primera vez en un equipo requiere conexión.

### Equipos

- El admin registra cada equipo de mostrador (ADR-0003). El equipo recibe un token de
  equipo de larga duración y revocable, que lo identifica y fija su serie de numeración.

### Permisos

- Cada endpoint declara los roles permitidos mediante una dependencia de FastAPI. No hay
  endpoints sin declaración: lo que no declara roles no se expone.
- **Las respuestas se modelan por rol.** Los esquemas de respuesta para Vendedor y
  Almacén no tienen campos de costo ni margen, de modo que no pueden filtrarse por
  descuido (principio IV).
- La base de datos no es accesible desde el navegador: Data API de Supabase desactivada
  (ADR-0001).
- Hay pruebas automatizadas por rol para cada endpoint (principio VII).

### Auditoría (RF-46)

- Las acciones sensibles (cambios de precio, descuentos y su autorización, anulaciones,
  ajustes, tasas, usuarios, intentos de PIN) se registran en una tabla de auditoría, en
  la **misma transacción** que la acción. Si no se puede auditar, la acción no ocurre.

## Alternativas consideradas

- **Supabase Auth:** ahorra código, pero no encaja con usuarios sin correo, divide la
  lógica de identidad entre dos sistemas y Supabase Auth seguiría siendo un punto de
  acceso directo a la base de datos.
- **Token de renovación en IndexedDB o localStorage:** funciona sin dominio propio, pero
  queda expuesto a cualquier script inyectado (XSS).
- **Sesiones de servidor con cookie únicamente:** simple, pero obliga a consultar la base
  de datos en cada petición y complica el uso sin conexión.

## Consecuencias

- El dominio propio deja de ser opcional antes del uso real (~10–15 USD/año, dentro del
  presupuesto de RNF-03).
- Hay que construir y probar con cuidado el inicio de sesión, la renovación y la
  revocación. Es código pequeño pero sensible.
- Un vendedor puede vender hasta 12 horas sin validar su sesión. Es el precio de no
  perder ventas; la auditoría y las alertas lo compensan.
