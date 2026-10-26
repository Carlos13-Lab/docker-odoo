# Prueba técnica — Desarrollador Odoo

Esta carpeta es el directorio de addons de la prueba. Aquí van **todos los módulos que entregues**
(`shop_integration_api`, `fleet_inspection` ya migrado, `sale_commission` corregido y `payment_request`).

| Carpeta | Qué contiene |
|---|---|
| `src/custom/prueba-tecnica/sale_commission` | Módulo en producción del **Ejercicio 3** (ticket urgente). Revisa su historial con `git log -- src/custom/prueba-tecnica/sale_commission`. |
| `src/custom/prueba-tecnica-odoo16/fleet_inspection` | Módulo del **Ejercicio 2**, escrito para **Odoo 16**. Está fuera del directorio de addons a propósito: con su versión `16.0.x` impediría arrancar Odoo 17 o superior. El primer paso de la migración es moverlo a `src/custom/prueba-tecnica/`. |

## Levantar el entorno

1. Copia `instances.example.jsonc` a `instances.json` y agrega una instancia que use esta carpeta como addons
   (cambia la versión por la que elijas: 17.0, 18.0 o 19.0):

   ```jsonc
   "prueba-tecnica": {
     "odoo_version": "18.0",
     "external_port": 8069,
     "database": "pg16",
     "odoo_config": "18.0_default",
     "overwrite_odoo_config": {
       "addons": ["src/custom/prueba-tecnica"],
       "dev_mode": true
     }
   }
   ```

   La instancia necesita una entrada en `odoo_configs` para su versión y una en `databases`
   (puedes partir de las del ejemplo). No necesitas Odoo Enterprise.

2. Construye y levanta: `./odoo build` y `./odoo start`.
3. Corre las pruebas: `./odoo test prueba-tecnica sale_commission` (varios módulos separados por coma).

Más detalles del CLI en el `readme.md` de la raíz del repositorio.

---

# Entrega — Carlos Díaz

**Versión de Odoo: 18.0** (instancia `prueba-tecnica` en `instances.json`, Postgres 16).

Comando de pruebas de la entrega (base nueva):
`./odoo test prueba-tecnica shop_integration_api,fleet_inspection,sale_commission,payment_request`

| Ejercicio | Módulo | A | B | C | Documentación |
|---|---|---|---|---|---|
| 1. API para tienda en línea | `shop_integration_api` | ✅ | ⏳ | ⏳ | `shop_integration_api/README.md` |
| 2. Migración de inspecciones | `fleet_inspection` | ✅ | ⏳ | ⏳ | `fleet_inspection/README.md` (tabla de cambios) |
| 3. Ticket urgente T-200 | `sale_commission` | ✅ | ✅ | ✅ | `sale_commission/INCIDENT.md` |
| 4. Solicitudes de pago | `payment_request` | ✅ | ✅ | ⏳ | `payment_request/README.md` (supuestos y preguntas al cliente) |

Cada módulo tiene su `README.md` (tramos, cómo probarlo, supuestos y limitaciones) y su `AI_LOG.md`.

## Problemas conocidos del entorno

- `instances.example.json` apunta al perfil `postgresql.conf`, que no existe en `.resources/dbconfigs/`:
  Postgres no arranca. Usar `postgresql.small.conf`.
- `./odoo test` ejecuta Odoo como root dentro del contenedor y deja carpetas del filestore que el
  usuario `odoo` no puede escribir (`Permission denied: /home/odoo/data/filestore/...`). Después de
  correr las pruebas: `docker compose -f docker-compose.generated.yml exec -u root odoo-prueba-tecnica chown -R odoo:odoo /home/odoo/data`.
- Crear bases desde la terminal (`odoo -d <base> -i ... --stop-after-init`) es más fiable que desde el
  gestor web.
