from odoo import _,models, fields, api
from datetime import datetime
from odoo.exceptions import UserError


class SaleOrder (models.Model):
    _inherit = 'sale.order'
    _description = 'Orden de Venta'

    oc_id = fields.Many2one('oc.compras', string="OC", ondelete="set null",)
    # state = fields.Selection( selection_add=[("facturado", "Facturado")])
    state_factura = fields.Selection( [("facutrado_parcial", "Facturado parcial"),("facturado", "Facturado")], string="Estados de factura")


    def create(self, vals):
        res = super(SaleOrder, self).create(vals)
        if vals["state_factura"]:
            res.state_factura = ''

        return res



    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for record in self:
            if record.state_factura:
                record.state_factura = ''
            if record.oc_id:
                grupo = self.env["procurement.group"].search([("name", "=", record.name)])
                if grupo:
                    entregas = self.env["stock.picking"].search([("group_id", "=", grupo.id)])
                    compras = self.env["purchase.order"].search([("origin", "=", record.name)])
                    if entregas and not compras:
                        for entrega in entregas:
                            entrega.oc_id = record.oc_id.id
                            # estado = self.env.ref('oc_compras.estado_entrega_atencion', raise_if_not_found=False)
                            # record.oc_id.state = estado.id
                    if compras:
                        for compra in compras:
                            compra.oc_id = record.oc_id.id  
                            estado = self.env.ref('oc_compras.estado_proveedor_solicitud', raise_if_not_found=False)
                            record.oc_id.state = estado.id
                    if record.ots:
                        record.ots.oc_id = record.oc_id.id
                        estado = self.env.ref('oc_compras.estado_servicios', raise_if_not_found=False)
                        record.oc_id.state = estado.id
        return res



# class SaleOrderLine(models.Model):
#     _inherit 