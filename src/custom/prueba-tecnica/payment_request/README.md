# Solicitudes de pago (`payment_request`)

Solicitudes de pago a proveedores con flujo de aprobación, para reemplazar los pedidos por WhatsApp
de Distribuidora Andina C.A. (ficticia).

## Tramos completados

| Tramo | Estado |
|---|---|
| A — Modelo, flujo, grupos, vistas y pruebas | ✅ |
| B — Niveles de aprobación, wizards de rechazo y pago, PDF | ✅ 20/20 pruebas (A y B) en verde |
| C — USD/VES, multi-compañía, concurrencia, ARCHITECTURE.md | ⏳ Pendiente |

## Cómo funciona

1. **Cualquier empleado con el grupo *Solicitante*** crea una solicitud: proveedor, monto, moneda,
   fecha y concepto. El número sale de la secuencia `SP/2026/0001` y el solicitante es el usuario actual.
2. **Enviar** → la solicitud queda bloqueada (ya no se pueden cambiar sus datos ni borrarla), se le
   asigna el aprobador según el monto y se le crea una actividad a ese aprobador.
3. **Aprobador asignado**: *Aprobar*, o *Rechazar* con un motivo obligatorio que queda en el chatter y
   le llega al solicitante. Se guarda quién aprobó y cuándo.
4. **Tesorería**: *Registrar pago* elige el diario y crea el pago a proveedor (`account.payment`)
   publicado y vinculado a la solicitud (botón *Pago* en el formulario).
5. **Imprimir**: reporte PDF de la solicitud con quién aprobó, cuándo y el pago.

### Niveles de aprobación (tramo B)

*Solicitudes de pago › Configuración › Niveles de aprobación* (administradores). Cada nivel tiene un
monto mínimo y un aprobador. Al enviar, se asigna el nivel con el **mayor monto mínimo que no supere el
monto** de la solicitud, convertido a la moneda de la compañía. Ejemplo:

| Nivel | Desde | Aprobador |
|---|---|---|
| Jefe de área | 0 | Jefe de compras |
| Gerencia | 5.000 | Gerente de administración |

Una solicitud de 1.200 la aprueba el jefe de compras; una de 7.800, gerencia. Si no hay ningún nivel
configurado, no se puede enviar y el mensaje dice dónde configurarlo.

Estados: Borrador → Enviada → Aprobada → Pagada, o Rechazada. Cada cambio de estado queda en el chatter.

| Grupo | Ve | Puede |
|---|---|---|
| Solicitante | Solo sus solicitudes | Crear, editar y borrar mientras están en borrador; enviar |
| Aprobador (incluye Solicitante) | Todas | Además, aprobar y rechazar |
| Tesorería (incluye Solicitante) | Todas | Además, registrar el pago |

Menús: *Solicitudes de pago › Solicitudes* (todos), *Por aprobar* (aprobadores), *Por pagar* (tesorería).

## Seguridad: lo que un usuario no puede hacer

Las reglas no dependen solo de ocultar botones: se validan en el servidor.

- **Ver solicitudes ajenas:** regla de registro `requester_id = usuario` para el solicitante.
- **Aprobar, rechazar o pagar sin el grupo:** cada método verifica el grupo con `has_group()` y lanza
  `AccessError`, aunque se llame directamente por RPC.
- **Aprobar una solicitud asignada a otro aprobador:** solo el aprobador asignado puede aprobar o
  rechazar (`AccessError` para cualquier otro, aunque sea Aprobador).
- **Pagar dos veces:** el pago exige estado *Aprobada* y que no haya pago vinculado; además, una
  restricción `unique(payment_id)` en la base de datos.
- **Saltarse el flujo con `write({'state': ...})` o creando la solicitud ya aprobada:** `write()` y
  `create()` rechazan cambios de estado. Los métodos del flujo, después de validar grupo y estado,
  escriben el estado con `sudo()`: es el único uso de `sudo()` del módulo y está limitado a ese campo.
- **Editar o borrar una solicitud enviada:** `write()` bloquea los campos de negocio y `unlink()`
  solo permite borradores.
- **Monto cero o negativo:** restricción `@api.constrains`.

## Cómo probarlo

```bash
./odoo test prueba-tecnica payment_request
```

Las pruebas cubren el flujo completo y cada caso de la lista anterior, con usuarios de cada grupo
(`with_user`), no como administrador.

Prueba manual: crear tres usuarios (Solicitante, Aprobador, Tesorería), crear y enviar una solicitud
con el primero, aprobarla con el segundo y pagarla con el tercero.

## Supuestos y preguntas al cliente

Preguntas que le haría a Carolina, y lo que asumí para avanzar sin su respuesta:

| Pregunta | Supuesto para avanzar |
|---|---|
| ¿Quién es «el jefe del área» de cada empleado? ¿Usan departamentos en Odoo (módulo de Empleados)? | Tramo A: un grupo *Aprobador*. Tramo B: niveles configurables por monto con su aprobador; sin depender de RRHH. |
| ¿Desde qué monto un pago es «grande»? ¿Ese monto se mide en dólares o en bolívares? | Tramo B: niveles con monto mínimo configurable, comparado en la moneda de la compañía. |
| Los pagos grandes: ¿los aprueba solo gerencia, o primero el jefe y después gerencia (dos firmas)? | Una sola aprobación, la del nivel que corresponde al monto. |
| Si se rechaza, ¿el empleado puede corregir y reenviar la misma solicitud, o crea otra? | Rechazada es un estado final; se crea una solicitud nueva. |
| «Una vez enviada no la pueda cambiar»: ¿tampoco el aprobador? | Nadie cambia los datos después de enviar; si hay un error, se rechaza. |
| ¿Hay pagos parciales o en cuotas? | No: un pago por solicitud. |
| ¿Qué tasa se usa para pagar en bolívares una deuda en dólares: BCV del día del pago? ¿Quién la carga en Odoo? | Tramo C: la tasa registrada en Odoo para la fecha del pago. |
| ¿La solicitud se asocia a una factura del proveedor ya registrada, o puede ser un anticipo? | Solicitud independiente de la factura; el pago se registra como pago a proveedor. |
| ¿Quiénes son Tesorería? ¿Pueden también aprobar? | Grupos independientes: Tesorería no aprueba, salvo que se le den ambos grupos. |
| ¿Hace falta adjuntar soportes (factura, presupuesto)? | Se adjuntan desde el chatter; no es obligatorio. |
| ¿Trabajan con varias empresas en el mismo Odoo? | Tramo A: una compañía. Tramo C agrega reglas por compañía. |

## Limitaciones conocidas

- **Tesorería incluye el grupo de facturación de Contabilidad** (`account.group_account_invoice`):
  es el permiso mínimo de Odoo para crear pagos. Así Tesorería crea el pago con sus propios permisos,
  sin `sudo()`.
- Los usuarios necesitan un **correo electrónico** configurado: en Odoo, un usuario sin correo no
  puede publicar en el chatter (por ejemplo, el motivo del rechazo).
- El pago se registra en la **moneda de la solicitud**. Pagar en bolívares una solicitud en dólares es
  el tramo C.
- Un aprobador puede aprobar sus propias solicitudes si el nivel le corresponde. No se pidió
  separarlo; se puede agregar si Carolina lo confirma.
- Si el aprobador asignado no está disponible, hoy hay que cambiar el nivel y crear la solicitud de
  nuevo. Una reasignación queda como mejora.
