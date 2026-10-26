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
    approval_level_id = fields.Many2one(
        "payment.approval.level", string="Nivel de aprobación", readonly=True, copy=False, tracking=True
    )
    approver_id = fields.Many2one("res.users", string="Aprobador asignado", readonly=True, copy=False, tracking=True)
    approved_by_id = fields.Many2one("res.users", string="Aprobada por", readonly=True, copy=False)
    approved_date = fields.Datetime(string="Fecha de aprobación", readonly=True, copy=False)
    rejection_reason = fields.Text(string="Motivo del rechazo", readonly=True, copy=False)
    payment_id = fields.Many2one("account.payment", string="Pago", readonly=True, copy=False)
    payment_count = fields.Integer(compute="_compute_payment_count")

    _sql_constraints = [
        ("payment_uniq", "unique(payment_id)", "Un pago solo puede estar vinculado a una solicitud."),
    ]

    @api.depends("payment_id")
    def _compute_payment_count(self):
        for request in self:
            request.payment_count = 1 if request.payment_id else 0

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

    def _set_state(self, state, **extra):
        # sudo() solo para escribir el estado (y sus datos de auditoría), después de validar grupo y
        # estado en cada acción. write() rechaza cambios de estado que no vengan de aquí.
        self.sudo().write(dict(extra, state=state))

    def _check_assigned_approver(self, action_label):
        for request in self:
            if request.approver_id != self.env.user:
                raise AccessError(
                    _("Solo %(approver)s, el aprobador asignado, puede %(action)s la solicitud %(name)s.",
                      approver=request.approver_id.name or _("el aprobador asignado"),
                      action=action_label, name=request.name)
                )

    def _amount_in_company_currency(self):
        self.ensure_one()
        return self.currency_id._convert(self.amount, self.company_id.currency_id, self.company_id, self.date)

    def action_submit(self):
        self._check_state("draft", _("enviar"))
        Level = self.env["payment.approval.level"]
        for request in self:
            level = Level._find_for_amount(request.company_id, request._amount_in_company_currency())
            if not level:
                raise UserError(_(
                    "No hay un nivel de aprobación para el monto de la solicitud %s. "
                    "Pida a un administrador que configure los niveles en Solicitudes de pago › Configuración.",
                    request.name,
                ))
            request._set_state("submitted", approval_level_id=level.id, approver_id=level.approver_id.id)
            request.activity_schedule(
                "mail.mail_activity_data_todo",
                user_id=level.approver_id.id,
                summary=_("Aprobar solicitud de pago %s", request.name),
            )

    def action_approve(self):
        self._check_group("payment_request.group_payment_request_approver", _("aprobar"))
        self._check_state("submitted", _("aprobar"))
        self._check_assigned_approver(_("aprobar"))
        self._set_state("approved", approved_by_id=self.env.user.id, approved_date=fields.Datetime.now())
        self.activity_feedback(["mail.mail_activity_data_todo"], feedback=_("Aprobada"))

    def action_reject(self, reason):
        self._check_group("payment_request.group_payment_request_approver", _("rechazar"))
        self._check_state("submitted", _("rechazar"))
        self._check_assigned_approver(_("rechazar"))
        reason = (reason or "").strip()
        if not reason:
            raise UserError(_("Indique el motivo del rechazo."))
        self._set_state("rejected", rejection_reason=reason)
        self.activity_feedback(["mail.mail_activity_data_todo"], feedback=_("Rechazada"))
        for request in self:
            request.message_post(
                body=_("Solicitud rechazada. Motivo: %s", reason),
                partner_ids=request.requester_id.partner_id.ids,
                subtype_xmlid="mail.mt_comment",
            )

    def action_open_reject_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Rechazar solicitud"),
            "res_model": "payment.request.reject.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }

    def action_open_pay_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Registrar pago"),
            "res_model": "payment.request.pay.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }

    def _register_payment(self, journal, payment_date):
        """Crea y publica el pago a proveedor y deja la solicitud en «pagada»."""
        self.ensure_one()
        self._check_group("payment_request.group_payment_request_treasury", _("pagar"))
        self._check_state("approved", _("pagar"))
        if self.payment_id:
            raise UserError(_("La solicitud %s ya tiene un pago registrado.", self.name))
        payment = self.env["account.payment"].create({
            "payment_type": "outbound",
            "partner_type": "supplier",
            "partner_id": self.partner_id.id,
            "amount": self.amount,
            "currency_id": self.currency_id.id,
            "journal_id": journal.id,
            "date": payment_date,
            "memo": "%s - %s" % (self.name, (self.concept or "").splitlines()[0][:60]),
            "company_id": self.company_id.id,
        })
        payment.action_post()
        self._set_state("paid", payment_id=payment.id)
        self.message_post(body=_("Pago registrado: %s", payment.name))
        return payment

    def action_view_payment(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.payment",
            "res_id": self.payment_id.id,
            "view_mode": "form",
        }
