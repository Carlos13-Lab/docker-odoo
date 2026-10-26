from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PaymentApprovalLevel(models.Model):
    _name = "payment.approval.level"
    _description = "Nivel de aprobación de solicitudes de pago"
    _order = "company_id, min_amount desc"

    name = fields.Char(string="Nivel", required=True, help="Por ejemplo: Jefe de área, Gerencia.")
    min_amount = fields.Monetary(
        string="Monto mínimo",
        required=True,
        default=0.0,
        help="Las solicitudes desde este monto (en la moneda de la compañía) las aprueba este nivel.",
    )
    approver_id = fields.Many2one(
        "res.users",
        string="Aprobador",
        required=True,
        domain=lambda self: [("groups_id", "in", self.env.ref("payment_request.group_payment_request_approver").id)],
    )
    company_id = fields.Many2one(
        "res.company", string="Compañía", required=True, default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("min_amount_company_uniq", "unique(company_id, min_amount)",
         "Ya existe un nivel con ese monto mínimo en la compañía."),
    ]

    @api.constrains("min_amount")
    def _check_min_amount(self):
        for level in self:
            if level.min_amount < 0:
                raise ValidationError(_("El monto mínimo no puede ser negativo."))

    @api.constrains("approver_id")
    def _check_approver_group(self):
        group = self.env.ref("payment_request.group_payment_request_approver")
        for level in self:
            if group not in level.approver_id.groups_id:
                raise ValidationError(
                    _("%s no tiene el grupo Aprobador de solicitudes de pago.", level.approver_id.name)
                )

    @api.model
    def _find_for_amount(self, company, amount_company_currency):
        """Nivel con el mayor monto mínimo que no supere el monto de la solicitud."""
        return self.search(
            [("company_id", "=", company.id), ("min_amount", "<=", amount_company_currency)],
            order="min_amount desc",
            limit=1,
        )
