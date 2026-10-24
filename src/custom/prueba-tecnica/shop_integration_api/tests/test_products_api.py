from datetime import datetime, timedelta

from odoo.tests import HttpCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestProductsApi(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(
            cls.env, login="shop_api_user", password="shop_api_user_pwd",
            groups="sales_team.group_sale_salesman",
        )
        cls.parts = cls.env["product.category"].create({"name": "Repuestos"})
        cls.brakes = cls.env["product.category"].create({"name": "Frenos", "parent_id": cls.parts.id})
        cls.other = cls.env["product.category"].create({"name": "Otros"})
        cls.stock_location = cls.env.ref("stock.stock_location_stock")

        def product(code, categ, qty=0.0, **vals):
            values = {"name": f"Producto {code}", "default_code": code, "categ_id": categ.id,
                      "list_price": 10.0, "is_storable": True}
            values.update(vals)
            record = cls.env["product.product"].create(values)
            if qty:
                cls.env["stock.quant"]._update_available_quantity(record, cls.stock_location, qty)
            return record

        cls.pad = product("API-PAD", cls.brakes, qty=5)
        cls.disc = product("API-DISC", cls.brakes)
        cls.filter = product("API-FILTER", cls.parts, qty=2)
        cls.cable = product("API-CABLE", cls.other, qty=8)
        cls.not_for_sale = product("API-NOSALE", cls.brakes, qty=3, sale_ok=False)
        cls.archived = product("API-OLD", cls.brakes, qty=3, active=False)

    def setUp(self):
        super().setUp()
        self.authenticate("shop_api_user", "shop_api_user_pwd")

    def _get(self, query=""):
        response = self.url_open(f"/api/v1/products{query}")
        return response, response.json()

    def _codes(self, body):
        return {item["default_code"] for item in body["data"] if (item["default_code"] or "").startswith("API-")}

    def test_lists_only_active_saleable_products(self):
        response, body = self._get()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._codes(body), {"API-PAD", "API-DISC", "API-FILTER", "API-CABLE"})
        pad = next(item for item in body["data"] if item["default_code"] == "API-PAD")
        self.assertEqual(set(pad), {"id", "default_code", "name", "price", "qty_available"})
        self.assertEqual(pad["id"], self.pad.id)
        self.assertEqual(pad["price"], 10.0)
        self.assertEqual(pad["qty_available"], 5.0)

    def test_filter_category_includes_subcategories(self):
        _response, body = self._get(f"?category_id={self.parts.id}")
        self.assertEqual(self._codes(body), {"API-PAD", "API-DISC", "API-FILTER"})
        _response, body = self._get(f"?category_id={self.brakes.id}")
        self.assertEqual(self._codes(body), {"API-PAD", "API-DISC"})

    def test_filter_in_stock(self):
        _response, body = self._get("?in_stock=true")
        self.assertEqual(self._codes(body), {"API-PAD", "API-FILTER", "API-CABLE"})
        _response, body = self._get("?in_stock=false")
        self.assertEqual(self._codes(body), {"API-PAD", "API-DISC", "API-FILTER", "API-CABLE"})

    def test_filter_updated_since(self):
        old = datetime(2020, 1, 1)
        self.env.cr.execute(
            "UPDATE product_product SET write_date = %s WHERE id IN %s",
            (old, tuple((self.pad | self.disc | self.filter | self.cable).ids)),
        )
        self.env.cr.execute(
            "UPDATE product_template SET write_date = %s WHERE id IN %s",
            (old, tuple((self.pad | self.disc | self.filter | self.cable).product_tmpl_id.ids)),
        )
        self.env.invalidate_all()
        self.filter.product_tmpl_id.list_price = 12.0  # cambio en la plantilla
        self.env.flush_all()
        since = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        _response, body = self._get(f"?updated_since={since}")
        self.assertEqual(self._codes(body), {"API-FILTER"})

    def test_filters_combined(self):
        _response, body = self._get(f"?category_id={self.brakes.id}&in_stock=1")
        self.assertEqual(self._codes(body), {"API-PAD"})
        since = (datetime.now() - timedelta(days=1)).isoformat()
        _response, body = self._get(f"?category_id={self.parts.id}&in_stock=true&updated_since={since}")
        self.assertEqual(self._codes(body), {"API-PAD", "API-FILTER"})

    def test_invalid_date_returns_400(self):
        response, body = self._get("?updated_since=24/10/2026")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(body["error"]["code"], "INVALID_PARAMETER")
        self.assertEqual(body["error"]["field"], "updated_since")
        self.assertIn("ISO 8601", body["error"]["message"])

    def test_invalid_category_and_flag_return_400(self):
        response, body = self._get("?category_id=abc")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(body["error"]["field"], "category_id")
        response, body = self._get("?in_stock=quizas")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(body["error"]["field"], "in_stock")

    def test_requires_login(self):
        self.logout()
        response = self.url_open("/api/v1/products", allow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertIn("/web/login", response.headers["Location"])
