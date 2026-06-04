# -*- coding: utf-8 -*-

from odoo import _, models, fields, api
from odoo.exceptions import UserError, ValidationError


# ============================================================
# STOCK PICKING
# ============================================================
class InventarioOC(models.Model):
    _inherit = "stock.picking"

    oc_id = fields.Many2one("oc.compras", string="OC")

    def _set_oc_state(self, xmlid):
        estado = self.env.ref(xmlid, raise_if_not_found=False)
        for record in self:
            if estado and record.oc_id:
                record.oc_id.state = estado.id

    def action_generate_eguide(self):
        res = super().action_generate_eguide()
        for record in self:
            if record.oc_id:
                record._set_oc_state("oc_compras.estado_guia_generado")
        return res

    def action_send_delivery_guide(self):
        res = super().action_send_delivery_guide()
        for record in self:
            if record.oc_id:
                record._set_oc_state("oc_compras.estado_guia_generado")
        return res

    def button_validate(self):
        res = super().button_validate()

        for record in self:
            if record.picking_type_id.code == "incoming" and record.group_id:
                sale = self.env["sale.order"].search([
                    ("name", "=", record.group_id.name)
                ], limit=1)

                if sale and sale.oc_id:
                    record.oc_id = sale.oc_id.id

                    estado = self.env.ref(
                        "oc_compras.estado_proveedor_solicitud",
                        raise_if_not_found=False
                    )

                    if estado:
                        sale.oc_id.state = estado.id

        return res


# ============================================================
# FACTURAS
# ============================================================
class FacturaOC(models.Model):
    _inherit = "account.move"

    oc_id = fields.Many2one("oc.compras", string="OC")

    # ---------------- VALIDACIÓN ----------------
    @api.constrains("invoice_origin")
    def _check_invoice_origin(self):
        for record in self:
            if record.move_type in ["out_invoice", "in_invoice"] and not record.invoice_origin:
                raise ValidationError(
                    _("No se puede crear una factura sin una orden de venta o compra.")
                )

    # ---------------- MÉTODO CENTRAL ----------------
    def _update_sale_invoice_status(self, sale):
        """
        Actualiza el estado de facturación de la venta considerando:
        - Facturas publicadas.
        - Notas de crédito publicadas.
        - Monto real facturado.
        """
        if not sale:
            return

        posted_moves = sale.invoice_ids.filtered(lambda m: m.state == "posted")

        invoices = posted_moves.filtered(lambda m: m.move_type == "out_invoice")
        refunds = posted_moves.filtered(lambda m: m.move_type == "out_refund")

        total_invoice = sum(invoices.mapped("amount_total_signed"))
        total_refund = sum(refunds.mapped("amount_total_signed"))

        monto_real = total_invoice - abs(total_refund)

        if not invoices:
            sale.state_factura = False
            sale.fecha_factura = False
        elif monto_real < sale.amount_total:
            sale.state_factura = "facturado_parcial"
            sale.fecha_factura = fields.Datetime.now()
        else:
            sale.state_factura = "facturado"
            sale.fecha_factura = fields.Datetime.now()

    def _finalizar_ots_de_venta(self, sale):
        """
        Finaliza las órdenes de trabajo relacionadas a las tareas de la venta.
        Corrección principal:
        - sale.ots puede tener varias tareas.
        - No se debe usar sale.ots.id.
        - Se debe usar sale.ots.ids con operador 'in'.
        """
        if not sale or not sale.ots:
            return

        ordenes_trabajo = self.env["maintenance.request"].search([
            ("tarea", "in", sale.ots.ids)
        ])

        if not ordenes_trabajo:
            return

        state_fac = self.env["maintenance.stage"].search([
            ("is_finalizado", "=", True)
        ], limit=1)

        if state_fac:
            ordenes_trabajo.write({
                "stage_id": state_fac.id
            })

    # ---------------- POST ----------------
    def action_post(self):
        res = super().action_post()

        estado_facturado = self.env.ref(
            "oc_compras.estado_facturado",
            raise_if_not_found=False
        )

        for move in self:
            if move.move_type != "out_invoice":
                continue

            sales = move.invoice_line_ids.mapped("sale_line_ids.order_id")

            for sale in sales:
                move._update_sale_invoice_status(sale)

                if sale.oc_id:
                    move.oc_id = sale.oc_id.id

                    if estado_facturado:
                        sale.oc_id.state = estado_facturado.id

                move._finalizar_ots_de_venta(sale)

        return res

    # ---------------- CANCEL ----------------
    def button_cancel(self):
        res = super().button_cancel()

        state_oc = self.env.ref(
            "oc_compras.estado_guia_firmada_registrada",
            raise_if_not_found=False
        )

        for move in self:
            sales = move.invoice_line_ids.mapped("sale_line_ids.order_id")

            for sale in sales:
                move._update_sale_invoice_status(sale)

                if state_oc and sale.oc_id:
                    sale.oc_id.state = state_oc.id

        return res


