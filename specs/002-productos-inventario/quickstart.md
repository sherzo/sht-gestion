# Guía de validación: productos, categorías e inventario

Escenarios para comprobar de punta a punta que la etapa 1.1b cumple la especificación.
Endpoints, errores y permisos: `contracts/api.md`. Tablas y estados: `data-model.md`.
Decisiones: `research.md`.

## Preparación local

```bash
docker compose up -d                      # Postgres 17
cd backend
uv sync                                   # agrega Pillow y httpx (R9)
uv run alembic upgrade head               # incluye 0004_productos_e_inventario
uv run uvicorn app.main:app --reload      # http://localhost:8000
# en otra terminal, desde la raíz
pnpm install
pnpm api:types                            # regenera los tipos del OpenAPI
pnpm dev:app                              # http://localhost:3000
```

Variables nuevas del backend (`backend/.env`):

| Variable | Local | Producción |
|---|---|---|
| `PHOTO_STORAGE` | `local` (fotos en `backend/.media/`, servidas en `/media`) | `supabase` |
| `SUPABASE_URL` | — | URL del proyecto |
| `SUPABASE_STORAGE_KEY` | — | Secreto `supabase-storage-key` en Secret Manager |
| `PHOTO_BUCKET` | — | `product-photos` (público) |

Usuarios de prueba: el Admin de la instalación (etapa 1.1a), un Vendedor y un Almacén
creados desde **Usuarios**.

## Pruebas automatizadas

```bash
cd backend
uv run ruff check . && uv run ruff format --check .
uv run pytest                             # con DATABASE_URL: incluye las pruebas db
# desde la raíz
pnpm typecheck && pnpm build
```

Pruebas clave de la etapa (todas referencian su FR/RN):

| Prueba | Verifica |
|---|---|
| `test_units_domain.py` | Decimales por unidad, cero, negativos (FR-020, sin base de datos) |
| `test_attributes_domain.py` | Obligatorios, tipos, opciones activas y desactivadas (FR-006) |
| `test_search_domain.py` | Normalización sin acentos ni mayúsculas (FR-032) |
| `test_sku.py` | Formato, correlativo, sin reutilizar, 20 altas simultáneas (FR-002, SC-006) |
| `test_stock_movements.py` | Saldo, inmutabilidad, trigger contra escritura directa del stock (FR-016, FR-017, FR-021) |
| `test_adjustments.py` | Inmediatos, pendientes, aprobación con revalidación, rechazo, retiro (FR-019, FR-019a) |
| `test_stock_counts.py` | Estados, a ciegas, diferencia al anotar, aplicar con saldo negativo, conteos simultáneos (FR-024 a FR-027) |
| `test_products.py` | Alta, edición, restricciones con movimientos, unidad fija, desactivar y publicar (FR-001 a FR-010) |
| `test_prices_costs.py` | Historial de precios, costo inicial y `cost_locked` (FR-011 a FR-013) |
| `test_photos.py` | Normalización a WebP, límites, quitar y ordenar (FR-008) |
| `test_no_cost_leak.py` | Ninguna respuesta a Vendedor o Almacén con costos; ninguna al Almacén con precio (FR-014, SC-004) |
| `test_permissions_matrix.py` | Filas nuevas de la matriz del contrato (SC-004) |
| `test_search_performance.py` | 1.000 productos, búsqueda < 200 ms en el servidor (SC-001) |
| `test_audit.py` | Acciones de R14 con valores antes y después (FR-034, SC-007) |

## Escenarios manuales

1. **Estructura inicial (US6):** como Admin, abrir **Configuración → Categorías**: están
   Mangueras (`MAN`, metro fijo), Conexiones, Ferrules y Ferretería con sus atributos;
   en **Unidades**, metro (2 decimales) y unidad (0).
2. **Alta por Almacén (US1):** como Almacén, crear "Manguera R2 1/2"" con tipo R2 y
   diámetro 1/2". Recibe `MAN-0001`, unidad metro, stock 0. No aparece ningún campo de
   precio ni costo, ni el botón de publicar. Intentar elegir "unidad" como unidad: no se
   puede.
3. **Precio, costo y publicación (US4):** como Admin, abrir la ficha, fijar 12,50 USD,
   luego 13,00 USD: el historial muestra ambos y la auditoría los dos cambios. Fijar
   costo inicial 7,25. Publicar: queda publicado. Como Vendedor, la ficha muestra 13,00
   y no el costo; como Almacén, ni precio ni costo.
4. **Fotos (US1):** subir una foto de 4 MB tomada con el teléfono: queda en WebP,
   orientada, y es la principal. Subir 5 más: la sexta se rechaza. Reordenar y quitar
   una.
5. **Ajustes (US2):** como Admin, ajuste +10 por corrección a `MAN-0001`: stock 10,00.
   Como Almacén, −2 por daño: queda pendiente, el stock sigue en 10,00 y el Admin lo ve
   en **Pendientes**. Aprobar: stock 8,00, el kardex muestra quién solicitó y quién
   aprobó. Otra solicitud de −3: rechazarla con motivo; el Almacén ve el motivo en
   **Mis solicitudes**. Intentar −0,305 m: se rechaza.
6. **Kardex por rol:** como Vendedor, la ficha no ofrece el kardex y la API responde
   403 en `GET /products/{id}/movements`.
7. **Conteo a ciegas (US5):** como Almacén, abrir un conteo de Ferrules, anotar dos
   productos con cantidades distintas a las del sistema y uno igual; la pantalla no
   muestra el stock del sistema. Marcar "listo para revisión" e intentar aplicarlo: no
   puede. Como Admin, ver las diferencias y aplicar: se generan exactamente dos ajustes
   con motivo "conteo físico".
8. **Conteos simultáneos:** con un conteo abierto de Ferrules, intentar abrir otro de
   todo el inventario: se rechaza indicando los productos en conflicto.
9. **Stock bajo (US3):** poner stock mínimo 10 a `MAN-0001` (stock 8,00): aparece en
   **Stock bajo** y en la tarjeta del inicio de Admin y Almacén.
10. **Búsqueda (US3, SC-001):** con los 1.000 productos de prueba cargados
    (`uv run python -m app.cli seed-demo-products 1000`, solo en local), buscar
    "r2 1/2", "conexion giratoria" y un SKU desde el teléfono: resultados en menos de 1
    segundo.
11. **Pantallas (FR-036, SC-008):** recorrer las pantallas en un teléfono de 360 px y en
    PC: sin desplazamiento horizontal, números `1.234,56`, metros con 2 decimales,
    fechas `dd/mm/aaaa`.

## Cierre de la etapa

- `docs/modelo-de-datos.md`, `docs/arquitectura.md` (búsqueda, fotos, matriz por
  endpoint), `docs/despliegue.md` (bucket, secreto y respaldo de fotos) y `CHANGELOG.md`
  actualizados (RNF-09).
- Bucket `product-photos` creado en Supabase y secreto `supabase-storage-key` en Secret
  Manager antes de desplegar.
- Restauración del respaldo probada en local, incluidas las fotos (plan de fases,
  definición de terminado).
