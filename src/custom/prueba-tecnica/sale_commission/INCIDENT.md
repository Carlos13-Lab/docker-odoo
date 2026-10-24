# INCIDENT T-200 — Los vendedores no pueden confirmar pedidos

| | |
|---|---|
| Cliente | Comercial Los Andes C.A. (ficticia) |
| Prioridad | Crítica |
| Síntoma | Desde el despliegue de las 12:00 m., ningún vendedor puede confirmar pedidos (error rojo). El gerente sí puede. |
| Módulo | `sale_commission` 1.1.0 → corregido en 1.1.1 |
| Rama / PR | `hotfix/T-200` |

## 1. Resumen

La versión 1.1.0 agregó comisiones por categoría de producto. El nuevo modelo de reglas
(`sale.commission.rule`) solo tenía permisos para el gerente de ventas, pero se consulta al
confirmar cualquier pedido: para un vendedor, Odoo bloquea la lectura y el pedido no se confirma.

Durante la revisión apareció un segundo error en el mismo cambio: cuando no hay regla de categoría,
el porcentaje se tomaba de **quien confirma** y no del **vendedor del pedido**. Como el gerente pasó
la tarde confirmando pedidos ajenos, esas líneas pueden haber quedado con el porcentaje del gerente.

## 2. Cómo se reproduce

1. Usuario con el grupo *Ventas / Usuario: solo mis documentos* (sin grupo de gerente).
2. Crear una cotización con cualquier producto y pulsar *Confirmar*.
3. Resultado:

```
File ".../sale_commission/models/sale_order_line.py", line 28, in _get_commission_percent
    rules = self.env["sale.commission.rule"].search([
odoo.exceptions.AccessError: You are not allowed to access 'Comisión por categoría de producto'
(sale.commission.rule) records.
This operation is allowed for the following groups:
    - Sales/Administrator
```

Con un usuario gerente el mismo flujo funciona, porque el gerente sí tiene permiso sobre el modelo.

## 3. Causa raíz

Commit `3f4d73f` — *[FEAT] sale_commission: porcentaje de comisión por categoría de producto*:

1. **Permisos:** `security/ir.model.access.csv` solo da acceso a `sale.commission.rule` al grupo
   `sales_team.group_sale_manager`. `SaleOrder.action_confirm()` llama a
   `SaleOrderLine._get_commission_percent()`, que hace `search()` sobre ese modelo con el usuario
   actual → `AccessError` para cualquier vendedor.
2. **Porcentaje equivocado:** sin regla aplicable, `_get_commission_percent()` devolvía
   `self.env.user.commission_percent` (quien confirma) en vez de
   `self.order_id.user_id.commission_percent` (vendedor del pedido). Antes de la 1.1.0 el cálculo sí
   usaba el vendedor del pedido.

## 4. Corrección (cambio mínimo)

| Commit | Cambio |
|---|---|
| `e9889f2` [FIX] | Una línea en `ir.model.access.csv`: **solo lectura** de `sale.commission.rule` para `sales_team.group_sale_salesman`. Versión 1.1.1. |
| `68337ee` [FIX] | `_get_commission_percent()` devuelve `self.order_id.user_id.commission_percent`. |

Decisiones:

- **Lectura y nada más:** el vendedor necesita leer la regla para calcular su comisión, no
  modificarla. Crear, editar y borrar reglas sigue siendo solo del gerente.
- **Sin `sudo()`:** no hace falta saltarse los permisos; basta con darlos bien.
- **Sin dar el grupo de gerente a los vendedores:** les abriría todo lo del gerente (pedidos ajenos,
  configuración, reportes de todos).
- **No se reescribe nada más.** Las inconsistencias de la sección 11 quedan como seguimiento.

## 5. Pruebas (rojo antes, verde después)

Se ejecutan con `./odoo test prueba-tecnica sale_commission`.

