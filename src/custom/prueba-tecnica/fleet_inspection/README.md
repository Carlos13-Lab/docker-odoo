# Inspecciones de vehículos (`fleet_inspection`)

Registra inspecciones de los vehículos de Flota con un checklist de puntos (frenos, luces, cauchos…).
Escrito originalmente para Odoo 16 y **migrado a Odoo 18.0** (Ejercicio 2 de la prueba técnica).

## Qué hace

- El checklist se carga solo al crear la inspección, con los puntos configurados.
- Estados: borrador → en curso → aprobada / rechazada. Un punto crítico con falla impide aprobar.
- Tipo de vehículo: moto, carro, camión u otro.
- Grupos: *Inspector* (ve solo sus inspecciones) y *Supervisor de inspecciones* (ve todas, aprueba y rechaza).
- Acción planificada diaria: marca las inspecciones con más de 7 días en curso y le crea una actividad al inspector.
- Reporte PDF de la inspección.

## Tramos completados

| Tramo | Estado |
|---|---|
| A — Migración a 18.0 | ✅ Instala en una base nueva sin advertencias del módulo; 9/9 pruebas en verde. |
| B — Tipo de vehículo como catálogo | ⏳ Pendiente |
| C — Migración idempotente por lotes y MIGRATION_PLAN.md | ⏳ Pendiente |

## Cómo probarlo

```bash
./odoo test prueba-tecnica fleet_inspection
```

Para revisar advertencias al instalar, en una base nueva:

```bash
odoo -d prueba_fleet -i fleet_inspection --stop-after-init --log-level=warn
```

## Cambios de la migración 16.0 → 18.0

Cada fila es un commit `[MIG]` separado. La columna «Cómo se detectó» indica qué dijo Odoo 18 al
instalar el módulo sin cambios.

| Qué cambió | Por qué | Cómo se resolvió | Cómo se detectó |
|---|---|---|---|
| Carpeta `prueba-tecnica-odoo16/` → `prueba-tecnica/` | Con la versión `16.0.x` el módulo no puede estar en el `addons_path` de 18.0. | `git mv` al directorio de addons de la instancia. | — |
| Versión del manifiesto `16.0.1.0.0` → `18.0.1.0.0` | Odoo 18 solo acepta `x.y`, `x.y.z` o `18.0.x.y(.z)`. | Nueva versión `18.0.1.0.0`. | `ValueError: Invalid version '16.0.1.0.0'` (no carga el registro). |
| `ir.cron`: `numbercall` y `doall` | Esos campos se eliminaron de `ir.cron` en 18.0: una acción planificada activa corre indefinidamente. | Se quitaron del XML de datos. | `ValueError: Invalid field 'numbercall' on model 'ir.cron'`. |
| `@api.model def create(self, vals)` | Desde 17.0 se espera `create` por lotes; la forma de un solo registro está obsoleta. | `@api.model_create_multi def create(self, vals_list)`. La búsqueda de puntos del checklist se hace una vez para todo el lote. | `DeprecationWarning: ... is not overriding the create method in batch`. |
| `name_get()` | Se eliminó en 17.0; el nombre a mostrar sale del campo calculado `display_name`. | `_compute_display_name` con `@api.depends("name", "vehicle_id.license_plate", "vehicle_id.name")`. | La prueba `test_name_get_includes_plate` fallaba al llamar `name_get()`. |
| `states={...}` en campos Python (`vehicle_id`, `vehicle_type`) | El parámetro `states` de los campos ya no existe en 17.0+. | Se quitó del campo y el readonly pasó a la vista: `readonly="state != 'draft'"`. El comportamiento es el mismo: `states` en el campo también era solo de interfaz. | `WARNING ... unknown parameter 'states'`. |
| `attrs="{...}"` y `states="..."` en vistas | Eliminados en 17.0: la visibilidad y el solo lectura se escriben como expresiones Python. | `invisible="state != 'draft'"`, `readonly="state in ('approved', 'rejected')"`, `required="state == 'in_progress'"`, `invisible="not is_overdue"`. | En 17.0+ la vista no valida con `attrs`. |
| `<tree>` → `<list>` y `view_mode` `tree` → `list` | En 18.0 la vista de lista se llama `list`. | Renombrado en las vistas de inspección, del checklist y de los puntos, y en las acciones. | Revisión del código (la versión declarada es 18). |
| `<div class="oe_chatter">` con tres campos → `<chatter/>` | En 18.0 el chatter es una etiqueta propia. | `<chatter/>`. | Revisión del código. |
| `<group expand="0" string="...">` en la búsqueda | Los atributos ya no se usan en 18.0. | `<group>` simple. | Revisión del código. |
| Reporte: `t-esc` → `t-out` | `t-esc` está obsoleto desde 15.0; `t-out` escapa igual. | Reemplazo en la plantilla QWeb. | Revisión del código. |
| Pruebas: `name_get()`, `odoo.tests.common.Form`, `super(Clase, cls)` | `name_get` ya no existe; `Form` se importa desde `odoo.tests` en 18.0. | `display_name`, `from odoo.tests import Form, TransactionCase, tagged`, `super()`. | `DeprecationWarning: Since 18.0: odoo.tests.common.Form is deprecated` y el error de `name_get`. |

## Supuestos

- La versión de Odoo de la entrega es 18.0 (declarada en el README principal).
- Se mantiene el comportamiento de 16: mismos estados, grupos, reglas, cron y reporte. La migración no
  agrega funcionalidad.

## Limitaciones conocidas

- **Aprobar y rechazar no verifican el grupo en Python.** Los botones tienen `groups` de supervisor,
  pero `action_approve()` y `action_reject()` no comprueban el grupo: un inspector podría llamarlos
  por RPC sobre sus propias inspecciones. Ya pasaba en la versión 16; no se corrigió para no cambiar
  comportamiento en la migración. Propuesta: verificar `self.env.user.has_group(...)` en esos métodos,
  con prueba.
- Los mensajes `<string>:38: (ERROR/3) Unexpected indentation` que aparecen al arrancar vienen de la
  descripción de un módulo estándar de Odoo, no de este módulo.
