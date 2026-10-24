-- T-200: líneas de pedidos confirmados desde el despliegue cuyo porcentaje de
-- comisión no coincide con el del vendedor del pedido.
-- SOLO LECTURA: corre dentro de una transacción READ ONLY y termina en ROLLBACK.
--
-- Solo se revisan líneas SIN regla de categoría aplicable: cuando hay regla, el
-- porcentaje sale de la regla y el error no aplica.
--
-- Uso:
--   docker compose -f docker-compose.generated.yml exec -T odoo-prueba-tecnica \
--     psql -d <base> -v since="'2026-10-23 12:00:00'" \
--     < src/custom/prueba-tecnica/sale_commission/scripts/t200_affected_lines.sql
-- (since = hora del despliegue en UTC)

BEGIN READ ONLY;

SELECT so.name                                              AS pedido,
       so.date_order                                        AS confirmado_utc,
       vend.login                                           AS vendedor,
       pp.default_code                                      AS producto,
       sol.price_subtotal                                   AS subtotal,
       sol.commission_percent                               AS porcentaje_actual,
       vend.commission_percent                              AS porcentaje_correcto,
       sol.commission_amount                                AS comision_actual,
       round((sol.price_subtotal * vend.commission_percent / 100.0)::numeric, 2)
                                                            AS comision_correcta
  FROM sale_order_line sol
  JOIN sale_order so        ON so.id = sol.order_id
  JOIN res_users vend       ON vend.id = so.user_id
  JOIN product_product pp   ON pp.id = sol.product_id
  JOIN product_template pt  ON pt.id = pp.product_tmpl_id
  JOIN product_category pc  ON pc.id = pt.categ_id
 WHERE so.state = 'sale'
   AND sol.display_type IS NULL
   AND so.date_order >= :since
   AND NOT EXISTS (
         SELECT 1
           FROM sale_commission_rule r
           JOIN product_category rc ON rc.id = r.categ_id
          WHERE pc.parent_path LIKE rc.parent_path || '%'
            AND (r.company_id IS NULL OR r.company_id = sol.company_id)
       )
   AND sol.commission_percent IS DISTINCT FROM vend.commission_percent
 ORDER BY so.date_order, so.name;

ROLLBACK;
