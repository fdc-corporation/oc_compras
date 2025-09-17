from odoo import _, models, fields, api
from datetime import datetime
from odoo.exceptions import UserError, ValidationError



class InventarioOC(models.Model):
    _inherit = "stock.picking"

    oc_id = fields.Many2one("oc.compras", string="OC")

    def action_generate_eguide(self):
        result = super(InventarioOC, self).action_generate_eguide()

        for record in self:
            if record.oc_id:
                estado = self.env.ref(
                    "oc_compras.estado_guia_generado", raise_if_not_found=False
                )
                record.oc_id.state = estado.id
            else:
                sale = self.env["sale.order"].search(
                    [("name", "=", record.group_id.name), ("state", "=", "sale")]
                )
                if sale and sale.oc_id:
                    estado = self.env.ref(
                        "oc_compras.estado_guia_generado", raise_if_not_found=False
                    )
                    record.oc_id.state = estado.id
        return result

    def action_send_delivery_guide(self):
        result = super(InventarioOC, self).action_send_delivery_guide()

        for record in self:
            if record.oc_id:
                estado = self.env.ref(
                    "oc_compras.estado_guia_generado", raise_if_not_found=False
                )
                record.oc_id.state = estado.id

        return result

    def button_validate (self):
        result = super(InventarioOC, self).button_validate()
        for record in self:
            if record.picking_type_id.code == "incoming" :
                sale = self.env["sale.order"].search(
                    [("name", "=", record.group_id.name)]
                )
                if sale:
                    record.oc_id = sale.oc_id.id
                    estado = self.env.ref('oc_compras.estado_proveedor_solicitud', raise_if_not_found=False)
                    sale.oc_id.state = estado.id
        return result




class FacturaOC(models.Model):
    _inherit = "account.move"

    oc_id = fields.Many2one("oc.compras", string="OC")

    @api.constrains('invoice_origin')
    def _check_invoice_origin(self):
        for record in self:
            if record.move_type in ['out_invoice', 'in_invoice'] and not record.invoice_origin:
                raise ValidationError(_("No se puede crear una factura sin una orden de venta o compra."))


    def action_post(self):
        result = super(FacturaOC, self).action_post()

        for record in self:
            name_orden = record.invoice_origin or ""
            ordenes = [n.strip() for n in name_orden.split(",")] if "," in name_orden else [name_orden.strip()]
            sales = self.env['sale.order'].search([('name', 'in', ordenes)])

            for sale in sales:
                # Buscar todas las facturas publicadas vinculadas a la orden
                facturas = self.env['account.move'].search([
                    ('invoice_origin', 'ilike', sale.name),
                    ('state', '=', 'posted'),
                    ('move_type', '=', 'out_invoice')
                ])
                monto_facturado = sum(facturas.mapped('amount_total'))

                # Verificar estado por monto
                if not facturas:
                    sale.state_factura = False
                elif monto_facturado < sale.amount_total:
                    sale.state_factura = "facutrado_parcial"
                else:
                    sale.state_factura = "facturado"

                sale.fecha_factura = fields.Datetime.now()

                # Mantener tu lógica de OC
                if sale.oc_id:
                    record.oc_id = sale.oc_id.id
                    estado = self.env.ref('oc_compras.estado_facturado', raise_if_not_found=False)
                    if estado:
                        sale.oc_id.state = estado.id

                # Mantener tu lógica de OT
                if sale.ots:
                    orden_trabajo = self.env['maintenance.request'].search([
                        ("tarea", "=", sale.ots.id)
                    ], limit=1)
                    if orden_trabajo:
                        state_fac = self.env['maintenance.stage'].search([
                            ("is_finalizado", "=", True)
                        ], limit=1)
                        if state_fac:
                            orden_trabajo.stage_id = state_fac.id

        return result


    def button_annul(self):
        result = super(FacturaOC, self).button_annul()
        for fac in self:
            name_orden = fac.invoice_origin or ""
            ordenes = [n.strip() for n in name_orden.split(",")] if "," in name_orden else [name_orden.strip()]
            sales = self.env['sale.order'].search([('name', 'in', ordenes)])

            for sale in sales:
                # Buscar facturas activas (no canceladas) relacionadas con la venta
                facturas_activas = self.env['account.move'].search([
                    ('invoice_origin', 'ilike', sale.name),
                    ('state', '=', 'posted'),
                    ('move_type', '=', 'out_invoice')
                ])
                monto_facturado = sum(facturas_activas.mapped('amount_total'))

                if not facturas_activas:
                    # No hay facturas -> limpiar estado
                    sale.state_factura = False
                    sale.fecha_factura = False
                elif monto_facturado < sale.amount_total:
                    sale.state_factura = "facutrado_parcial"
                    sale.fecha_factura = fields.Datetime.now()
                else:
                    sale.state_factura = "facturado"
                    sale.fecha_factura = fields.Datetime.now()

                # Restaurar estado de la OC
                state_oc = self.env.ref("oc_compras.estado_guia_firmada_registrada", raise_if_not_found=False)
                if state_oc and sale.oc_id:
                    sale.oc_id.state = state_oc.id

        return result



