# Despliegue — SHT Gestión

| Campo | Valor |
|---|---|
| Versión | 0.2 |
| Fecha | 2026-10-07 |
| Documentos relacionados | `docs/decisiones/0002-hosting-ambientes-y-presupuesto.md`, `docs/arquitectura.md` §6 |

> Configuración inicial (una sola vez) de los servicios de producción y procedimientos
> de operación. Los valores entre `<>` se reemplazan por los reales. Nada de lo que aquí
> se llama "secreto" se escribe en el repositorio ni se pega en conversaciones.

## 1. Resumen

| Pieza | Servicio | Nombre | Región |
|---|---|---|---|
| API | Cloud Run | `sht-api` → https://sht-api-wilmjh5geq-uk.a.run.app | `us-east4` (Virginia, cerca de Supabase) |
| Imágenes de la API | Artifact Registry | repositorio `sht` (conserva las 5 más recientes) | `us-east4` |
| Secreto de conexión de la API | Secret Manager | `database-url` | — |
| Respaldos | Cloud Storage | `sht-gestion-respaldos` (borra a los 30 días) | `us-east1` |
| Base de datos y fotos | Supabase | proyecto `sht-gestion` | `us-east-1` (Virginia) |
| App interna | Cloudflare Pages | `sht-gestion-app` | — |
| Catálogo | Cloudflare Pages | `sht-gestion-catalogo` | — |

Proyecto de Google Cloud: `sht-gestion` (número `10222744454`).

**A verificar** (ADR-0002): que las regiones elegidas mantengan nivel gratuito para Cloud
Run, Artifact Registry y Cloud Storage, y que el plan Free de Cloudflare Pages permita uso
comercial.

| Workflow | Cuándo corre | Qué hace |
|---|---|---|
| `ci.yml` | Cada PR y push a `main` | Lint, migraciones (subir/bajar/subir) y pruebas del backend; tipos y build del frontend |
| `deploy-api.yml` | Push a `main` que toca `backend/`, o a mano | Imagen → Artifact Registry → migraciones → Cloud Run → comprobación |
| `deploy-web.yml` | Push a `main` que toca `frontend/`, `catalog/` o `packages/`, o a mano | Build estático → crea los proyectos de Pages si faltan → Cloudflare Pages |
| `backup.yml` | Diario a las 03:00 (Caracas), o a mano | `pg_dump` → cifrado con age → Cloud Storage |

Los workflows de despliegue y respaldo **no corren** mientras falten sus variables en
GitHub. Para lanzarlos a mano: `gh workflow run <archivo> -R sherzo/sht-gestion`.

## 2. Herramientas locales

| Herramienta | Para qué | Instalación en Windows |
|---|---|---|
| Docker Desktop | Postgres local | `winget install Docker.DockerDesktop` (requiere WSL 2) |
| Google Cloud CLI | Configurar Google Cloud | `winget install Google.CloudSDK` |
| GitHub CLI | Cargar variables y lanzar workflows | `winget install GitHub.cli` |
| age | Claves del respaldo | `winget install FiloSottile.age` |

**Particularidades en Windows** (aprendidas al configurar):

- Tras instalar, hay que reiniciar **toda** la aplicación desde la que se abre la terminal
  (por ejemplo VS Code), no solo la terminal, para que el PATH incluya las herramientas.
- En Git Bash, usar **`gcloud.cmd`**: el `gcloud` sin extensión busca un `python` del
  sistema y falla. `gcloud.cmd` usa el Python que trae el SDK.
- `gcloud.cmd` falla con argumentos que tienen espacios o tildes (por ejemplo
  `--display-name="API en Cloud Run"`). Usar valores sin espacios, o pasar las opciones en
  un archivo con `--flags-file`.
- `gh auth login` guarda la sesión en el almacén de credenciales de Windows; se comprueba
  con `gh auth status`.

## 3. Supabase

1. Crear el proyecto `sht-gestion` en la región `us-east-1`, plan Free. Guardar la
   contraseña de la base de datos (usuario `postgres`) en un gestor de contraseñas.
2. **Desactivar la Data API** en la configuración del proyecto, para que el único acceso
   a los datos sea la API (ADR-0001).
3. Generar la contraseña del rol de la API en una terminal propia (64 caracteres
   hexadecimales, sin símbolos que rompan la cadena de conexión):

   ```powershell
   $b = New-Object byte[] 32; [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b); -join ($b | ForEach-Object { $_.ToString('x2') })
   ```

4. En el editor SQL, crear el rol de la API, **sin permiso `DELETE`** (modelo de datos
   §1.4), reemplazando la contraseña antes de ejecutar:

   ```sql
   create role sht_api with login password '<contraseña-generada>';
   grant usage on schema public to sht_api;
   alter default privileges for role postgres in schema public
     grant select, insert, update on tables to sht_api;
   alter default privileges for role postgres in schema public
     grant usage, select on sequences to sht_api;
   ```

   Si se ejecutó con la contraseña de ejemplo: `alter role sht_api with password '<nueva>';`.
   Si alguna tabla necesita borrado (por ejemplo, limpieza de tokens vencidos), se le
   concede en su propia migración.
