# Despliegue — SHT Gestión

| Campo | Valor |
|---|---|
| Versión | 0.1 |
| Fecha | 2026-10-07 |
| Documentos relacionados | `docs/decisiones/0002-hosting-ambientes-y-presupuesto.md`, `docs/arquitectura.md` §6 |

> Configuración inicial (una sola vez) de los servicios de producción y procedimientos
> de operación. Los valores entre `<>` se reemplazan por los reales. Nada de lo que aquí
> se llama "secreto" se escribe en el repositorio.

## 1. Resumen

| Pieza | Servicio | Nombre | Región |
|---|---|---|---|
| API | Cloud Run | `sht-api` | `us-east4` (Virginia, cerca de Supabase) |
| Imágenes de la API | Artifact Registry | repositorio `sht` | `us-east4` |
| Secreto de conexión de la API | Secret Manager | `database-url` | — |
| Respaldos | Cloud Storage | `sht-respaldos-<sufijo>` | `us-east1` |
| Base de datos y fotos | Supabase | proyecto `sht-gestion` | `us-east-1` (Virginia) |
| App interna | Cloudflare Pages | `sht-app` | — |
| Catálogo | Cloudflare Pages | `sht-catalogo` | — |

**A verificar** al crear cada recurso (ADR-0002): que la región elegida tenga nivel
gratuito para Cloud Run, Artifact Registry y Cloud Storage.

| Workflow | Cuándo corre | Qué hace |
|---|---|---|
| `ci.yml` | Cada PR y push a `main` | Lint, migraciones (subir/bajar/subir) y pruebas del backend; tipos y build del frontend |
| `deploy-api.yml` | Push a `main` que toca `backend/` | Imagen → Artifact Registry → migraciones → Cloud Run → comprobación |
| `deploy-web.yml` | Push a `main` que toca `frontend/`, `catalog/` o `packages/` | Build estático → Cloudflare Pages |
| `backup.yml` | Diario a las 03:00 (Caracas) | `pg_dump` → cifrado con age → Cloud Storage |

Los workflows de despliegue y respaldo **no corren** mientras falten sus variables en
GitHub, así que el repositorio puede existir antes que las cuentas.

## 2. Herramientas locales

| Herramienta | Para qué | Instalación en Windows |
|---|---|---|
| Docker Desktop | Postgres local | `winget install Docker.DockerDesktop` (requiere WSL 2) |
| Google Cloud CLI | Configurar Google Cloud | `winget install Google.CloudSDK` |
| GitHub CLI | Cargar variables y secretos | `winget install GitHub.cli` |
| age | Claves del respaldo | `winget install FiloSottile.age` |

## 3. Supabase

1. Crear el proyecto `sht-gestion` en la región `us-east-1`, plan Free. Guardar la
   contraseña de la base de datos en un gestor de contraseñas.
2. **Desactivar la Data API** en la configuración del proyecto, para que el único acceso
   a los datos sea la API (ADR-0001).
3. En el editor SQL, crear el rol de la API, **sin permiso `DELETE`** (modelo de datos
   §1.4):

   ```sql
   create role sht_api with login password '<contraseña-larga-aleatoria>';
   grant usage on schema public to sht_api;
   alter default privileges for role postgres in schema public
     grant select, insert, update on tables to sht_api;
   alter default privileges for role postgres in schema public
     grant usage, select on sequences to sht_api;
   ```

   Si alguna tabla necesita borrado (por ejemplo, limpieza de tokens vencidos), se le
   concede en su propia migración.
4. Anotar las cadenas de conexión (botón "Connect" del proyecto):
   - **API:** pooler en modo transacción (puerto 6543) con el usuario `sht_api`.
   - **Migraciones y respaldo:** pooler en modo sesión (puerto 5432) con el usuario
     `postgres`. Los runners de GitHub no tienen IPv6, así que no sirve la conexión
     directa.

## 4. Google Cloud

1. Crear el proyecto (por ejemplo `sht-gestion`) y asociarle una cuenta de facturación.
2. **Alerta de presupuesto** (Facturación → Presupuestos y alertas): 5 USD mensuales,
   con aviso por correo al 50 %, 90 % y 100 %.
3. Con la CLI (`gcloud auth login` y `gcloud config set project <proyecto>`):

