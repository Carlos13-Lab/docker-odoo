from datetime import datetime, timezone

from odoo import http
from odoo.http import request

TRUE_VALUES = {"1", "true", "yes"}
FALSE_VALUES = {"0", "false", "no"}


class ApiError(Exception):
    """Error de la API con el formato que documentamos para la tienda."""

    def __init__(self, status, code, message, field=None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.field = field
        self.message = message

    def response(self):
        error = {"code": self.code, "message": self.message}
        if self.field:
            error["field"] = self.field
        return request.make_json_response({"error": error}, status=self.status)


def _parse_int(params, name):
    value = params.get(name)
    if value in (None, ""):
        return None
    try:
        return int(value)
    except ValueError:
        raise ApiError(400, "INVALID_PARAMETER", f"«{name}» debe ser un número entero.", name) from None


def _parse_bool(params, name):
    value = (params.get(name) or "").strip().lower()
    if not value:
        return False
    if value in TRUE_VALUES:
        return True
    if value in FALSE_VALUES:
        return False
    raise ApiError(400, "INVALID_PARAMETER", f"«{name}» debe ser true o false.", name)


def _parse_datetime(params, name):
    """Acepta fecha (2026-10-24) o fecha y hora ISO 8601 (2026-10-24T13:00:00-04:00).

    Sin zona horaria se interpreta como UTC. Devuelve un datetime UTC sin zona, como lo guarda Odoo.
    """
    value = (params.get(name) or "").strip()
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise ApiError(
            400, "INVALID_PARAMETER",
            f"«{name}» no es una fecha válida. Use el formato ISO 8601, por ejemplo 2026-10-24 o 2026-10-24T13:00:00Z.",
            name,
        ) from None
    if parsed.tzinfo:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


class ShopApiController(http.Controller):
    @http.route("/api/v1/products", type="http", auth="user", methods=["GET"], csrf=False, readonly=True)
    def products(self, **params):
        try:
            domain = self._products_domain(params)
        except ApiError as error:
            return error.response()
        products = request.env["product.product"].search(domain, order="default_code, id")
        return request.make_json_response({
            "data": [self._product_payload(product) for product in products],
            "count": len(products),
        })

    def _products_domain(self, params):
        # Solo productos activos (search ya excluye los archivados) que se pueden vender.
        domain = [("sale_ok", "=", True)]
        category_id = _parse_int(params, "category_id")
        if category_id is not None:
            domain.append(("categ_id", "child_of", category_id))
        if _parse_bool(params, "in_stock"):
            domain.append(("qty_available", ">", 0))
        updated_since = _parse_datetime(params, "updated_since")
        if updated_since:
            # El precio y el nombre viven en la plantilla: un cambio ahí también cuenta como modificación.
            domain += ["|", ("write_date", ">=", updated_since), ("product_tmpl_id.write_date", ">=", updated_since)]
        return domain

    def _product_payload(self, product):
        return {
            "id": product.id,
            "default_code": product.default_code or None,
            "name": product.name,
            "price": product.lst_price,
            "qty_available": product.qty_available,
        }
