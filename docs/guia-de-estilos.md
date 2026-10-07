# Guía de estilos — SHT Gestión

| Campo | Valor |
|---|---|
| Versión | 1.0 |
| Fecha | 2026-10-07 |
| Estado | Vigente (base previa a la etapa 1.1a) |
| Documentos relacionados | `docs/decisiones/0007-guia-de-estilos-y-tecnologia-css.md`, `docs/arquitectura.md`, `docs/marca/` |

> Reglas visuales comunes a la app interna (`frontend/`) y al catálogo (`catalog/`).
> Los valores viven en un solo archivo, `packages/shared/styles/theme.css` (Tailwind
> CSS v4). Si esta guía y ese archivo no coinciden, se corrige uno de los dos en el mismo
> cambio. Esta versión cubre la base; los componentes de cada pantalla se definen en la
> etapa que los necesita (sección 9).

## 1. Marca

El logo original está en `docs/marca/logo.pdf` (Adobe Illustrator, "Logo Suministros
HT - Final", diciembre de 2023). Es 100 % vectorial y su texto está convertido a
contornos. Los SVG de `docs/marca/` se extrajeron de ese PDF sin redibujar nada.

| Archivo | Contenido | Usar sobre |
|---|---|---|
| `logo-vertical.svg` | Isotipo ámbar arriba, texto azul debajo | Blanco o fondos claros |
| `logo-horizontal.svg` | Isotipo ámbar a la izquierda, texto azul | Blanco o fondos claros (\*) |
| `logo-horizontal-negativo.svg` | Isotipo ámbar, texto blanco | Azul de marca |
| `logo-horizontal-azul.svg` | Todo en azul | Ámbar de marca |
| `isotipo.svg` | Solo el símbolo (T + H en escudo), ámbar | Azul de marca |
| `isotipo-azul.svg` | Solo el símbolo, azul | Ámbar de marca o blanco |
| `icono-app.svg` | Isotipo ámbar sobre cuadrado azul redondeado | Favicon e ícono de la app |

(\*) El PDF no trae la versión horizontal sobre blanco. Se derivó de la horizontal
cambiando el texto blanco por azul, como en la versión vertical sobre blanco del propio
PDF.

**Reglas de uso:**

- No deformar, rotar, recolorear fuera de estas versiones ni agregar sombras o
  contornos.
- Dejar alrededor un espacio libre de al menos la altura de la palabra "TURMERO".
- Tamaño mínimo: logo completo de 120 px de ancho; por debajo, usar solo el isotipo
  (legible hasta 16 px en `icono-app.svg`).
- Nunca poner el logo con texto azul sobre fondos oscuros ni el negativo sobre fondos
  claros.
- La tipografía del logotipo es **Gravita GEO Bold**, que es de pago. En la web el logo
  se usa siempre como SVG y nunca se escribe con esa fuente.
- Las apps sirven copias de los SVG que usan (`*/public/marca/` y `*/src/app/icon.svg`).
  La fuente de verdad es `docs/marca/`: si cambia el logo, se reemplazan las copias.

## 2. Color

La marca tiene solo dos colores, más el blanco. Los demás tonos se derivan de ellos.

| Color | Hex | Token | Papel |
|---|---|---|---|
| Azul de marca | `#03045E` | `navy-900` | Color principal: barra superior, botones primarios, títulos |
| Ámbar de marca | `#F7AA00` | `amber-500` | Acento: botón destacado, selección, resaltes |
| Blanco | `#FFFFFF` | `white` | Superficies (tarjetas, formularios) |

### 2.1 Contraste

Mínimo exigido (WCAG AA): 4,5:1 para texto y 3:1 para íconos y bordes que transmiten
información.

| Texto / fondo | Contraste | ¿Se puede? |
|---|---|---|
| Azul `navy-900` sobre blanco | 17,75 | Sí |
| Blanco sobre azul `navy-900` | 17,75 | Sí |
| Ámbar `amber-500` sobre azul `navy-900` | 9,05 | Sí |
| Azul `navy-900` sobre ámbar `amber-500` | 9,05 | Sí |
| **Ámbar `amber-500` sobre blanco** | **1,96** | **No.** El ámbar nunca va como texto ni ícono sobre fondos claros |
| Ámbar oscuro `amber-800` sobre blanco | 6,79 | Sí, si hace falta un texto "ámbar" sobre claro |

### 2.2 Escalas

Generadas en OKLCH a partir de los colores de marca, que quedan fijos en su paso. Los
valores exactos están en `theme.css`.

| Paso | 50 | 100 | 200 | 300 | 400 | 500 | 600 | 700 | 800 | 900 | 950 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `navy` | `#f1f5ff` | `#dee8fd` | `#c3d4f9` | `#9cb7f2` | `#698ee8` | `#3c64d6` | `#2044c2` | `#112ba2` | `#081981` | **`#03045e`** | `#01023e` |
| `amber` | `#fff9f1` | `#fff0d7` | `#ffe0af` | `#ffcb77` | `#ffb93d` | **`#f7aa00`** | `#d98b03` | `#b0660c` | `#8a4b0b` | `#6c380d` | `#401f0a` |
| `neutral` | `#f8fafc` | `#f1f5f9` | `#e2e8f0` | `#cbd5e1` | `#94a3b8` | `#64748b` | `#475569` | `#334155` | `#1e293b` | `#0f172a` | `#020617` |

Los grises (`neutral`) tienen un toque azulado para acompañar al azul de marca. Para
texto sobre blanco sirven desde `neutral-500` (4,76:1).

### 2.3 Tokens semánticos

Las pantallas usan estos nombres y no los pasos de la escala. Así un cambio de tono, o un
tema oscuro futuro, se hace en un solo lugar.

| Token (clase de Tailwind) | Valor | Uso |
|---|---|---|
| `primary` / `primary-hover` | `navy-900` / `navy-800` | Botón primario, barra superior, enlaces |
| `on-primary` | `white` | Texto sobre `primary` |
| `accent` / `accent-hover` | `amber-500` / `amber-400` | Acción destacada (p. ej. "Cobrar"), elemento seleccionado |
| `on-accent` | `navy-900` | Texto sobre `accent` |
| `canvas` | `neutral-50` | Fondo general de la página |
| `surface` | `white` | Tarjetas, tablas, formularios, diálogos |
| `line` | `neutral-200` | Bordes y separadores |
| `ink` | `neutral-900` | Texto normal |
| `ink-muted` | `neutral-600` | Texto secundario, ayudas, etiquetas |
| `focus` | `navy-500` | Anillo de foco del teclado |

Ejemplos: `bg-primary text-on-primary hover:bg-primary-hover`,
`bg-accent text-on-accent`, `border-line bg-surface`, `text-ink-muted`.

### 2.4 Estados

| Estado | Texto / ícono | Fondo suave | Contraste sobre blanco | Uso |
|---|---|---|---|---|
| `success` | `#15803d` | `success-soft` `#f0fdf4` | 5,02 | Operación guardada, caja cuadrada, "Disponible" |
| `warning` | `#c2410c` | `warning-soft` `#fff7ed` | 5,18 | Stock bajo, tasa que no es del día (RF-18), venta con diferencias al sincronizar |
| `danger` | `#b91c1c` | `danger-soft` `#fef2f2` | 6,47 | Errores, anulaciones, "Agotado", stock negativo |
| `info` | `#0369a1` | `info-soft` `#f0f9ff` | 5,93 | Avisos neutros, operaciones pendientes de sincronizar |

- El ámbar de marca **no** se usa para advertencias: el naranja de `warning` es otro
  color, para que una alerta no se confunda con un botón destacado.
- Un estado nunca depende solo del color: siempre va con texto y, cuando se pueda, con un
  ícono.
- En los mensajes, el texto en el color del estado va sobre su fondo suave (contraste
  ≥ 4,79:1).

## 3. Tipografía

| Fuente | Token | Uso |
|---|---|---|
| **Montserrat** | `font-display` | Títulos (`h1`–`h3`, ya aplicada por defecto) y textos de marca. Geométrica, cercana a la del logo |
| **Inter** | `font-sans` (por defecto) | Todo lo demás: textos, formularios, tablas, montos |

- Ambas son libres (Google Fonts) y se cargan con `next/font/google` en
  `src/app/fonts.ts` de cada app. Se descargan al construir y se sirven desde la propia
  app, así que funcionan sin conexión (RNF-01) y no hacen peticiones a Google.
- Montos, cantidades y tablas de números usan `tabular-nums` para que las cifras queden
  alineadas.
- Escala sugerida (clases de Tailwind): título de página `text-2xl font-bold`, título de
  sección `text-xl font-semibold`, texto `text-base`, ayudas y etiquetas `text-sm`. El
  texto normal no baja de 16 px en los formularios del teléfono.

## 4. Espaciado, bordes y sombras

Se usa la escala por defecto de Tailwind (múltiplos de 4 px).

- Separación interna de tarjetas: `p-4` en el teléfono, `p-6` desde tablet.
- Radios: `rounded-lg` para controles (botones, campos), `rounded-xl` para tarjetas y
  diálogos.
- Sombras: solo `shadow-sm` en tarjetas y `shadow-lg` en diálogos y menús flotantes.
- Bordes: `border border-line`.

## 5. Formato de datos (RNF-07)

- Números: `1.234,56`; fechas: `dd/mm/aaaa`; hora: `hh:mm`; zona horaria
  `America/Caracas`. Se formatean solo con los formateadores de `packages/shared`
  (`docs/arquitectura.md` §4.2–4.3).
- Precios en USD y Bs: el USD va primero y destacado; el Bs debajo o al lado, en
  `ink-muted`, con la fecha de la tasa si no es la del día (RF-18, en `warning`).

## 6. Accesibilidad y uso en el mostrador

- Contraste mínimo de la sección 2.1.
- Zonas táctiles de al menos 44 × 44 px (botones, filas seleccionables).
- Foco visible con el teclado: anillo `focus` (definido en `theme.css`, no se quita).
- Solo tema claro por ahora: se lee mejor en el mostrador con luz de día. Los tokens
  semánticos permiten agregar un tema oscuro más adelante sin tocar las pantallas.
- `lang="es-VE"` en el documento y textos alternativos en español en las imágenes.

## 7. Implementación

- `packages/shared/styles/theme.css`: bloque `@theme` de Tailwind con las escalas, los
  estados, los tokens semánticos y las fuentes, más los estilos base (fondo, texto,
  títulos y foco). Quita la paleta por defecto de Tailwind (`--color-*: initial`), así
  que solo existen los colores de esta guía; una clase como `bg-red-500` no genera nada.
- Cada app tiene `postcss.config.mjs` y `src/app/globals.css`, que importa
  `tailwindcss` y el tema compartido, y aplica las fuentes en `layout.tsx`.
- `themeColor` del viewport: `#03045E` (barra del navegador en el teléfono).
- Favicon: `src/app/icon.svg` (copia de `docs/marca/icono-app.svg`).

## 8. Cómo cambiar la guía

1. Ajustar el valor en `theme.css` y la tabla correspondiente de esta guía.
2. Comprobar el contraste de los pares afectados (≥ 4,5:1 para texto).
3. Registrar el cambio en `CHANGELOG.md`. Cambiar la tecnología o los principios
   (colores de marca, fuentes) requiere un ADR nuevo que reemplace a ADR-0007.

## 9. Pendiente por etapa

| Etapa | Se define |
|---|---|
| 1.1a | Botones, campos y mensajes de formulario; diseño del inicio de sesión y de la gestión de usuarios; íconos |
| 1.3 | Pantalla de venta: lista de productos, totales USD/Bs, teclado numérico, pagos |
| 1.5 | Íconos de la app instalable (PNG 192/512 y "maskable") a partir de `icono-app.svg`; indicador de sin conexión y pendientes |
| 1.6 | Diseño del catálogo público: tarjetas de producto, filtros, botón de WhatsApp |
