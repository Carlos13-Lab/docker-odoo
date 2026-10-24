# AI_LOG — fleet_inspection

## Herramientas
- Claude Code (claude.ai/code), con un Odoo 18 + Postgres 16 propio en su sesión para probar.

## Prompts clave (3 a 5)
1. «Migra fleet_inspection a Odoo 18 y verifícalo antes de pasármelo».
   - Instaló el módulo sin cambios en Odoo 18 y fue corrigiendo error por error (versión del manifiesto, numbercall del cron, create, name_get, states, attrs, tree, chatter). Un commit por tipo de cambio.
2. «Escribe la tabla de cambios del README: qué cambió, por qué, cómo se resolvió».
   - La tabla incluye el mensaje real de Odoo 18 que detectó cada cambio. La revisé fila por fila.

## Lo que la IA hizo mal
- Los README con tablas en Markdown hacían que Odoo mostrara avisos de docutils al instalar: Odoo usa el README como descripción del módulo y lo procesa como RST.
- Cómo me di cuenta: al instalar los cuatro módulos juntos aparecieron los avisos «Undefined substitution referenced». Se corrigió con una description corta en el manifiesto.

## Lo que escribí yo sin IA
- Probé la migración en mi entorno Docker (9/9 pruebas y luego 35/35 con los cuatro módulos).
- Revisé el diff de cada commit y abrí y mergeé el PR.
- (completar con lo que hayas revisado o cambiado tú)
