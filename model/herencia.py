from odoo import _,models, fields, api
from datetime import datetime
from odoo.exceptions import UserError


class FacturaOC (models.Model):
    _inherit = 'account.move'

    oc_id = fields.Many2one('oc.compras', string="OC")

    def write(self, vals):
        res = super(FacturaOC, self).write(vals)

        # Verificar si el estado de pago ha cambiado
        if 'payment_state' in vals:
            print('-----------EJECUCION DEL METODO PARA REGISTRO DEL PAGO---------------')
            # self.factura_pagado_oc_update()
        return res


    def action_post (self):
        result = super(FacturaOC, self).action_post()

        for record in self:
            name_orden = record.invoice_origin
            sale = self.env['sale.order'].search([('name', '=', name_orden)])

            if sale:
                sale.state_factura = "facturado"
                record.oc_id = sale.oc_id.id
                estado = self.env.ref('oc_compras.estado_facturado', raise_if_not_found=False)
                if estado:
                    record.oc_id.state_factura = estado.id
                    
                    record.oc_id.factura = [(6, 0, [record.id])]
        return result




    # def factura_pagado_oc_update(self):
    #     for record in self:
    #         if record.oc_id:
    #             print('-----------------RECORD_OC_ID')
    #             print(record.oc_id)
    #             estado = self.env.ref('oc_compras.estado_factura_cancelada', raise_if_not_found=False)
    #             if estado :                   
    #                 record.oc_id.state = estado.id
    #                 print('-----------------ESTADO ENCONTRADO')
    #                 print(estado)



class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def post(self):
        res = super(AccountPayment, self).post()
        for payment in self:
            for move in payment.reconciled_invoice_ids:
                print(f"Factura {move.name} reconciliada con pago {payment.name}")
                # move.factura_pagado_oc_update()
        return res


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    def action_create_payments(self):
        res = super(AccountPaymentRegister, self).action_create_payments()
        for record in self:
            for move in record.line_ids.move_id:
                if move.state == 'posted':
                    print(f"Pagando factura: {move.name}")
                    # move.factura_pagado_oc_update()
        return res



class ComprasOC (models.Model):
    _inherit = 'purchase.order'


    oc_id = fields.Many2one('oc.compras', string="OC")

    def button_confirm (self):
        res = super(ComprasOC, self).button_confirm()

        for record in self:
            if record.oc_id:
                    estado = self.env.ref('oc_compras.estado_solicitud_aceptada', raise_if_not_found=False)
                    if estado :
                        record.oc_id.state = estado.id
        return res

    def action_view_picking (self):
        res = super(ComprasOC, self).action_view_picking()

        for record in self:
            estado = self.env.ref('oc_compras.estado_producto_almacen', raise_if_not_found=False)
            if estado :
                record.oc_id.state = estado.id
        return res



class InventarioOC (models.Model):
    _inherit = 'stock.picking'

    oc_id = fields.Many2one('oc.compras', string="OC")

    # def button_validate (self):
    #     result = super(InventarioOC, self).button_validate()
    #     for record in self :
    #         if record.oc_id:
    #             estado = self.env.ref('oc_compras.estado_entrega_proceso', raise_if_not_found=False)
    #             record.oc_id.state = estado.id
    #         elif not record.oc_id :
    #             cotizacion = record.origin
    #             sale = self.env['sale.order'].search([('name', '=', cotizacion), ('state', '=', 'sale')])
    #             if sale and sale.oc_id :
    #                 record.oc_id = sale.oc_id.id
    #                 estado = self.env.ref('oc_compras.estado_entrega_proceso', raise_if_not_found=False)
    #                 record.oc_id.state = estado.id
    #     return result

    def action_generate_eguide (self):
        result = super(InventarioOC, self).action_generate_eguide()
        
        for record in self:
            if record.oc_id:
                estado = self.env.ref('oc_compras.estado_guia_generado', raise_if_not_found=False)
                record.oc_id.state = estado.id
            else : 
                cotizacion = record.origin
                sale = self.env['sale.order'].search([('name', '=', cotizacion), ('state', '=','sale')])
                if sale and sale.oc_id :
                    sale.oc_id.guia_generada = record.id
                    estado = self.env.ref('oc_compras.estado_guia_generado', raise_if_not_found=False)
                    record.oc_id.state = estado.id
        return result


    def action_send_delivery_guide (self):
        result = super(InventarioOC, self).action_send_delivery_guide()
        
        for record in self:
            if record.oc_id:
                estado = self.env.ref('oc_compras.estado_guia_generado', raise_if_not_found=False)
                record.oc_id.state = estado.id
        
        return result


