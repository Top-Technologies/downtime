from odoo import models, fields, api


class MrpOperationType(models.Model):
    _name = 'mrp.operation.type'
    _description = 'Operation Type'
    _order = 'name asc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Operation Type', required=True, tracking=True )
    code = fields.Char(string='Code', required=True, tracking=True)
    
    active = fields.Boolean(default=True, tracking=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Operation type name must be unique!'),
        ('code_uniq', 'unique(code)', 'Operation type code must be unique!'),
    ]
