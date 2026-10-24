# Comisiones de vendedores (`sale_commission`)

Calcula la comisión del vendedor en cada línea de pedido de venta y ofrece un análisis mensual por vendedor.

## Configuración

- **Porcentaje del vendedor:** Ajustes › Usuarios › pestaña *Comisiones* (solo gerentes de ventas).
- **Porcentaje por categoría (desde la 1.1):** Inventario/Ventas › Configuración › Categorías de producto,
  campo *Comisión (%)*. Si la categoría (o una categoría padre) tiene porcentaje, reemplaza al del vendedor.

## Cómo funciona

- Al confirmar el pedido se fija el porcentaje en cada línea y se calcula la comisión sobre el subtotal sin impuestos.
- El botón *Recalcular comisiones* del pedido vuelve a aplicar los porcentajes vigentes.
- Ventas › Reportes › *Comisiones*: tabla dinámica y gráfico por vendedor y mes. Cada vendedor ve solo lo suyo.

## Pruebas

```bash
./odoo test prueba-tecnica sale_commission
```

## Entrega — Ticket T-200

| Tramo | Estado |
|---|---|
| A — Reproducir, causa raíz, corrección y prueba | ✅ |
| B — Contención, commit culpable, despliegue y mensaje al cliente | ✅ |
| C — Impacto en los datos, script de solo lectura y prevención | ✅ |

Todo el detalle está en `INCIDENT.md`. El script de solo lectura está en `scripts/t200_affected_lines.sql`.

### Qué se corrigió (versión 1.1.1)
- Los vendedores pueden leer (solo leer) las reglas de comisión por categoría: sin eso no podían confirmar pedidos.
- La comisión se toma del vendedor del pedido y no de quien lo confirma.

### Supuestos
- Hacer el cambio mínimo: no se reescribe el módulo porque está en producción.
- El segundo error (la comisión de quien confirma) entra en el hotfix, en un commit aparte, porque la contención de la tarde (el gerente confirmando por todos) genera datos incorrectos mientras no se corrija.

### Limitaciones conocidas
- El botón «Recalcular comisiones» calcula distinto que la confirmación: no considera las categorías padre ni la compañía. Queda como seguimiento (sección 11 de `INCIDENT.md`).
- El script de solo lectura compara con el porcentaje actual del vendedor: si se cambió después del despliegue, esos casos hay que revisarlos a mano.
