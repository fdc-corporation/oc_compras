from odoo import _,models, fields, api
from datetime import datetime
from odoo.exceptions import UserError


class SaleOrder (models.Model):
    _inherit = 'sale.order'
    _description = 'Orden de Venta'

    oc_id = fields.Many2one('oc.compras', string="OC", ondelete="set null",)
    state = fields.Selection( selection_add=[("facturado", "Facturado")])

    def action_confirm(self):
        result = super(SaleOrder, self).action_confirm()
        for record in self:
            if record.oc_id:
                try:
                    # Buscamos el Orden de entrega de la cotizacion que cumpla 3 filtros
                    orden = self.orden_entrega_confirmada()
                    if orden:
                        estado = self.env.ref('oc_compras.estado_entrega_atencion', raise_if_not_found=False)
                        if estado:
                            record.oc_id.state = estado.id
                        else:
                            print("No se encontró el estado 'estado_entrega_atencion'.")
                    
                    elif not orden :
                        # Buscamos una OC al proveedor de la cotizacion
                        oc_proveedor = self.search_oc_proveedor() 
                        if oc_proveedor:
                            estado = self.env.ref('oc_compras.estado_proveedor_solicitud', raise_if_not_found=False)
                            if estado:
                                record.oc_id.state = estado.id
                except UserError as e:
                    print(f"Error validado por el usuario: {e}")
                except Exception as e:
                    print(f"Error inesperado: {e}")
        return result

    # def create_mantenimiento (self) :
    #     try:
    #         res = super(SaleOrder, self).create_mantenimiento()
            
    #         for record in self:
    #             if record.oc_id:
    #                 estado = self.env.ref('oc_compras.estado_servicios', raise_if_not_found=False)
    #                 print('----------------------------------------')
    #                 print(estado)
    #                 if estado: 
    #                     print('EL ESTADO EXISTE ----------------------------')

    #                     record.ots.oc_id = self.oc_id.id
    #                     record.oc_id.state = estado.id
    #         return res

    #     except Exception as e:
    #                 print(f"Error inesperado: {e}")


    def orden_entrega_confirmada(self):
        name_cotizacion = self.name
        print(self.name)
        print(self.oc_id.id)
        orden = self.env['stock.picking'].search([
            ('origin', '=', name_cotizacion),
            ('state', '=', 'assigned'),
            ('products_availability', '=', 'Disponible')
        ])
        print(orden)
        if orden:
            orden.oc_id = self.oc_id.id
            return True
        return False

    def search_oc_proveedor (self):
        for record in self:
            cotizacion = record.name
            oc_proveedor = self.env['purchase.order'].search([("origin", "ilike", cotizacion)])
            if oc_proveedor:
                oc_proveedor.oc_id = record.oc_id.id 
                return True
        return False



    # def create_invoices (self):
    #     result = super(SaleOrder, self).create_invoices()

    #     for record in self: 
    #         if record.oc_id :
    #             factura = self.env['account.move'].search([('invoice_origin', '=', record.invoice_origin)], limit=1)
    #             if factura : 
    #                 factura.oc_id = record.oc_id.id
    #                 record.oc_id.factura = factura.id
    #                 estado = self.env.ref('oc_compras.estado_facturado', raise_if_not_found=False)
    #                 if estado:
    #                     record.oc_id.state = estado.id
    #     return result


    #     else :
    #         self.ordeners_compra_proveedor_confirm()


    # def ordeners_compra_proveedor_confirm (self):
    #     return False