class AccountReverse(models.TransientModel):
    _inherit = "account.move.reversal"

    def  refund_moves (self):
        result = super(AccountReverse, self).refund_moves()
        for fac in self:
            name_orden = fac.move_ids.invoice_origin if fac.move_ids.invoice_origin else ""
            ordenes = [n.strip() for n in name_orden.split(",")] if "," in name_orden else [name_orden.strip()]
            sales = self.env['sale.order'].search([('name', 'in', ordenes)])

            for sale in sales:
                # Buscar facturas activas (no canceladas) relacionadas con la venta
                facturas_activas = self.env['account.move'].search([
                    ('invoice_origin', 'ilike', sale.name),
                    ('state', '=', 'posted'),
                    ('move_type', '=', 'out_invoice')
                ])
                monto_facturado = sum(facturas_activas.mapped('amount_total'))

                if not facturas_activas:
                    # No hay facturas -> limpiar estado
                    sale.state_factura = False
                    sale.fecha_factura = False
                elif monto_facturado < sale.amount_total:
                    sale.state_factura = "facutrado_parcial"
                    sale.fecha_factura = fields.Datetime.now()
                else:
                    sale.state_factura = "facturado"
                    sale.fecha_factura = fields.Datetime.now()

                # Restaurar estado de la OC
                state_oc = self.env.ref("oc_compras.estado_guia_firmada_registrada", raise_if_not_found=False)
                if state_oc and sale.oc_id:
                    sale.oc_id.state = state_oc.id

        return result


    def  modify_moves (self):
        result = super(AccountReverse, self).modify_moves()
        for fac in self:
            name_orden = fac.move_ids.invoice_origin if fac.move_ids.invoice_origin else ""
            ordenes = [n.strip() for n in name_orden.split(",")] if "," in name_orden else [name_orden.strip()]
            sales = self.env['sale.order'].search([('name', 'in', ordenes)])

            for sale in sales:
                # Buscar facturas activas (no canceladas) relacionadas con la venta
                facturas_activas = self.env['account.move'].search([
                    ('invoice_origin', 'ilike', sale.name),
                    ('state', '=', 'posted'),
                    ('move_type', '=', 'out_invoice')
                ])
                monto_facturado = sum(facturas_activas.mapped('amount_total'))

                if not facturas_activas:
                    # No hay facturas -> limpiar estado
                    sale.state_factura = False
                    sale.fecha_factura = False
                elif monto_facturado < sale.amount_total:
                    sale.state_factura = "facutrado_parcial"
                    sale.fecha_factura = fields.Datetime.now()
                else:
                    sale.state_factura = "facturado"
                    sale.fecha_factura = fields.Datetime.now()

                # Restaurar estado de la OC
                state_oc = self.env.ref("oc_compras.estado_guia_firmada_registrada", raise_if_not_found=False)
                if state_oc and sale.oc_id:
                    sale.oc_id.state = state_oc.id

        return result