```bash
PROJECT=<proyecto>
PROJECT_NUMBER=$(gcloud projects describe $PROJECT --format='value(projectNumber)')
REPO=sherzo/sht-gestion

gcloud services enable run.googleapis.com artifactregistry.googleapis.com \
  secretmanager.googleapis.com iamcredentials.googleapis.com storage.googleapis.com

# Imágenes de la API, conservando solo las 5 más recientes.
gcloud artifacts repositories create sht --repository-format=docker --location=us-east4
cat > cleanup.json <<'EOF'
[{"name": "conservar-5", "action": {"type": "Keep"}, "mostRecentVersions": {"keepCount": 5}},
 {"name": "borrar-resto", "action": {"type": "Delete"}, "condition": {"tagState": "ANY"}}]
EOF
gcloud artifacts repositories set-cleanup-policies sht --location=us-east4 \
  --policy=cleanup.json --no-dry-run

# Cuentas de servicio: una para ejecutar la API y otra para desplegar desde GitHub.
gcloud iam service-accounts create sht-api-runtime --display-name="API en Cloud Run"
gcloud iam service-accounts create sht-deployer --display-name="Despliegue desde GitHub"
RUNTIME_SA=sht-api-runtime@$PROJECT.iam.gserviceaccount.com
DEPLOY_SA=sht-deployer@$PROJECT.iam.gserviceaccount.com

# Secreto con la cadena de conexión de la API (pooler en modo transacción, usuario sht_api).
printf '%s' 'postgresql+psycopg://<usuario>:<contraseña>@<host>:6543/postgres' | \
  gcloud secrets create database-url --data-file=-
gcloud secrets add-iam-policy-binding database-url \
  --member="serviceAccount:$RUNTIME_SA" --role=roles/secretmanager.secretAccessor

# Permisos de la cuenta de despliegue.
gcloud projects add-iam-policy-binding $PROJECT --member="serviceAccount:$DEPLOY_SA" --role=roles/run.admin
gcloud projects add-iam-policy-binding $PROJECT --member="serviceAccount:$DEPLOY_SA" --role=roles/artifactregistry.writer
gcloud iam service-accounts add-iam-policy-binding $RUNTIME_SA \
  --member="serviceAccount:$DEPLOY_SA" --role=roles/iam.serviceAccountUser

# Bucket de respaldos: borra copias de más de 30 días.
BUCKET=sht-respaldos-<sufijo>
gcloud storage buckets create gs://$BUCKET --location=us-east1 --uniform-bucket-level-access
echo '{"rule": [{"action": {"type": "Delete"}, "condition": {"age": 30}}]}' > lifecycle.json
gcloud storage buckets update gs://$BUCKET --lifecycle-file=lifecycle.json
gcloud storage buckets add-iam-policy-binding gs://$BUCKET \
  --member="serviceAccount:$DEPLOY_SA" --role=roles/storage.objectCreator

# GitHub Actions se autentica sin claves (Workload Identity Federation), solo desde este repositorio.
gcloud iam workload-identity-pools create github --location=global --display-name="GitHub"
gcloud iam workload-identity-pools providers create-oidc sht-repo \
  --location=global --workload-identity-pool=github \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository=='$REPO'"
gcloud iam service-accounts add-iam-policy-binding $DEPLOY_SA \
  --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github/attribute.repository/$REPO"
```

## 5. Cloudflare

1. Crear la cuenta y dos proyectos de Pages con subida directa: `sht-app` y
   `sht-catalogo`.
2. Crear un token de API con el permiso **Cuenta → Cloudflare Pages → Editar**.
3. Anotar el ID de la cuenta.
4. **A verificar:** que los términos del plan Free permitan uso comercial (ADR-0002).

## 6. Clave de los respaldos

```bash
age-keygen -o sht-respaldo.key
```

- La línea `public key: age1…` va a GitHub como `AGE_PUBLIC_KEY`.
- El archivo `sht-respaldo.key` es la **única** forma de leer los respaldos: se guarda en
  el gestor de contraseñas y en una copia fuera del computador. Nunca se sube al
  repositorio ni a la nube junto a los respaldos.

## 7. Variables y secretos de GitHub

En el repositorio: Settings → Secrets and variables → Actions (o con `gh variable set` /
`gh secret set`).

| Tipo | Nombre | Valor |
|---|---|---|
| Variable | `GCP_PROJECT_ID` | ID del proyecto de Google Cloud |
| Variable | `GCP_REGION` | `us-east4` |
| Variable | `GCP_WIF_PROVIDER` | `projects/<número>/locations/global/workloadIdentityPools/github/providers/sht-repo` |
| Variable | `GCP_DEPLOY_SA` | `sht-deployer@<proyecto>.iam.gserviceaccount.com` |
| Variable | `GCP_RUNTIME_SA` | `sht-api-runtime@<proyecto>.iam.gserviceaccount.com` |
| Variable | `API_URL` | URL de Cloud Run (tras el primer despliegue) o `https://api.<dominio>` |
| Variable | `CORS_ORIGINS` | `https://sht-app.pages.dev` (o `https://app.<dominio>`) |
| Variable | `BACKUP_BUCKET` | `sht-respaldos-<sufijo>` |
| Variable | `AGE_PUBLIC_KEY` | Clave pública de age |
| Variable | `CLOUDFLARE_ACCOUNT_ID` | ID de la cuenta de Cloudflare |
| Variable | `CF_PAGES_APP_PROJECT` | `sht-app` |
| Variable | `CF_PAGES_CATALOG_PROJECT` | `sht-catalogo` |
| Secreto | `MIGRATIONS_DATABASE_URL` | `postgresql+psycopg://postgres.<ref>:<contraseña>@<host>:5432/postgres` |
| Secreto | `BACKUP_DATABASE_URL` | La misma conexión, con prefijo `postgresql://` |
| Secreto | `CLOUDFLARE_API_TOKEN` | Token de Cloudflare |

Orden recomendado: primero las variables de Google Cloud y los secretos de base de datos
(despliega la API), luego `API_URL` y `CORS_ORIGINS` con la URL obtenida, y por último
Cloudflare (despliega la app, que ya sabe dónde está la API).

## 8. Restaurar un respaldo

El respaldo contiene solo el esquema `public` (los datos del sistema). Los esquemas
internos de Supabase no se copian. **Las fotos de Supabase Storage no entran en este
respaldo**; cómo respaldarlas se decide en la etapa 1.1b, cuando existan.

Se prueba al cierre de cada etapa (plan de fases, definición de terminado):

```bash
gcloud storage cp gs://<bucket>/<archivo>.dump.age .
age --decrypt --identity sht-respaldo.key --output respaldo.dump <archivo>.dump.age
docker compose up -d
docker compose exec -T db createdb -U sht sht_restaurada
docker compose exec -T db pg_restore -U sht --no-owner -d sht_restaurada < respaldo.dump
```
