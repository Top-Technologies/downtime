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
        string='Duration (Minutes)',
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
    
    category = fields.Selection(
        # 'mrp.downtime.category',
        string='Category',
        related='reason_id.category',
        store=True,
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
            ('needs_update', 'Needs Update'),
            ('approved', 'Approved')
        ],
        default='draft',
        tracking=True
    )


    is_editable = fields.Boolean(
        string="Editable",
        default=True
    )

    is_reporter = fields.Boolean(
    compute="_compute_is_reporter",
    store=False
    )

    is_responsible = fields.Boolean(
        compute="_compute_is_responsible",
        store=False
    )

    was_submitted = fields.Boolean(
        string="Was Submitted",
        default=False
    )



    # ----------------------------
    # COMPUTE
    # ----------------------------
    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for rec in self:
            if rec.start_time and rec.end_time:
                delta = rec.end_time - rec.start_time
                rec.duration_hours = delta.total_seconds() / 3600 * 60 # convert to minutes
            else:
                rec.duration_hours = 0.0
    
    
    def _compute_is_reporter(self):
        for rec in self:
            rec.is_reporter = rec.reported_by == self.env.user


    def _compute_is_responsible(self):
        for rec in self:
            rec.is_responsible = self.env.user in rec.responsible_user_ids


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
            rec.write({
                'state': 'submitted',
                'is_editable': False,
                'was_submitted': True,
            })

            rec.message_post(
                body=_("Downtime submitted by %s") % self.env.user.name,
                subtype_xmlid="mail.mt_note"
            )

            if rec.reason_id.notification_type == 'activity':
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
            if self.env.user not in rec.responsible_user_ids:
                raise UserError(_("Only responsible users can approve this downtime."))

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

        tracked_fields = {
            'start_time', 'end_time', 'reason_id',
            'description', 'production_id'
        }

        for rec in self:
            if (
                rec.was_submitted
                and rec.state == 'submitted'
                and rec.is_editable
                and tracked_fields.intersection(vals.keys())
            ):
                rec.state = 'needs_update'

                rec.message_post(
                    body=_(
                        "Downtime log was modified by %s. "
                        "Changes require re-submission."
                    ) % self.env.user.name,
                    subtype_xmlid="mail.mt_note"
                )

        return res


