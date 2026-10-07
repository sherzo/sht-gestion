# ADR-0007: Guía de estilos y tecnología CSS

- **Estado:** Aceptada
- **Fecha:** 2026-10-07
- **Requisitos relacionados:** RNF-01, RNF-02, RNF-03, RNF-04, RNF-07; ADR-0001

## Contexto

La etapa 1.1a trae las primeras pantallas reales (inicio de sesión, usuarios). Hasta
ahora la app y el catálogo usaban estilos en línea sin criterio común. Hace falta una
base visual compartida y alineada con la marca antes de construirlas, para no repasar
cada pantalla después.

El negocio tiene un logo profesional (`docs/marca/logo.pdf`, vectorial) con dos colores:
azul `#03045E` y ámbar `#F7AA00`. Restricciones: costo cero (RNF-03), funcionamiento
sin conexión (RNF-01), equipos modestos (RNF-04) y sitios estáticos de Next.js
(ADR-0001).

## Decisión

- **Tailwind CSS v4** en `frontend/` y `catalog/`, con PostCSS
  (`@tailwindcss/postcss`).
- **Un único tema compartido** en `packages/shared/styles/theme.css` (bloque `@theme`),
  importado por las dos apps. Quita la paleta por defecto de Tailwind para que solo
  existan los colores de la guía.
- **Paleta:** azul de marca como color principal (`navy-900`), ámbar como acento
  (`amber-500`), grises azulados y cuatro colores de estado distintos del ámbar. Las
  pantallas usan tokens semánticos (`primary`, `accent`, `surface`, `ink`…).
- **Tipografía:** Montserrat para títulos e Inter para el resto, autoalojadas con
  `next/font/google`.
- **Solo tema claro** por ahora; los tokens semánticos permiten agregar el oscuro sin
  tocar pantallas.
- **Logo como SVG** extraído del PDF original; la fuente del logotipo (Gravita GEO, de
  pago) no se usa en la web.
- Las reglas de uso están en `docs/guia-de-estilos.md`.

## Alternativas consideradas

- **CSS propio (variables CSS + CSS Modules):** cero dependencias, pero más código por
  pantalla y sin restricción práctica de la paleta. Tailwind genera solo las clases
  usadas, así que el CSS final sigue siendo pequeño.
- **Biblioteca de componentes completa (MUI, Chakra, etc.):** más peso en el teléfono y
  un estilo propio que habría que pelear para seguir la marca. Si más adelante hacen
  falta componentes accesibles (diálogos, menús), se evaluarán piezas sueltas sobre
  Tailwind en la etapa que los necesite.
- **Montserrat en todo:** más identidad, pero es ancha y menos cómoda en tablas y
  montos.
- **Tema claro y oscuro desde el inicio:** duplica el trabajo de diseño de cada pantalla
  sin una necesidad del negocio.
- **Fuentes desde el CDN de Google:** no funcionan sin conexión y agregan una petición
  externa.

## Consecuencias

- Las pantallas se construyen con clases de Tailwind y tokens semánticos; un cambio de
  color se hace en un solo archivo.
- Un color fuera de la guía no compila a nada, lo que evita colores improvisados.
- El build descarga las fuentes de Google una vez; la CI y el despliegue necesitan
  internet (ya la tienen).
- Los SVG de la marca se copian a cada app; si cambia el logo hay que reemplazar las
  copias (`docs/guia-de-estilos.md` §1).
- Se agregan dependencias de desarrollo (`tailwindcss`, `@tailwindcss/postcss`,
  `postcss`), sin costo ni servicios externos.
