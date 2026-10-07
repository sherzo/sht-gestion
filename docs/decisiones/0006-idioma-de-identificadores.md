# ADR-0006: Idioma de identificadores y convenciones

- **Estado:** Aceptada
- **Fecha:** 2026-10-05
- **Requisitos relacionados:** RNF-07; restricciones técnicas de la constitución

## Contexto

`CLAUDE.md` y la constitución piden todo en español (UI, documentación, commits y
comentarios) y permiten identificadores en inglés si el stack lo hace más natural, a
condición de decidirlo una vez y ser consistentes.

## Decisión

- **En inglés:** tablas, columnas, enums, clases, funciones, variables, rutas y campos
  de la API, nombres de archivos de código.
- **En español:** textos de la interfaz, mensajes de error mostrados al usuario,
  comentarios, docstrings, documentación, mensajes de commit y nombres de ramas.
- Las traducciones de los términos del negocio se fijan en el **glosario de
  `docs/arquitectura.md`** y no se improvisan. Un término nuevo se agrega primero al
  glosario.
- Los errores de la API devuelven un código estable en inglés y un mensaje en español,
  por ejemplo `{"code": "cash_session_closed", "message": "La caja está cerrada"}`.
- Las referencias a requisitos (`RF-XX`, `RN-XX`) se mantienen tal cual en comentarios,
  pruebas y commits.

## Alternativas consideradas

- **Identificadores en español:** más cercanos al negocio, pero chocan con las
  convenciones del ecosistema (FastAPI, SQLAlchemy, Next.js), mezclan idiomas en cada
  línea y complican tildes y eñes en nombres.

## Consecuencias

- El código se lee de forma natural junto a las librerías, y el glosario evita
  traducciones inconsistentes (por ejemplo, que "caja" aparezca como `cash_box` en un
  lugar y `register` en otro).
- Quien lea el código necesita el glosario para relacionarlo con el PRD.
