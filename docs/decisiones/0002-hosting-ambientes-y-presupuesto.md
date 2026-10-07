# ADR-0002: Hosting, ambientes y presupuesto

- **Estado:** Aceptada
- **Fecha:** 2026-10-05
- **Requisitos relacionados:** RNF-03, RNF-06, RF-38; principios III y VI

## Contexto

RNF-03 fija que la producción arranca en planes gratuitos y que el presupuesto máximo de
infraestructura es de 35–40 USD/mes, con cada servicio pago justificado en un ADR. El
stack (ADR-0001) tiene cuatro piezas que alojar: la API (FastAPI), la base de datos y
las fotos (Supabase), la app interna estática y el catálogo estático.

## Decisión

### Proveedores

| Pieza | Proveedor | Plan inicial |
|---|---|---|
| API FastAPI | Google Cloud Run (contenedor, escala a cero) | Nivel gratuito |
| Postgres + fotos | Supabase | Free |
| App interna y catálogo | Cloudflare Pages (dos proyectos) | Free |
| CI, respaldo, regeneración del catálogo | GitHub Actions | Incluido |
| Copias de respaldo | Bucket de Google Cloud Storage | Nivel gratuito |

- La API y la base de datos se ubican en la misma zona geográfica (este de EE. UU.) para
  reducir la latencia entre ambas. La región exacta de Cloud Run se fija al configurarla,
  verificando que aplique el nivel gratuito.
- No se usa Vercel: su plan Hobby está restringido a uso personal no comercial.

### Límites conocidos de los planes gratuitos

Verificados el 2026-10-05 en la página de precios de Supabase:

- Free: 500 MB de base de datos, 1 GB de almacenamiento de archivos, 5 GB de egreso,
  2 proyectos activos, **sin respaldos** y **pausa tras 1 semana de inactividad**.
- Pro: desde 25 USD/mes, respaldos diarios con 7 días de retención, sin pausa por
  inactividad, 8 GB de disco por proyecto.

**A verificar** al configurar cada servicio: las cifras vigentes del nivel gratuito de
Cloud Run, Cloud Storage y Artifact Registry (donde se guardan las imágenes de la API,
con una política que conserve solo las últimas), y que los términos de Cloudflare Pages
Free permitan el uso comercial.

### Ambientes

| Ambiente | Uso | Infraestructura | Cuándo |
|---|---|---|---|
| **Local** | Desarrollo | Docker Compose con Postgres; FastAPI y Next.js en modo desarrollo | Desde la etapa 1.0 |
| **Producción** | El negocio | Proveedores de la tabla anterior | Desde la etapa 1.0 |
| **Pruebas (staging)** | Probar cada versión en el equipo real del mostrador antes de publicarla | Copia de producción: segundo proyecto gratuito de Supabase, otro servicio Cloud Run y otro proyecto Pages | Cuando el negocio empiece a usar el sistema con datos reales |

- El mismo código y la misma imagen de contenedor corren en todos los ambientes; solo
  cambia la configuración, mediante variables de entorno y secretos. Subir de plan es un
  cambio de configuración, nunca de código.
- Nunca se desarrolla contra la base de datos de producción.
- Mientras el negocio no use el sistema con datos reales, producción hace también de
  ambiente de pruebas.

### Presupuesto y criterios para subir de plan

| Gasto | Costo aproximado | Se activa cuando |
|---|---|---|
| Dominio propio | ~10–15 USD/año | Antes del uso real del negocio: lo requiere el manejo de sesión (ADR-0005) y da una URL estable al catálogo |
| Supabase Pro | 25 USD/mes | Ocurre cualquiera de estas cosas: base de datos o fotos sobre ~70 % del límite gratuito; el proyecto se pausa una vez; el dueño decide contar con respaldos administrados |
| Cloud Run con una instancia siempre activa | A verificar | Se mide que el arranque en frío afecta la operación en línea de forma real (no solo se percibe) |

Todo junto debe caber en 35–40 USD/mes. Cualquier otro gasto requiere un ADR nuevo.

### Protecciones contra sorpresas

- Cloud Run exige asociar una cuenta de facturación incluso dentro del nivel gratuito.
  Se configura desde el primer día una **alerta de presupuesto** en Google Cloud
  (por ejemplo a 5 USD) con aviso por correo.
- Las fotos se comprimen en el navegador antes de subirlas (por ejemplo WebP, lado mayor
  de 1.200 px) para cuidar el almacenamiento y el egreso.
- El catálogo copia las fotos optimizadas dentro de su build, de modo que el tráfico del
  catálogo lo sirve Cloudflare y no consume el egreso de Supabase.

### Respaldo diario (RNF-06)

- Un workflow programado de GitHub Actions ejecuta `pg_dump` cada día, cifra la copia y
  la sube al bucket de Cloud Storage, con una regla de ciclo de vida que conserva las
  últimas 30 copias diarias.
- Corre desde el primer día, aunque luego se contrate Supabase Pro: es una copia fuera
  del proveedor de la base de datos.
- La restauración se prueba al cierre de cada etapa de la Fase 1, restaurando en el
  ambiente local.
- Un fallo del workflow notifica por correo al dueño del repositorio.
- Riesgo: en repositorios públicos, GitHub desactiva los workflows programados tras 60
  días sin actividad en el repositorio. Si el repositorio es público, se vigila esa
  condición.

## Alternativas consideradas

- **Render (gratuito) para la API:** se duerme a los 15 minutos y tarda 30–60 s en
  despertar.
- **VPS pequeño (~5 USD/mes):** sin arranque en frío, pero hay que mantener el sistema
  operativo, la seguridad y los despliegues.
- **Vercel para el frontend:** el plan gratuito no permite uso comercial y el plan Pro
  consumiría buena parte del presupuesto.
- **Ambiente de pruebas desde el día uno:** duplica la configuración sin beneficio
  mientras no haya datos reales que proteger.

## Consecuencias

- Costo inicial de 0 USD, con un camino claro y medible hacia los planes pagos.
- El arranque en frío de Cloud Run puede añadir unos segundos a la primera petición tras
  un rato sin uso. La cola de ventas sin conexión (ADR-0003) evita que eso bloquee una
  venta.
- Mientras se use Supabase Free, la única copia de respaldo es la propia: probar la
  restauración no es opcional.
- La pausa por inactividad de Supabase Free es un riesgo en cierres largos del negocio
  (por ejemplo vacaciones). Es uno de los criterios para pasar a Pro.
