from odoo import _, models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    _description = 'Orden de Venta'

    oc_id = fields.Many2one(
        'oc.compras',
        string="OC",
        ondelete="set null",
    )

    state_factura = fields.Selection(
        [
            ("facturado_parcial", "Facturado parcial"),
            ("facturado", "Facturado"),
        ],
        string="Estado de factura",
        copy=False,
        compute="_compute_state_factura",
        store=True,
    )

    fecha_factura = fields.Datetime(
        string="Fecha de facturación"
    )

    @api.depends("amount_total", "invoice_ids.amount_total", "invoice_ids.estado_sunat")
    def _compute_state_factura(self):
        for record in self:
            # Filtrar facturas válidas (ajusta según tu lógica SUNAT)
            facturas = record.invoice_ids.filtered(
                lambda f: f.l10n_latam_document_type_id.id == 64 and f.estado_sunat == "05"
            )

            _logger.info(f"Facturas relacionadas con la orden {record.name}: {[f.name for f in facturas]}")

            total_venta = record.amount_total
            total_facturado = sum(facturas.mapped("amount_total_in_currency_signed"))

            _logger.info(f"Total venta: {total_venta}")
            _logger.info(f"Total facturado: {total_facturado}")

            if total_facturado >= total_venta and total_facturado > 0:
                record.state_factura = "facturado"

            elif total_facturado > 0:
                record.state_factura = "facturado_parcial"

            else:
                record.state_factura = False



    def action_confirm(self):
        res = super().action_confirm()
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



class SaleOrder(models.Model):
    _inherit = "sale.order"

    def write(self, vals):
        # --- 1) Detectar eliminación de líneas ANTES de aplicar el write ---
        deleted_lines_info = []
        if "order_line" in vals:
            for command in vals["order_line"]:
                # command = (2, line_id, 0)  -> Odoo: "Delete"
                if command[0] == 2:
                    line_id = command[1]
                    line = self.env["sale.order.line"].browse(line_id)
                    if line.exists():
                        deleted_lines_info.append({
                            "order": line.order_id,
                            "product_name": line.product_id.display_name or line.name or _("Sin producto"),
                            "internal_ref": line.product_id.default_code or _("Sin código"),
                            "qty": line.product_uom_qty,
                            "uom": line.product_uom.name if line.product_uom else "",
                            "price_unit": line.price_unit,
                            "currency": line.order_id.currency_id.symbol or "",
                        })

        # --- 2) Detectar cambio de cliente ANTES de aplicar el write ---
        partner_change_info = []
        if "partner_id" in vals:
            for order in self:
                if order.partner_id.id != vals["partner_id"]:
                    new_partner = self.env["res.partner"].browse(vals["partner_id"])
                    partner_change_info.append({
                        "order": order,
                        "old_partner": order.partner_id,
                        "new_partner": new_partner,
                    })

        # --- 3) Ejecutar el write real ---
        result = super(SaleOrder, self).write(vals)

        # --- 4) Postear mensajes en el chatter ---
        user_name = self.env.user.name

        for info in deleted_lines_info:
            body = _(
                "Linea de producto eliminada\n"
                "Producto: %(product)s\n"
                "Codigo interno: %(code)s\n"
                "Cantidad: %(qty)s %(uom)s\n"
                "Precio unitario: %(price)s %(currency)s\n"
                "Eliminado por: %(user)s"
            ) % {
                "product": info["product_name"],
                "code": info["internal_ref"],
                "qty": info["qty"],
                "uom": info["uom"],
                "price": "%.2f" % info["price_unit"],
                "currency": info["currency"],
                "user": user_name,
            }
            info["order"].message_post(body=body, subtype_xmlid="mail.mt_note")

        for info in partner_change_info:
            body = _(
                "Cliente modificado en la cotizacion\n"
                "Cliente anterior: %(old)s\n"
                "Cliente nuevo: %(new)s\n"
                "Modificado por: %(user)s"
            ) % {
                "old": info["old_partner"].display_name or _("Sin cliente"),
                "new": info["new_partner"].display_name or _("Sin cliente"),
                "user": user_name,
            }
            info["order"].message_post(body=body, subtype_xmlid="mail.mt_note")

        return result