5. Cadenas de conexión: botón **Connect** del proyecto, selector **Method**:

   | Uso | Method | Puerto | Usuario |
   |---|---|---|---|
   | API (secreto `database-url`) | Transaction pooler | 6543 | `sht_api.<ref>` |
   | Migraciones y respaldo (secretos de GitHub) | Session pooler | 5432 | `postgres.<ref>` |

   - El host termina en `.pooler.supabase.com`. La **conexión directa**
     (`db.<ref>.supabase.co`) no sirve: en el plan Free solo funciona por IPv6, que ni
     Cloud Run ni GitHub Actions tienen.
   - El prefijo puede quedar como `postgresql://`: SQLAlchemy 2.1 usa psycopg (v3) por
     defecto, y `pg_dump` exige justamente ese formato.

## 4. Google Cloud

1. Crear el proyecto `sht-gestion` y asociarle una cuenta de facturación.
2. **Alerta de presupuesto** (Facturación → Presupuestos y alertas,
   https://console.cloud.google.com/billing/budgets): 5 USD mensuales sobre el proyecto,
   sin incluir créditos de prueba, con aviso por correo al 50 %, 90 % y 100 %. La alerta
   avisa pero no corta el gasto; el límite real es `--max-instances 2` en Cloud Run.
3. Con la CLI (`gcloud.cmd auth login` y `gcloud.cmd config set project sht-gestion`).
   En Git Bash, reemplazar `gcloud` por `gcloud.cmd`:

```bash
PROJECT=sht-gestion
PROJECT_NUMBER=$(gcloud projects describe $PROJECT --format='value(projectNumber)')
REPO=sherzo/sht-gestion
RUNTIME_SA=sht-api-runtime@$PROJECT.iam.gserviceaccount.com
DEPLOY_SA=sht-deployer@$PROJECT.iam.gserviceaccount.com

gcloud services enable run.googleapis.com artifactregistry.googleapis.com \
  secretmanager.googleapis.com iamcredentials.googleapis.com storage.googleapis.com \
  sts.googleapis.com

# Imágenes de la API, conservando solo las 5 más recientes.
gcloud artifacts repositories create sht --repository-format=docker --location=us-east4
cat > cleanup.json <<'EOF'
[{"name": "conservar-5", "action": {"type": "Keep"}, "mostRecentVersions": {"keepCount": 5}},
 {"name": "borrar-resto", "action": {"type": "Delete"}, "condition": {"tagState": "ANY"}}]
EOF
gcloud artifacts repositories set-cleanup-policies sht --location=us-east4 \
  --policy=cleanup.json --no-dry-run

# Cuentas de servicio: una para ejecutar la API y otra para desplegar desde GitHub.
gcloud iam service-accounts create sht-api-runtime --display-name=sht-api-runtime
gcloud iam service-accounts create sht-deployer --display-name=sht-deployer

# Permisos de la cuenta de despliegue. Si alguno falla con "does not exist", es la demora
# de propagación de una cuenta recién creada: repetir el comando.
gcloud projects add-iam-policy-binding $PROJECT --member="serviceAccount:$DEPLOY_SA" --role=roles/run.admin --condition=None
gcloud projects add-iam-policy-binding $PROJECT --member="serviceAccount:$DEPLOY_SA" --role=roles/artifactregistry.writer --condition=None
gcloud iam service-accounts add-iam-policy-binding $RUNTIME_SA \
  --member="serviceAccount:$DEPLOY_SA" --role=roles/iam.serviceAccountUser

# Bucket de respaldos: sin acceso público y borra copias de más de 30 días.
BUCKET=sht-gestion-respaldos
gcloud storage buckets create gs://$BUCKET --location=us-east1 \
  --uniform-bucket-level-access --public-access-prevention
echo '{"rule": [{"action": {"type": "Delete"}, "condition": {"age": 30}}]}' > lifecycle.json
gcloud storage buckets update gs://$BUCKET --lifecycle-file=lifecycle.json
gcloud storage buckets add-iam-policy-binding gs://$BUCKET \
  --member="serviceAccount:$DEPLOY_SA" --role=roles/storage.objectCreator

# GitHub Actions se autentica sin claves (Workload Identity Federation), solo desde este
# repositorio. Las opciones con comillas van en un archivo por el problema de gcloud.cmd.
cat > wif-provider.yaml <<'EOF'
--location: global
--workload-identity-pool: github
--issuer-uri: https://token.actions.githubusercontent.com
--attribute-mapping: google.subject=assertion.sub,attribute.repository=assertion.repository
--attribute-condition: assertion.repository=='sherzo/sht-gestion'
EOF
gcloud iam workload-identity-pools create github --location=global --display-name=GitHub
gcloud iam workload-identity-pools providers create-oidc sht-repo --flags-file=wif-provider.yaml
gcloud iam service-accounts add-iam-policy-binding $DEPLOY_SA \
  --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github/attribute.repository/$REPO"
```

4. **Secreto `database-url`**, desde la consola web (Seguridad → Secret Manager,
   https://console.cloud.google.com/security/secret-manager?project=sht-gestion), con la
   cadena del Transaction pooler (§3). Para cambiarla: **+ Nueva versión**, nunca borrar y
   recrear el secreto (se pierde el permiso de abajo), y luego destruir la versión vieja.
5. Dar a la API permiso de lectura del secreto:

```bash
gcloud secrets add-iam-policy-binding database-url \
  --member="serviceAccount:$RUNTIME_SA" --role=roles/secretmanager.secretAccessor
```

## 5. Cloudflare

1. Crear la cuenta en cloudflare.com y anotar el **ID de la cuenta** (Workers & Pages →
   panel derecho "Account ID"). No es secreto.
2. Crear un token de API (My Profile → API Tokens → Create Token → Custom token):
   - Permiso: **Account → Cloudflare Pages → Edit**.
   - Account Resources: la cuenta propia.
3. Guardarlo directamente como secreto `CLOUDFLARE_API_TOKEN` en GitHub (§7). No hace
   falta crear los proyectos de Pages: `deploy-web.yml` los crea si no existen.

## 6. Clave de los respaldos

```bash
age-keygen -o sht-respaldo.key
```

- Generarla **fuera del repositorio**. La línea `Public key: age1…` va a GitHub como
  `AGE_PUBLIC_KEY`.
- El archivo `sht-respaldo.key` es la **única** forma de leer los respaldos: se guarda en
  el gestor de contraseñas y en una copia fuera del computador. Nunca se sube al
  repositorio ni a la nube junto a los respaldos.

## 7. Variables y secretos de GitHub

En el repositorio: Settings → Secrets and variables → Actions, o con `gh variable set` /
`gh secret set`.

| Tipo | Nombre | Valor |
|---|---|---|
| Variable | `GCP_PROJECT_ID` | `sht-gestion` |
| Variable | `GCP_REGION` | `us-east4` |
| Variable | `GCP_WIF_PROVIDER` | `projects/10222744454/locations/global/workloadIdentityPools/github/providers/sht-repo` |
| Variable | `GCP_DEPLOY_SA` | `sht-deployer@sht-gestion.iam.gserviceaccount.com` |
| Variable | `GCP_RUNTIME_SA` | `sht-api-runtime@sht-gestion.iam.gserviceaccount.com` |
| Variable | `API_URL` | `https://sht-api-wilmjh5geq-uk.a.run.app` (luego `https://api.<dominio>`) |
| Variable | `CORS_ORIGINS` | `https://sht-gestion-app.pages.dev` (luego `https://app.<dominio>`) |
| Variable | `BACKUP_BUCKET` | `sht-gestion-respaldos` |
| Variable | `AGE_PUBLIC_KEY` | Clave pública de age |
| Variable | `CLOUDFLARE_ACCOUNT_ID` | ID de la cuenta de Cloudflare |
| Variable | `CF_PAGES_APP_PROJECT` | `sht-gestion-app` |
| Variable | `CF_PAGES_CATALOG_PROJECT` | `sht-gestion-catalogo` |
| Secreto | `MIGRATIONS_DATABASE_URL` | Cadena del Session pooler (§3) |
| Secreto | `BACKUP_DATABASE_URL` | La misma cadena |
| Secreto | `CLOUDFLARE_API_TOKEN` | Token de Cloudflare |

Orden: primero las variables de Google Cloud y los secretos de base de datos (despliega la
API), luego `API_URL` con la URL obtenida, y por último Cloudflare y `CORS_ORIGINS`
(despliega la app, que ya sabe dónde está la API). Al cambiar `CORS_ORIGINS` hay que
volver a desplegar la API para que la tome.

## 8. Restaurar un respaldo

El respaldo contiene solo el esquema `public` (los datos del sistema). Los esquemas
internos de Supabase no se copian. **Las fotos de Supabase Storage no entran en este
respaldo**; cómo respaldarlas se decide en la etapa 1.1b, cuando existan.

Se prueba al cierre de cada etapa (plan de fases, definición de terminado). La cuenta de
despliegue solo puede subir respaldos; leerlos requiere la cuenta propia del dueño:

```bash
gcloud storage cp gs://sht-gestion-respaldos/<archivo>.dump.age .
age --decrypt --identity sht-respaldo.key --output respaldo.dump <archivo>.dump.age
docker compose up -d
docker compose exec -T db createdb -U sht sht_restaurada
docker compose exec -T db pg_restore -U sht --no-owner -d sht_restaurada < respaldo.dump
```
