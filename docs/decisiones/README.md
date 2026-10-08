# Registro de decisiones técnicas (ADR)

Cada decisión técnica relevante se registra aquí (RNF-09). Una decisión aceptada no se
edita para cambiarla: se escribe un ADR nuevo que la reemplaza y se marca la anterior
como "Reemplazada por ADR-XXXX".

## Índice

| ADR | Título | Estado |
|---|---|---|
| [0001](0001-stack-tecnologico.md) | Stack tecnológico | Aceptada |
| [0002](0002-hosting-ambientes-y-presupuesto.md) | Hosting, ambientes y presupuesto | Aceptada |
| [0003](0003-ventas-sin-conexion-y-sincronizacion.md) | Ventas sin conexión, sincronización y numeración por equipo | Aceptada |
| [0004](0004-dinero-cantidades-y-redondeo.md) | Dinero, cantidades y redondeo | Aceptada |
| [0005](0005-autenticacion-y-permisos.md) | Autenticación y permisos | Aceptada |
| [0006](0006-idioma-de-identificadores.md) | Idioma de identificadores y convenciones | Aceptada |
| [0007](0007-guia-de-estilos-y-tecnologia-css.md) | Guía de estilos y tecnología CSS | Aceptada |
| [0008](0008-sesion-y-verificacion-por-peticion.md) | Sesión de jornada y verificación en cada petición | Aceptada |

## Plantilla

```markdown
# ADR-XXXX: Título

- **Estado:** Propuesta | Aceptada | Reemplazada por ADR-YYYY
- **Fecha:** AAAA-MM-DD
- **Requisitos relacionados:** RF-XX, RN-XX, RNF-XX, principios de la constitución

## Contexto

Qué problema se resuelve y qué restricciones aplican.

## Decisión

Qué se decidió, en concreto.

## Alternativas consideradas

Opciones descartadas y por qué.

## Consecuencias

Qué se gana, qué se pierde, riesgos y cómo se mitigan.
```
