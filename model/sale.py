from odoo import _,models, fields, api
from datetime import datetime
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

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

    def _compute_state_factura(self):
        for record in self:
            facturas = self.env["account.move"].search([("invoice_origin", "ilike", record.name), ("l10n_latam_document_type_id", "in", ["invoice"]), ("estado_sunat", "=", "05")])
            _logger.info(f"Facturas relacionadas con la orden {record.name}: {[factura.name for factura in facturas]}")
            total_venta = record.amount_total
            _logger.info(f"Total de venta para la orden {record.name}: {total_venta}")
            total_facturado = sum(factura.amount_total_in_currency_signed for factura in facturas)
            _logger.info(f"Total facturado para la orden {record.name}: {total_facturado}")
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



class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('product_id')
    def _onchange_product_id_custom(self):
        # Llamar al método original
        res = super()._onchange_product_id()
        
        if self.product_id:
            if self.product_id.description_sale:
                # Reemplazar el campo name por la descripción de venta
                self.name = self.product_id.description_sale
            else:
                return res


# class SaleOrderLine(models.Model):
#     _inherit 