class AccountPayment(models.Model):
    _inherit = "account.payment"

    def post(self):
        res = super(AccountPayment, self).post()
        for payment in self:
            for move in payment.reconciled_invoice_ids:
                print(f"Factura {move.name} reconciliada con pago {payment.name}")
                # move.factura_pagado_oc_update()
        return res


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def action_create_payments(self):
        res = super(AccountPaymentRegister, self).action_create_payments()
        for record in self:
            for move in record.line_ids.move_id:
                if move.state == "posted":
                    print(f"Pagando factura: {move.name}")
                    # move.factura_pagado_oc_update()
        return res


class ComprasOC(models.Model):
    _inherit = "purchase.order"

    oc_id = fields.Many2one("oc.compras", string="OC")
    peso = fields.Float(string="Peso Total")

    def button_confirm(self):
        res = super(ComprasOC, self).button_confirm()
        sale = self.env["sale.order"].search([("name", "=", self.origin)])
        for record in self:
            if record.oc_id:
                estado = self.env.ref(
                    "oc_compras.estado_solicitud_aceptada", raise_if_not_found=False
                )
                if estado:
                    record.oc_id.state = estado.id
            else : 
                if sale:
                    record.oc_id =  sale.oc_id.id
                    estado = self.env.ref(
                        "oc_compras.estado_solicitud_aceptada", raise_if_not_found=False
                    )
                    if estado:
                        sale.oc_id.state = estado.id

        return res

    # def action_view_picking(self):
    #     res = super(ComprasOC, self).action_view_picking()

    #     for record in self:
    #         estado = self.env.ref(
    #             "oc_compras.estado_producto_almacen", raise_if_not_found=False
    #         )
    #         if estado:
    #             record.oc_id.state = estado.id
    #     return res



class OTS(models.Model):
    _inherit = "maintenance.request"

    order_compra = fields.Many2one(
        "oc.compras", string="Orden de compra", ondelete="set null"
    )
    oc_cliente = fields.Char(related="order_compra.oc", store=True)
    not_oc = fields.Boolean(string="No tiene OC?")

    def write(self, vals):
        res = super(OTS, self).write(vals)
        if "tarea" in vals:
            self._compute_order_compra()
        return res

    # OBTENER LA OC DE LA TAREA PARA EL MODULO DE OC_COMPRAS
    @api.onchange("tarea", "order_compra")
    def _compute_order_compra(self):
        for record in self:
            if record.tarea and record.tarea.oc_id:
                record.order_compra = record.tarea.oc_id.id
                if record.tarea.oc_id:
                    record.tarea.oc_id.ot_servicio = self.id
            else:
                record.order_compra = False

    def _validacion_etapas(self):
        res = super(OTS, self)._validacion_etapas()
        for record in self:
            if record.not_oc == False:
                if record.stage_id.sequence == 4 and not record.order_compra:
                    raise UserError(
                        _("Debe registrar la OC en el mudlo de Orden de compras")
                    )
        return res


class Tarea(models.Model):
    _inherit = "tarea.mantenimiento"
    _description = "Tareas de mantenimiento"

    oc_id = fields.Many2one("oc.compras", string="OC")

    def create_ot(self):
        res = super().create_ot()

        ot = self.env["maintenance.request"].browse(res.get("res_id"))

        if self.oc_id:
            ot.order_compra = self.oc_id.id  # <-- este campo debe existir en maintenance.request
            estado = self.env.ref('oc_compras.estado_servicios', raise_if_not_found=False)
            ot.order_compra.state = estado.id
        return res



class GuiaFirmada(models.Model):
    _name = 'guia.firmada'
    _description = 'Guía Firmada'

    oc_id = fields.Many2one('oc.compras', string='OC')
    archivo = fields.Binary(string='Archivo Firmado', required=True)
    filename = fields.Char(string='Nombre del Archivo')
    fecha_subida = fields.Datetime(string='Fecha de Subida', default=fields.Datetime.now)


class EtapasMantenimiento (models.Model):
    _inherit = "maintenance.stage"
    _description = "Etapas de mantenimiento"


    is_finalizado = fields.Boolean(string="Es la etapa de Finalizado?")