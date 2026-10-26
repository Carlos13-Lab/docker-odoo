from odoo import fields, models


class PaymentRequestPayWizard(models.TransientModel):
    _name = "payment.request.pay.wizard"
    _description = "Registrar pago de una solicitud"

    request_id = fields.Many2one("payment.request", string="Solicitud", required=True, readonly=True)
    company_id = fields.Many2one(related="request_id.company_id")
    partner_id = fields.Many2one(related="request_id.partner_id", string="Proveedor")
    amount = fields.Monetary(related="request_id.amount", string="Monto")
    currency_id = fields.Many2one(related="request_id.currency_id")
    journal_id = fields.Many2one(
        "account.journal",
        string="Diario",
        required=True,
        domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', company_id)]",
        default=lambda self: self.env["account.journal"].search(
            [("type", "=", "bank"), ("company_id", "=", self.env.company.id)], limit=1
        ),
    )
    payment_date = fields.Date(string="Fecha de pago", required=True, default=fields.Date.context_today)

    def action_confirm(self):
        self.ensure_one()
        self.request_id._register_payment(self.journal_id, self.payment_date)
        return {"type": "ir.actions.act_window_close"}
