# API para tienda en línea (`shop_integration_api`)

Endpoints para que la tienda en línea de un cliente consulte productos con su stock desde Odoo.
Este documento es para el equipo que programa la tienda: debería bastar para integrarse sin llamarnos.

## Tramos completados

| Tramo | Estado |
|---|---|
| A — `GET /api/v1/products` con filtros, autenticación de usuario | ✅ 8/8 pruebas en verde |
| B — API keys, `POST /api/v1/orders`, log de llamadas | ⏳ Pendiente |
| C — Paginación, Idempotency-Key, stock sin N+1, webhook, openapi.yaml | ⏳ Pendiente |

## Autenticación (tramo A)

`auth="user"`: la llamada debe llevar la cookie de sesión de un usuario de Odoo (iniciar sesión en
`/web/session/authenticate` y reutilizar la cookie `session_id`). Sin sesión, Odoo redirige al inicio
de sesión. En el tramo B se reemplaza por API keys en la cabecera `Authorization: Bearer`.

El usuario debe tener al menos el grupo *Ventas / Usuario: solo mis documentos*.

## `GET /api/v1/products`

Devuelve los productos **activos** que **se pueden vender** (`sale_ok`), ordenados por código.

### Parámetros (todos opcionales, se pueden combinar)

| Parámetro | Ejemplo | Efecto |
|---|---|---|
| `category_id` | `7` | Productos de esa categoría **y de sus subcategorías**. |
| `in_stock` | `true` / `false` | `true`: solo con cantidad disponible mayor que cero. `false` o ausente: sin filtro. Acepta `true/false`, `1/0`, `yes/no`. |
| `updated_since` | `2026-10-24` o `2026-10-24T13:00:00-04:00` | Productos modificados desde esa fecha (ISO 8601). Sin zona horaria se interpreta como **UTC**. |

### Respuesta `200`

```json
{
  "data": [
    {"id": 42, "default_code": "ABC-123", "name": "Pastilla de freno", "price": 10.0, "qty_available": 5.0}
  ],
  "count": 1
}
```

| Campo | Significado |
|---|---|
| `id` | ID de la variante de producto en Odoo. |
| `default_code` | Código interno (referencia). `null` si no tiene. |
| `name` | Nombre del producto. |
| `price` | Precio de venta de la lista pública, en la moneda de la compañía, sin impuestos. |
| `qty_available` | Cantidad a mano en todos los almacenes de la compañía (no descuenta reservas). |

### Errores

Todos los errores usan el mismo formato:

```json
{"error": {"code": "INVALID_PARAMETER", "field": "updated_since", "message": "«updated_since» no es una fecha válida. Use el formato ISO 8601, por ejemplo 2026-10-24 o 2026-10-24T13:00:00Z."}}
```

| HTTP | `code` | Cuándo |
|---|---|---|
| 400 | `INVALID_PARAMETER` | `category_id` no es un número, `in_stock` no es un booleano o `updated_since` no es una fecha ISO 8601. `field` indica el parámetro. |
| 303 | — | Sin sesión: redirección al inicio de sesión (tramo A). |

### Ejemplos

```bash
# Repuestos (y subcategorías) con stock, modificados desde ayer
curl -b "session_id=..." "https://odoo.example.com/api/v1/products?category_id=7&in_stock=true&updated_since=2026-10-23"
```

## Cómo probarlo

```bash
./odoo test prueba-tecnica shop_integration_api
```

Las pruebas (`HttpCase`) llaman al endpoint con un usuario vendedor y cubren cada filtro solo y
combinado, las fechas mal escritas, parámetros inválidos y el acceso sin sesión.

## Supuestos

- **«Modificados desde»** cuenta los cambios en la variante y en la plantilla del producto: el precio
  y el nombre se guardan en la plantilla.
- **Cantidad disponible** = `qty_available` de Odoo (a mano, todos los almacenes de la compañía del
  usuario). Si la tienda vende desde un solo almacén, habría que filtrarlo (pregunta al cliente).
- **Precio** = precio de venta del producto, sin listas de precios ni impuestos.
- Se devuelve la variante (`product.product`), porque es lo que se vende y lo que tiene código.

## Limitaciones conocidas (tramo A)

- Sin paginación: devuelve todos los productos que cumplen los filtros (tramo C).
- `qty_available` se calcula por producto; en el tramo C se medirá y optimizará el número de consultas.
