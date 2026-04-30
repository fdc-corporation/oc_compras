from odoo import _,models, fields, api
from datetime import datetime
from odoo.exceptions import UserError


class SaleOrder (models.Model):
    _inherit = 'sale.order'
    _description = 'Orden de Venta'

    oc_id = fields.Many2one('oc.compras', string="OC", ondelete="set null",)
    # state = fields.Selection( selection_add=[("facturado", "Facturado")])
    state_factura = fields.Selection( [("facutrado_parcial", "Facturado parcial"),("facturado", "Facturado")], string="Estados de factura", copy=False, compute="_compute_state_factura", store=True)
    fecha_factura = fields.Datetime(string="Fecha de facturacion")

    def create(self, vals):
        res = super(SaleOrder, self).create(vals)
        if "state_factura" in vals:
            res.state_factura = ''

        return res

    def copy(self, default=None):
        default = dict(default)
        
        default.update(
            {
                "oc_id" : False,
                "state_factura" : False,
            }
        )
        return super().copy(default)
    
    
    def _compute_state_factura(self):
        for record in self:
            facturas = self.env["account.move"].search([("invoice_origin", "ilike", record.name), ("move_type", "in", ["out_invoice"]), ("state", "=", "posted"), ("edi_state", "=", "sent")])
            total_venta = record.amount_total
            total_facturado = sum(factura.amount_total_in_currency_signed for factura in facturas)
            if total_facturado >= total_venta:
                record.state_factura = "facturado"
            elif total_venta > total_facturado:
                record.state_factura = "facutrado_parcial"
            

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for record in self:
            if record.state_factura:
                record.state_factura = ''
            if record.oc_id:
                grupo = self
                if grupo:
                    entregas = self.env["stock.picking"].search([("sale_id", "=", grupo.id),("state", "!=", "cancel")])
                    compras = self.env["purchase.order"].search([("origin", "=", grupo.name),("state", "!=", "cancel")])
                    if entregas and not compras:
                        for entrega in entregas:
                            entrega.oc_id = record.oc_id.id
                            estado = self.env.ref('oc_compras.estado_entrega_atencion', raise_if_not_found=False)
                            record.oc_id.state = estado.id
                            if entrega.state != "done" and entrega.state != "cancel":
                                entrega.state = "draft"
                    if compras:
                        for compra in compras:
                            compra.oc_id = record.oc_id.id  
                            estado = self.env.ref('oc_compras.estado_proveedor_solicitud', raise_if_not_found=False)
                            record.oc_id.state = estado.id
                    if record.ots:
                        record.ots.oc_id = record.oc_id.id
                        estado = self.env.ref('oc_compras.estado_servicios', raise_if_not_found=False)
                        record.oc_id.state = estado.id
            else: 
                entregas = self.env["stock.picking"].search([("sale_id", "=", self.id),("state", "!=", "cancel")])
                if entregas:
                    for entrega in entregas:
                        if entrega.state != "done" and entrega.state != "cancel":
                            entrega.state = "draft"
        return res



# class SaleOrderLine(models.Model):
#     _inherit 