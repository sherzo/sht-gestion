# ADR-0009: Fotos de productos

- **Estado:** Aceptada
- **Fecha:** 2026-10-13
- **Requisitos relacionados:** RF-01, RF-07, RNF-03, RNF-05, RNF-06; principios IV y VI;
  aplica ADR-0002 (Supabase como almacenamiento de fotos)

## Contexto

La etapa 1.1b (`specs/002-productos-inventario/`, FR-008) agrega hasta 5 fotos por
producto, que usará el catálogo online (etapa 1.6). ADR-0002 ya eligió Supabase Storage
para guardarlas, pero quedaban abiertos cómo llegan las fotos, en qué formato se guardan,
quién tiene la clave de Storage y cómo se respaldan:

- Las fotos de teléfono pesan de 3 a 8 MB; con 1.000 productos el plan gratuito
  (1 GB de Storage) se agotaría rápido.
- Safari no genera WebP desde el navegador.
- La clave de Storage permite escribir cualquier archivo: no puede llegar al navegador.
- El respaldo diario (`backup.yml`) solo copiaba la base de datos.

## Decisión

1. **Subida a través de la API.** El navegador reduce la foto a 1.600 px de lado mayor
   (JPEG por canvas, que funciona en todos los navegadores) y la envía en
   `multipart/form-data` a `POST /products/{id}/photos`. La API verifica el permiso
   (Admin y Almacén), el tamaño (máximo 5 MB recibidos) y el tipo real con Pillow (JPEG,
   PNG o WebP), y rechaza imágenes de más de 50 megapíxeles.
2. **Normalización a WebP.** Pillow corrige la orientación según el EXIF, reduce a
   1.200 px de lado mayor y guarda WebP con calidad 80, **sin metadatos** (el EXIF puede
   llevar la ubicación del teléfono). Conserva la transparencia de los PNG. Resultado:
   ~100–200 KB por foto.
3. **Bucket público con rutas no adivinables.** `product-photos` en Supabase Storage, ruta
   `products/{producto}/{foto}.webp` con UUIDv7. La app y el catálogo usan la URL pública:
   las fotos no son información sensible porque se publican en el catálogo.
4. **Clave solo en el servidor.** La API escribe con la API REST de Storage (`httpx`) y la
   clave secreta del proyecto, guardada en Secret Manager como `supabase-storage-key`.
   En desarrollo y pruebas las fotos van a disco (`PHOTO_STORAGE=local`) y la API las
   sirve en `/media`; en staging y producción ese modo está prohibido.
5. **Quitar no borra filas.** Quitar una foto marca `removed_at` en `product_photo` y
   borra el objeto de Storage. Máximo 5 fotos activas por producto.
6. **Respaldo con rclone.** `backup.yml` copia cada noche las fotos nuevas (protocolo S3
   de Supabase Storage) a `gs://sht-gestion-respaldos/fotos/`. Como una foto nunca cambia,
   `rclone copy --immutable` solo sube las nuevas y falla si alguna cambiara. La regla de
   borrado a los 30 días del bucket se limita a los volcados (`matchesPrefix: ["sht-"]`):
   las fotos se conservan, aun las que se quitaron del producto.

## Alternativas consideradas

- **Subida directa del navegador a Storage con URL firmada:** ahorra un salto, pero la
  validación del tipo real y la normalización quedarían fuera del control del servidor.
- **Comprimir solo en el navegador:** Safari no exporta WebP, y una imagen mal formada o
  con EXIF llegaría tal cual.
- **Bucket privado con URL firmadas:** complica el catálogo estático y su caché sin
  proteger nada sensible.
- **`rclone sync`:** borraría del respaldo las fotos quitadas; se prefiere conservarlas.

## Consecuencias

- 1.000 productos con 3 fotos ocupan ~0,5 GB: dentro de Supabase Free. Al pasar del 70 %
  del límite rige el criterio de ADR-0002 para contratar Supabase Pro.
- La API procesa imágenes: Pillow agrega memoria por petición (~50 MB con una foto de 50
  megapíxeles), dentro de los 512 MB de Cloud Run.
- La cuenta de despliegue necesita listar y leer el bucket de respaldos para que rclone
  sepa qué fotos ya copió (`storage.objectViewer`); sigue sin poder borrar ni
  sobrescribir. Los volcados de la base siguen cifrados con age.
- Configuración nueva: bucket, secreto `supabase-storage-key`, variables `SUPABASE_URL`,
  `SUPABASE_S3_ENDPOINT` y `SUPABASE_S3_REGION`, y claves S3 en GitHub
  (`docs/despliegue.md` §3, §4 y §7).
