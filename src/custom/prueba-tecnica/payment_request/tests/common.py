from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import new_test_user


class PaymentRequestCommon(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        group = "payment_request.group_payment_request_"
        cls.requester = new_test_user(cls.env, login="pr_requester", name="Solicitante de prueba",
                                      groups=group + "requester")
        cls.other_requester = new_test_user(cls.env, login="pr_other_requester", name="Otro solicitante",
                                            groups=group + "requester")
        cls.approver = new_test_user(cls.env, login="pr_approver", name="Jefe de área",
                                     groups=group + "approver")
        cls.manager = new_test_user(cls.env, login="pr_manager", name="Gerencia",
                                    groups=group + "approver")
        cls.treasurer = new_test_user(cls.env, login="pr_treasurer", name="Tesorería de prueba",
                                      groups=group + "treasury")
        cls.vendor = cls.env["res.partner"].create({"name": "Proveedor de prueba"})
        Level = cls.env["payment.approval.level"]
        Level.search([]).unlink()
        cls.level_area = Level.create({"name": "Jefe de área", "min_amount": 0.0, "approver_id": cls.approver.id})
        cls.level_management = Level.create({"name": "Gerencia", "min_amount": 5000.0,
                                             "approver_id": cls.manager.id})
        cls.bank_journal = cls.company_data["default_journal_bank"]

    def _new_request(self, user=None, **vals):
        values = {"partner_id": self.vendor.id, "amount": 150.0, "concept": "Repuestos de octubre"}
        values.update(vals)
        return self.env["payment.request"].with_user(user or self.requester).create(values)

    def _submitted(self, **vals):
        request = self._new_request(**vals)
        request.action_submit()
        return request

    def _approved(self, **vals):
        request = self._submitted(**vals)
        request.with_user(request.approver_id).action_approve()
        return request

    def _reject(self, request, user, reason):
        wizard = self.env["payment.request.reject.wizard"].with_user(user).create(
            {"request_id": request.id, "reason": reason}
        )
        return wizard.action_confirm()

    def _pay(self, request, user=None):
        wizard = self.env["payment.request.pay.wizard"].with_user(user or self.treasurer).create(
            {"request_id": request.id, "journal_id": self.bank_journal.id}
        )
        return wizard.action_confirm()
