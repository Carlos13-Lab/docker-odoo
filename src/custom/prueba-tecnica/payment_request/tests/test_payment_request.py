from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestPaymentRequest(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.requester = new_test_user(
            cls.env, login="pr_requester", name="Solicitante de prueba",
            groups="payment_request.group_payment_request_requester",
        )
        cls.other_requester = new_test_user(
            cls.env, login="pr_other_requester", name="Otro solicitante",
            groups="payment_request.group_payment_request_requester",
        )
        cls.approver = new_test_user(
            cls.env, login="pr_approver", name="Aprobador de prueba",
            groups="payment_request.group_payment_request_approver",
        )
        cls.treasurer = new_test_user(
            cls.env, login="pr_treasurer", name="Tesorería de prueba",
            groups="payment_request.group_payment_request_treasury",
        )
        cls.vendor = cls.env["res.partner"].create({"name": "Proveedor de prueba"})

    def _new_request(self, user=None, **vals):
        values = {"partner_id": self.vendor.id, "amount": 150.0, "concept": "Repuestos de octubre"}
        values.update(vals)
        return self.env["payment.request"].with_user(user or self.requester).create(values)

    # Flujo

    def test_create_defaults_and_sequence(self):
        request = self._new_request()
        self.assertTrue(request.name.startswith("SP/"))
        self.assertEqual(request.requester_id, self.requester)
        self.assertEqual(request.state, "draft")
        self.assertEqual(request.currency_id, self.env.company.currency_id)

    def test_full_flow_paid(self):
        request = self._new_request()
        request.action_submit()
        self.assertEqual(request.state, "submitted")
        request.with_user(self.approver).action_approve()
        self.assertEqual(request.state, "approved")
        request.with_user(self.treasurer).action_pay()
        self.assertEqual(request.state, "paid")

    def test_reject(self):
        request = self._new_request()
        request.action_submit()
        request.with_user(self.approver).action_reject()
        self.assertEqual(request.state, "rejected")

    def test_state_changes_are_tracked(self):
        # El seguimiento se escribe al final de cada transacción (precommit). En la vida real la
        # creación y el envío son dos transacciones; aquí se simula ejecutando el precommit dos veces.
        request = self._new_request()
        self.env.flush_all()
        self.env.cr.precommit.run()
        request.action_submit()
        self.env.flush_all()
        self.env.cr.precommit.run()
        # mail.tracking.value solo lo lee el administrador: se consulta con sudo().
        tracked = request.sudo().message_ids.tracking_value_ids.filtered(lambda t: t.field_id.name == "state")
        self.assertTrue(tracked)

    # Lo que no se debe poder hacer

    def test_requester_sees_only_own(self):
        own = self._new_request()
        other = self._new_request(user=self.other_requester)
        visible = self.env["payment.request"].with_user(self.requester).search([])
        self.assertIn(own, visible)
        self.assertNotIn(other, visible)
        self.assertIn(other, self.env["payment.request"].with_user(self.approver).search([]))

    def test_requester_cannot_approve_calling_the_method(self):
        request = self._new_request()
        request.action_submit()
        with self.assertRaises(AccessError):
            request.action_approve()
        with self.assertRaises(AccessError):
            request.action_reject()
        self.assertEqual(request.state, "submitted")

    def test_requester_cannot_force_state_with_write(self):
        request = self._new_request()
        with self.assertRaises(UserError):
            request.write({"state": "approved"})
        with self.assertRaises(UserError):
            self._new_request(state="approved")

    def test_only_treasury_pays(self):
        request = self._new_request()
        request.action_submit()
        request.with_user(self.approver).action_approve()
        with self.assertRaises(AccessError):
            request.with_user(self.approver).action_pay()
        with self.assertRaises(AccessError):
            request.action_pay()

    def test_submitted_request_is_locked(self):
        request = self._new_request()
        request.action_submit()
        with self.assertRaises(UserError):
            request.write({"amount": 999.0})
        with self.assertRaises(UserError):
            request.with_user(self.approver).write({"partner_id": self.env.company.partner_id.id})
        with self.assertRaises(UserError):
            request.unlink()

    def test_draft_can_be_edited_and_deleted(self):
        request = self._new_request()
        request.write({"amount": 200.0})
        self.assertEqual(request.amount, 200.0)
        request.unlink()
        self.assertFalse(request.exists())

    def test_amount_must_be_positive(self):
        with self.assertRaises(ValidationError):
            self._new_request(amount=0.0)
        with self.assertRaises(ValidationError):
            self._new_request(amount=-10.0)

    def test_actions_respect_state(self):
        request = self._new_request()
        with self.assertRaises(UserError):
            request.with_user(self.approver).action_approve()
        request.action_submit()
        with self.assertRaises(UserError):
            request.action_submit()
        with self.assertRaises(UserError):
            request.with_user(self.treasurer).action_pay()