| Commit | Prueba | Resultado |
|---|---|---|
| `281f963` [TEST] | `test_salesman_can_confirm_own_order`: el pedido se crea y confirma **con `with_user(vendedor)`** | 🔴 1 error de 5 (`AccessError`) |
| `e9889f2` [FIX] | — | 🟢 5/5 |
| `9d49df7` [TEST] | `test_manager_confirms_for_salesman`: el gerente (12 %) confirma el pedido del vendedor (5 %). Además se quita `cls.env.user.commission_percent = 5.0` del setup | 🔴 2 fallos de 6: `12.0 != 5.0` y `0.0 != 5.0` |
| `68337ee` [FIX] | — | 🟢 6/6 |

## 6. Contención (primeros 15 minutos, antes de la corrección)

**Opción recomendada — dar el permiso de lectura a mano** (Ajustes › Técnico › Seguridad ›
Accesos › Nuevo): modelo *Comisión por categoría de producto*, grupo *Ventas / Usuario: solo mis
documentos*, solo *Leer*.

- Restablece la venta en minutos, sin desplegar código ni reiniciar.
- Reversible: se borra ese registro y todo vuelve a como estaba.
- Riesgos: (1) **no corrige** el porcentaje equivocado: mientras el gerente siga confirmando por
  otros, las comisiones siguen saliendo mal, así que hay que pedir que cada vendedor confirme lo suyo;
  (2) hay que borrar ese acceso manual después del despliegue para no dejar un registro duplicado
  fuera del código.

**Alternativa:** volver el módulo al commit anterior (`ad51040`) y actualizar con `-u`. Más lenta
(requiere despliegue), se pierde la comisión por categoría mientras tanto y cambia el esquema de datos.

**Lo que no se debe hacer:** dar el grupo de gerente a los vendedores, ni que el gerente siga
confirmando pedidos de otros (genera más datos con la comisión equivocada).

## 7. Commit que introdujo el error y por qué pasó la revisión

`git log --oneline -- src/custom/prueba-tecnica/sale_commission` muestra solo tres commits del
módulo antes del hotfix: `ad51040` (versión inicial), `3f4d73f` (comisión por categoría) y
`87ac54d` (README). El único que toca el flujo de confirmación es `3f4d73f`, y su diff contiene los
dos errores.

Pasó la revisión porque **el mismo commit cambió las pruebas** de forma que ya no podían detectarlo:

1. `_create_order()` dejó de usar `with_user(user)`: los pedidos pasaron a crearse y confirmarse
   como administrador, que tiene todos los permisos.
2. Se agregó `cls.env.user.commission_percent = 5.0`: el administrador tenía el mismo porcentaje que
   el vendedor de prueba, así que tomar el porcentaje de quien confirma daba el mismo número.

Las pruebas pasaban en verde sin ejercitar al usuario real que usa el flujo.

## 8. Despliegue y verificación en producción

1. **Respaldo:** `pg_dump` de la base y copia del filestore.
2. **Código:** traer la rama corregida (merge de `hotfix/T-200`) en el servidor.
3. **Actualizar solo el módulo afectado:**
   `odoo -d <base> -u sale_commission --stop-after-init` y reiniciar el servicio.
4. **Verificar:**
   - Ajustes › Aplicaciones: `sale_commission` en versión 1.1.1.
   - Ajustes › Técnico › Accesos: existe *sale.commission.rule.salesman* (solo lectura).
   - Con un **usuario vendedor real**: confirmar una cotización de prueba y revisar la comisión de la línea.
   - Con el gerente: confirmar un pedido propio; todo sigue igual.
5. **Retirar la contención:** borrar el acceso creado a mano en el paso 6.
6. **Datos:** ejecutar el script de la sección 10 y seguir el plan de corrección.

## 9. Mensaje al cliente

> Ya encontramos la causa del problema: la actualización de hoy al mediodía dejó a los vendedores sin
> un permiso que necesitan para confirmar pedidos. Lo corregimos y lo probamos con un usuario vendedor;
> mañana podrán vender con normalidad desde la apertura. También estamos revisando los pedidos que el
> gerente confirmó esta tarde, porque algunas comisiones pueden haber quedado con un porcentaje
> equivocado; les enviaremos el detalle y la corrección antes del cierre de mes.

