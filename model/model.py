from odoo import _, models, fields, api
from datetime import datetime
from odoo.exceptions import UserError

# class AdjuntosCorreo (models.Model):
#     _name = 'adjuntos.correo'
#     _description = 'Adjuntos de Correos'

#     name = fields.Char(string="Nombre")
#     archivo = fields.Binary(string="Archivo")


class EstadoOrden(models.Model):
    _name = "estado.orden"
    _description = "Estados de la Orden de Compras"

    name = fields.Char(string="Nombre")
    secuencia = fields.Integer(string="Secuencia")
    fold = fields.Boolean(
        string="Plegar en flujo", default=False, store=True
    )  # Para colapsar columnas
    # fold_flujo = fields.Boolean(string="Colapsar en flujo", default=False)


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    def download_file(self):
        self.ensure_one()
        download_refresh_url = "/download_refresh/%s" % self.id
        return {
            "type": "ir.actions.act_url",
            "url": download_refresh_url,
            "target": "new",  # Abrir en una nueva pestaña
        }


class GuiasFirmas(models.Model):
    _name = "guias.firmas"
    _description = "Guias Firmadas"

    name = fields.Char(string="Nombre del Archivo")
    guia_firmada = fields.Binary(string="Guia Firmada")
    fecha_registro = fields.Date(
        string="Guia Firmada", default=lambda self: fields.Date.today()
    )


class OrdenCompras(models.Model):
    _name = "oc.compras"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Orden de Compras"

    name = fields.Char(string="N° de orden de compra")
    creado_por = fields.Many2one(
        "res.users", string="Creado por", default=lambda self: self.env.user
    )
    compania = fields.Many2one(
        "res.company", string="Compañia", default=lambda self: self.env.company
    )
    fecha_creacion = fields.Date(
        string="Fecha de creacion", default=lambda self: fields.Date.today()
    )
    de = fields.Char(string="De")
    asunto = fields.Char(string="Asunto")
    tarea = fields.Char(string="Asunto")
    body = fields.Html(string="Contenido")
    documentos = fields.Many2many("ir.attachment", string="Adjuntos")
    cliente = fields.Many2one("res.partner", string="Cliente")
    cotizacion_id = fields.Many2one("sale.order", string="Cotización")
    factura = fields.Many2many("account.move", string="Factura")
    state = fields.Many2one(
        "estado.orden",
        string="Estado",
        required=True,
        default=lambda self: self.env["estado.orden"].search([], limit=1),
    )
    oc = fields.Char(string="N° de OC")
    guias = fields.Many2many("guias.firmas", string="Guia Firmada")
    ruta_estado = fields.Text(string="Ruta de Estados")
    guia_generada = fields.Many2one("stock.picking", string="Guia Generada")
    prioridad = fields.Selection(
        [
            ("muy_baja", "Muy baja"),
            ("baja", "Baja"),
            ("media", "Media"),
            ("alta", "Alta"),
        ],
        string="Prioridad",
    )
    fecha_solicitud = fields.Date(string="Fecha de Finalizacion")
    oc_existente = fields.Boolean(
        string="active_alert", compute="_compute_oc_existente"
    )
    is_sunat = fields.Boolean(string="Es una factura Sunat?")
    factura_sunat = fields.Char(string="Factura Sunat")
    ot_servicio = fields.Many2one("maintenance.request", string="OT")
    facturas_cantidad = fields.Integer(compute="_total_facturas")
    cotizacion_cantidad = fields.Integer(compute="_total_cotizaciones")
    servicios_cantidad = fields.Integer(compute="_total_servicios")
    guias_cantidad = fields.Integer(compute="_total_guias")
    fold = fields.Boolean(related="state.fold")
    is_finalizado = fields.Boolean(string="La OC esta finalizado", help='La OC ya esta finalizado')

    @api.depends("factura", "cotizacion_id", "ot_servicio", "guias_firmadas")
    def _compute_totals(self):
        for record in self:
            record.facturas_cantidad = len(record.factura)
            record.cotizacion_cantidad = len(record.cotizacion_id)
            record.servicios_cantidad = len(record.ot_servicio)
            record.guias_cantidad = len(record.guias_firmadas)

    def action_view_factura(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Facturas",
            "view_mode": "tree,form",
            "res_model": "account.move",
            "domain": [("id", "in", self.factura.ids)],
        }

    def action_view_cotizaciones(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Cotizaciones",
            "view_mode": "tree,form",
            "res_model": "sale.order",
            "domain": [("id", "in", self.cotizacion_id.ids)],
        }

    def action_view_servicios(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Órdenes de Trabajo",
            "view_mode": "tree,form",
            "res_model": "maintenance.request",
            "domain": [("id", "in", self.ot_servicio.ids)],
        }

    def action_view_guia(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Guías Electrónicas",
            "view_mode": "tree,form",
            "res_model": "stock.picking",
            "domain": [("id", "in", self.guia_generada.ids)],
        }
