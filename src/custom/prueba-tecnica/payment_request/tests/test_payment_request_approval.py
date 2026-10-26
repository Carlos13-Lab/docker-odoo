from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .common import PaymentRequestCommon


@tagged("post_install", "-at_install")
class TestPaymentRequestApproval(PaymentRequestCommon):
    """Tramo B: niveles de aprobación, rechazo con motivo, pago contable y PDF."""

    def test_level_assigned_by_amount(self):
        small = self._submitted(amount=1000.0)
        self.assertEqual(small.approval_level_id, self.level_area)
        self.assertEqual(small.approver_id, self.approver)
        big = self._submitted(amount=5000.0)
        self.assertEqual(big.approval_level_id, self.level_management)
        self.assertEqual(big.approver_id, self.manager)

    def test_submit_creates_activity_for_approver(self):
        request = self._submitted(amount=7000.0)
        activity = request.sudo().activity_ids
        self.assertEqual(len(activity), 1)
        self.assertEqual(activity.user_id, self.manager)

    def test_submit_without_level_is_blocked(self):
        self.env["payment.approval.level"].search([]).unlink()
        request = self._new_request()
        with self.assertRaises(UserError):
            request.action_submit()
        self.assertEqual(request.state, "draft")

    def test_only_assigned_approver_can_approve(self):
        request = self._submitted(amount=7000.0)  # le toca a Gerencia
        with self.assertRaises(AccessError):
            request.with_user(self.approver).action_approve()
        with self.assertRaises(AccessError):
            self._reject(request, self.approver, "No corresponde")
        self.assertEqual(request.state, "submitted")
        request.with_user(self.manager).action_approve()
        self.assertEqual(request.state, "approved")
        self.assertEqual(request.approved_by_id, self.manager)
        self.assertTrue(request.approved_date)
        self.assertFalse(request.sudo().activity_ids, "La actividad del aprobador se cierra al aprobar")

    def test_reject_requires_reason_and_posts_it(self):
        request = self._submitted()
        with self.assertRaises(UserError):
            self._reject(request, self.approver, "   ")
        self._reject(request, self.approver, "Falta la factura del proveedor")
        self.assertEqual(request.state, "rejected")
        self.assertEqual(request.rejection_reason, "Falta la factura del proveedor")
        bodies = request.with_user(self.requester).message_ids.mapped("body")
        self.assertTrue(any("Falta la factura del proveedor" in body for body in bodies),
                        "El solicitante ve el motivo en el historial")

    def test_payment_creates_linked_vendor_payment(self):
        request = self._approved(amount=320.0)
        self._pay(request)
        payment = request.payment_id
        self.assertEqual(request.state, "paid")
        self.assertTrue(payment)
        self.assertEqual(payment.payment_type, "outbound")
        self.assertEqual(payment.partner_type, "supplier")
        self.assertEqual(payment.partner_id, self.vendor)
        self.assertEqual(payment.amount, 320.0)
        self.assertEqual(payment.journal_id, self.bank_journal)
        self.assertNotEqual(payment.state, "draft")
        self.assertIn(request.name, payment.memo)
        self.assertEqual(request.payment_count, 1)

    def test_cannot_pay_twice(self):
        request = self._approved()
        self._pay(request)
        with self.assertRaises(UserError):
            self._pay(request)
        with self.assertRaises(UserError):
            request.with_user(self.treasurer)._register_payment(self.bank_journal, request.date)
        self.assertEqual(self.env["account.payment"].search_count([("memo", "ilike", request.name)]), 1)

    def test_pdf_shows_who_approved_and_when(self):
        request = self._approved()
        html = self.env["ir.actions.report"].with_user(self.requester)._render_qweb_html(
            "payment_request.action_report_payment_request", request.ids
        )[0].decode()
        self.assertIn(request.name, html)
        self.assertIn("Jefe de área", html)
        self.assertIn("Fecha de aprobación", html)
