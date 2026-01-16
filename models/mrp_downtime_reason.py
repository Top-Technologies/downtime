from odoo import models, fields, api


class MrpDowntimeReason(models.Model):
    _name = 'mrp.downtime.reason'
    _description = 'Downtime Reason'
    _order = 'name asc'

    name = fields.Char(string='Reason', required=True)

    category = fields.Selection(
        [
            ('mechanical', 'Mechanical'),
            ('electrical', 'Electrical'),
            ('material', 'Material'),
            ('manpower', 'Manpower'),
            ('planned', 'Planned'),
            ('software', 'Software'),
            ('other', 'Other')
        ],
        string="Category",
        required=True,
        default='other'
    )

    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        required=True
    )

    responsible_user_ids = fields.Many2many(
        'res.users',
        string='Responsible Users',
        required=True
    )

    notification_type = fields.Selection(
        [('activity', 'Activity')],
        default='activity'
    )

    active = fields.Boolean(default=True)

    @api.onchange('department_id')
    def _onchange_department_id(self):
        # Reset users when department changes
        self.responsible_user_ids = [(5, 0, 0)]
