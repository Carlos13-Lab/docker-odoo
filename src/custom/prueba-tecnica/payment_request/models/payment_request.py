from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

# Campos que el solicitante define y que no pueden cambiar una vez enviada la solicitud.
LOCKED_FIELDS = {"partner_id", "requester_id", "amount", "currency_id", "date", "concept", "company_id"}


class PaymentRequest(models.Model):
    _name = "payment.request"
    _description = "Solicitud de pago"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(string="Número", required=True, copy=False, readonly=True, default="/")
    partner_id = fields.Many2one("res.partner", string="Proveedor", required=True, tracking=True)
    requester_id = fields.Many2one(
        "res.users",
        string="Solicitante",
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company", string="Compañía", required=True, default=lambda self: self.env.company
    )
    amount = fields.Monetary(string="Monto", required=True, tracking=True)
    currency_id = fields.Many2one(
        "res.currency",
        string="Moneda",
        required=True,
        default=lambda self: self.env.company.currency_id,
        tracking=True,
    )
    date = fields.Date(string="Fecha", required=True, default=fields.Date.context_today)
    concept = fields.Text(string="Concepto", required=True)
    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("submitted", "Enviada"),
            ("approved", "Aprobada"),
            ("paid", "Pagada"),
            ("rejected", "Rechazada"),
        ],
        string="Estado",
        default="draft",
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
    )

    @api.constrains("amount")
    def _check_amount(self):
        for request in self:
            if request.amount <= 0:
                raise ValidationError(_("El monto de la solicitud debe ser mayor que cero."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("state", "draft") != "draft" and not self.env.su:
                raise UserError(_("Las solicitudes se crean en borrador."))
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code("payment.request") or "/"
        return super().create(vals_list)

    def write(self, vals):
        # El estado solo cambia con los métodos del flujo, que validan grupo y estado.
        # Sin esto, cualquiera con permiso de escritura podría hacer write({"state": "approved"}).
        if "state" in vals and not self.env.su:
            raise UserError(_("El estado de la solicitud solo cambia con los botones del flujo."))
        if LOCKED_FIELDS & set(vals) and any(request.state != "draft" for request in self):
            raise UserError(_("Una solicitud enviada ya no se puede modificar."))
        return super().write(vals)

    def unlink(self):
        if any(request.state != "draft" for request in self):
            raise UserError(_("Solo se pueden eliminar solicitudes en borrador."))
        return super().unlink()

    def _check_group(self, group_xmlid, action_label):
        if not self.env.user.has_group(group_xmlid):
            raise AccessError(_("No tiene permiso para %s solicitudes de pago.", action_label))

    def _check_state(self, expected_state, action_label):
        for request in self:
            if request.state != expected_state:
                raise UserError(
                    _("No se puede %(action)s la solicitud %(name)s en estado «%(state)s».",
                      action=action_label, name=request.name,
                      state=dict(request._fields["state"].selection)[request.state])
                )

    def _set_state(self, state):
        # sudo() solo para escribir el estado, después de validar grupo y estado en cada acción.
        self.sudo().write({"state": state})

    def action_submit(self):
        self._check_state("draft", _("enviar"))
        self._set_state("submitted")

    def action_approve(self):
        self._check_group("payment_request.group_payment_request_approver", _("aprobar"))
        self._check_state("submitted", _("aprobar"))
        self._set_state("approved")

    def action_reject(self):
        self._check_group("payment_request.group_payment_request_approver", _("rechazar"))
        self._check_state("submitted", _("rechazar"))
        self._set_state("rejected")

    def action_pay(self):
        self._check_group("payment_request.group_payment_request_treasury", _("pagar"))
        self._check_state("approved", _("pagar"))
        self._set_state("paid")
