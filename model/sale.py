from odoo import _,models, fields, api
from datetime import datetime
from odoo.exceptions import UserError


class SaleOrder (models.Model):
    _inherit = 'sale.order'
    _description = 'Orden de Venta'

    oc_id = fields.Many2one('oc.compras', string="OC")