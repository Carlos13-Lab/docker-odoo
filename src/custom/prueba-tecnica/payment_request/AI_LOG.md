# AI_LOG — payment_request

## Herramientas
- Claude Code (claude.ai/code), con un Odoo 18 propio en su sesión para probar.

## Prompts clave (3 a 5)
1. «Haz el tramo A de payment_request y pruébalo antes de pasármelo».
   - Generó modelo, grupos, reglas de registro, vistas, menús y 12 pruebas. Las validaciones de grupo y estado están en los métodos, no solo en los botones.
2. «Escribe la sección de supuestos y preguntas al cliente».
   - Generó la lista de preguntas a Carolina con un supuesto para cada una. La revisé y la ajusté.

## Lo que la IA hizo mal
- La prueba del historial (chatter) fallaba: no tuvo en cuenta que Odoo escribe el seguimiento al cerrar la transacción, ni que mail.tracking.value solo lo lee el administrador.
- Cómo me di cuenta: la prueba fallaba con «mail.tracking.value() is not true»; se corrigió ejecutando el precommit en la prueba y leyendo con sudo().
- Sin que se lo pidiera, cubrió un caso que el enunciado no menciona: que el solicitante cambie el estado con write() directamente. Revisé que tuviera sentido antes de aceptarlo.

## Lo que escribí yo sin IA
- Probé el módulo en mi Docker (12/12 pruebas y 35/35 con los cuatro módulos).
- (completar: preguntas al cliente que agregaste o cambiaste, prueba manual con tres usuarios si la hiciste)