## 10. Impacto en los datos

**Qué quedó mal:** líneas de pedidos confirmados por el gerente en nombre de un vendedor, cuyo
producto no tiene regla de categoría: guardaron el porcentaje del gerente. El pedido sigue siendo
del vendedor (`user_id` no cambió), así que el reporte mensual se lo atribuye a él, pero con un monto
equivocado.

**Qué no quedó mal:** líneas con regla de categoría (el porcentaje sale de la regla) y pedidos que
cada vendedor confirmó solo (antes del despliegue, o después de la corrección).

**Script de solo lectura:** `scripts/t200_affected_lines.sql`. Lista pedido, vendedor, producto,
porcentaje actual vs. correcto y comisión actual vs. correcta. Corre en una transacción
`READ ONLY` y termina en `ROLLBACK`, así que la base rechaza cualquier escritura.

```bash
docker compose -f docker-compose.generated.yml exec -T odoo-prueba-tecnica \
  psql -d <base> -v since="'2026-10-23 12:00:00'" \
  < src/custom/prueba-tecnica/sale_commission/scripts/t200_affected_lines.sql
```

`since` es la hora del despliegue en UTC. Al confirmar, Odoo guarda la fecha de confirmación en
`date_order`, por eso el filtro usa ese campo.

Limitaciones: compara con el porcentaje **actual** del vendedor (si alguien lo cambió después del
despliegue, revisar esos casos a mano) y no distingue si el pedido lo confirmó el gerente o el propio
vendedor: lista toda línea cuyo porcentaje no coincide, que es lo que hay que corregir.

**Plan de corrección (después del despliegue):**

1. Ejecutar el script con la hora del despliegue y guardar el resultado (CSV) como evidencia.
2. Enviarlo a administración del cliente para que lo valide antes de tocar nada.
3. Con la validación, recalcular solo esas líneas. El botón **Recalcular comisiones** no sirve tal
   cual (ver sección 11): usar un script de escritura revisado que aplique
   `_get_commission_percent()` a las líneas del listado, probado antes en una copia de la base.
4. Volver a ejecutar el script de solo lectura: debe devolver 0 filas.
5. Si ya se pagaron comisiones con esos montos, informar la diferencia a administración.

## 11. El mismo patrón en otras partes del módulo

- **`SaleOrder.action_recompute_commissions()`** también hace `search()` sobre
  `sale.commission.rule`: antes de la corrección, un vendedor que pulsara el botón obtenía el mismo
  `AccessError`. Con el permiso de lectura queda resuelto.
- **Además, calcula distinto que la confirmación:** busca la regla solo por la categoría exacta
  (sin `parent_of`, así que ignora las reglas de categorías padre) e ignora la compañía. Recalcular un
  pedido puede dar otro porcentaje que confirmarlo. **No se corrige en el hotfix** (no impide vender):
  queda como seguimiento — que el botón reutilice `_get_commission_percent()`, con prueba.
- **Reporte mensual (`sale.commission.report`):** tiene permisos y reglas de registro para el vendedor
  (solo ve lo suyo) y no usa `env.user` para calcular. Sin hallazgos.

## 12. Prevención

1. **Regla de pruebas:** toda prueba de un flujo de negocio se ejecuta con `with_user()` y el grupo
   **mínimo** que usa ese flujo en la vida real. Nunca solo como administrador.
2. **Checklist de revisión para cambios que agregan modelos o campos:**
   - ¿El modelo nuevo tiene acceso para **todos** los grupos que pasan por el flujo, no solo para quien lo configura?
   - ¿Hay `self.env.user` en un cálculo de negocio? ¿Es realmente "quien hace clic" o es el dueño del registro?
   - ¿El commit modifica pruebas existentes para que pasen (quitar `with_user`, fijar valores al admin)? Si es así, el revisor pide la justificación.
3. **Prueba de humo de permisos en CI:** para cada módulo, una prueba que ejecute el flujo principal
   (crear y confirmar) con el usuario de menor nivel.