# ============================================================
# REVERSIÓN
# ============================================================
class AccountReverse(models.TransientModel):
    _inherit = "account.move.reversal"

    def refund_moves(self):
        res = super().refund_moves()

        for wizard in self:
            for move in wizard.move_ids:
                sales = move.invoice_line_ids.mapped("sale_line_ids.order_id")

                for sale in sales:
                    move._update_sale_invoice_status(sale)

        return res

    def modify_moves(self):
        res = super().modify_moves()

        for wizard in self:
            for move in wizard.move_ids:
                sales = move.invoice_line_ids.mapped("sale_line_ids.order_id")

                for sale in sales:
                    move._update_sale_invoice_status(sale)

        return res


# ============================================================
# PAGOS
# ============================================================
class AccountPayment(models.Model):
    _inherit = "account.payment"

    def post(self):
        res = super().post()

        for payment in self:
            for move in payment.reconciled_invoice_ids:
                print(f"Factura {move.name} reconciliada con pago {payment.name}")

        return res


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def action_create_payments(self):
        res = super().action_create_payments()

        for record in self:
            for move in record.line_ids.mapped("move_id"):
                if move.state == "posted":
                    print(f"Pagando factura: {move.name}")

        return res


# ============================================================
# COMPRAS
# ============================================================
class ComprasOC(models.Model):
    _inherit = "purchase.order"

    oc_id = fields.Many2one("oc.compras", string="OC")
    peso = fields.Float(string="Peso Total")

    def button_confirm(self):
        res = super().button_confirm()

        estado_solicitud_aceptada = self.env.ref(
            "oc_compras.estado_solicitud_aceptada",
            raise_if_not_found=False
        )

        for record in self:
            sale = self.env["sale.order"].search([
                ("name", "=", record.origin)
            ], limit=1)

            if record.oc_id:
                if estado_solicitud_aceptada:
                    record.oc_id.state = estado_solicitud_aceptada.id

            elif sale and sale.oc_id:
                record.oc_id = sale.oc_id.id

                if estado_solicitud_aceptada:
                    sale.oc_id.state = estado_solicitud_aceptada.id

        return res


# ============================================================
# OT
# ============================================================
class OTS(models.Model):
    _inherit = "maintenance.request"

    order_compra = fields.Many2one("oc.compras", string="Orden de compra")
    oc_cliente = fields.Char(related="order_compra.oc", store=True)
    not_oc = fields.Boolean(string="No tiene OC?")

    @api.onchange("tarea")
    def _compute_order_compra(self):
        for record in self:
            if record.tarea and record.tarea.oc_id:
                record.order_compra = record.tarea.oc_id.id
            else:
                record.order_compra = False

    def _validacion_etapas(self):
        res = super()._validacion_etapas()

        for record in self:
            if (
                not record.not_oc
                and record.stage_id
                and record.stage_id.sequence == 4
                and not record.order_compra
            ):
                raise UserError(
                    _("Debe registrar la OC en el módulo de Orden de compras")
                )

        return res


class Tarea(models.Model):
    _inherit = "tarea.mantenimiento"

    oc_id = fields.Many2one("oc.compras", string="OC")

    def create_ot(self):
        """
        Este método normalmente se ejecuta desde una tarea individual.
        Se usa ensure_one para evitar singleton ocultos si llega un recordset múltiple.
        """
        self.ensure_one()

        res = super().create_ot()
        ot = self.env["maintenance.request"].browse(res.get("res_id")).exists()

        if ot and self.oc_id:
            ot.order_compra = self.oc_id.id

            estado = self.env.ref(
                "oc_compras.estado_servicios",
                raise_if_not_found=False
            )

            if estado and ot.order_compra:
                ot.order_compra.state = estado.id

        return res


# ============================================================
# GUIA FIRMADA
# ============================================================
class GuiaFirmada(models.Model):
    _name = "guia.firmada"
    _description = "Guía Firmada"

    oc_id = fields.Many2one("oc.compras", string="OC")
    archivo = fields.Binary(string="Archivo Firmado", required=True)
    filename = fields.Char(string="Nombre del Archivo")
    fecha_subida = fields.Datetime(
        string="Fecha de Subida",
        default=fields.Datetime.now
    )


# ============================================================
# ETAPAS MANTENIMIENTO
# ============================================================
class EtapasMantenimiento(models.Model):
    _inherit = "maintenance.stage"

    is_finalizado = fields.Boolean(string="Es la etapa Finalizado?")