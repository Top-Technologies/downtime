from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MrpDowntime(models.Model):
    _name = 'mrp.downtime'
    _description = 'Downtime Log'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'

    name = fields.Char(
        string='Reference',
        default='New',
        copy=False,
        readonly=True
    )

    production_id = fields.Many2one(
        'mrp.production',
        string='Manufacturing Order'
    )

    start_time = fields.Datetime(
        string='Start Time',
        required=True,
        tracking=True
    )

    end_time = fields.Datetime(
        string='End Time',
        required=True,
        tracking=True
    )

    duration_hours = fields.Float(
        string='Duration (Hours)',
        compute='_compute_duration',
        store=True,
        tracking=True
    )

    reason_id = fields.Many2one(
        'mrp.downtime.reason',
        string='Downtime Reason',
        required=True,
        tracking=True
    )

    responsible_user_ids = fields.Many2many(
        'res.users',
        string='Responsible Users',
        related='reason_id.responsible_user_ids',
        readonly=True
    )

    reported_by = fields.Many2one(
        'res.users',
        string='Reported By',
        default=lambda self: self.env.user,
        readonly=True,
        tracking=True
    )

    description = fields.Text(string='Description')

    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('approved', 'Approved')
        ],
        default='draft',
        tracking=True
    )

    is_editable = fields.Boolean(
        string="Editable",
        default=True
    )

    # ----------------------------
    # COMPUTE
    # ----------------------------
    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for rec in self:
            if rec.start_time and rec.end_time:
                delta = rec.end_time - rec.start_time
                rec.duration_hours = delta.total_seconds() / 3600
            else:
                rec.duration_hours = 0.0

    # ----------------------------
    # CREATE → OdooBot chatter
    # ----------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('mrp.downtime') or 'New'

        records = super().create(vals_list)

        for record in records:
            record.message_post(
                body=_("Downtime Log created by %s") % record.env.user.name,
                subtype_xmlid="mail.mt_note"
            )

        return records


    # ----------------------------
    # SUBMIT → Notify + OdooBot
    # ----------------------------
    def action_submit(self):
        for rec in self:
            rec.with_context(from_submit=True).write({
                'state': 'submitted',
                'is_editable': False,
            })

            rec.message_post(
                body=_("Downtime submitted by %s") % self.env.user.name,
                subtype_xmlid="mail.mt_note"
            )

            for user in rec.responsible_user_ids:
                rec.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=user.id,
                    summary='Downtime requires review',
                    note=f'Downtime reported: {rec.reason_id.name}'
                )

    def action_update_submit(self):
        for rec in self:
            rec.with_context(from_update_submit=True).write({
                'is_editable': False,
            })

            rec.message_post(
                body=_("Downtime updated by %s") % self.env.user.name,
                subtype_xmlid="mail.mt_note"
            )

    def action_edit(self):
        for rec in self:
            if rec.reported_by != self.env.user:
                raise UserError(
                    _("Only the reporter can edit this downtime log."))

            rec.is_editable = True

            rec.message_post(
                body=_("Downtime unlocked for editing by %s") % self.env.user.name,
                subtype_xmlid="mail.mt_note"
            )

    def action_approve(self):
        for rec in self:
            rec.state = 'approved'
            rec.is_editable = False

            rec.message_post(
                body=_("Downtime approved by %s") % self.env.user.name,
                subtype_xmlid="mail.mt_note"
            )

    # ----------------------------
    # EDIT AFTER SUBMISSION → Re-notify
    # ----------------------------

    def write(self, vals):
        res = super().write(vals)

        # Skip notifications during first submit
        if self.env.context.get('from_submit'):
            return res

        # Only notify when update-submit is used
        if self.env.context.get('from_update_submit'):
            for rec in self:
                for user in rec.responsible_user_ids:
                    rec.activity_schedule(
                        'mail.mail_activity_data_todo',
                        user_id=user.id,
                        summary='Downtime updated',
                        note='Downtime log was modified after submission'
                    )

        return res
