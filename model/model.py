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
    guia_id = fields.Binary(string="Guia Firmada")
    guia_filename = fields.Char(string="Nombre del Archivo")
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
    cotizacion_preview_html = fields.Html(string="Vista Previa", compute="_compute_cotizacion_preview_html")

    def _total_facturas(self):
        self.facturas_cantidad = len(self.factura)

    def _total_cotizaciones(self):
        self.cotizacion_cantidad = len(self.cotizacion_id)

    def _total_servicios(self):
        self.servicios_cantidad = len(self.ot_servicio)

    def _total_guias(self):
        self.guias_cantidad = len(self.guia_generada)

    def action_view_factura(self):
        return {
            "name": "Facturas",
            "domain": [("id", "in", self.factura.ids)],
            "view_type": "tree",
            "view_mode": "tree",
            "res_model": "account.move",
            "context": "{'create' : False}",
        }

    def action_view_cotizaciones(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Ventas",
            "view_mode": "form",
            "res_model": "sale.order",
            "res_id": self.cotizacion_id.id,
            "context": "{'create' : False}",
        }

    def action_view_servicios(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Ordenes de Compra",
            "view_mode": "form",
            "res_model": "maintenance.request",
            "res_id": self.ot_servicio.id,
            "context": "{'create' : False}",
        }

    def action_view_guia(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Guías Electronicas",
            "res_id": self.guia_generada.id,
            "view_mode": "form",
            "res_model": "stock.picking",
            "context": "{'create' : False}",
        }

    def descargar_guia(self):
        """Redirige a la URL de descarga"""
        self.ensure_one()
        if not self.guia_id:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Error",
                    "message": "No hay un archivo disponible para descargar.",
                    "type": "danger",
                    "sticky": False,
                },
            }
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{self.id}/guia_id?download=true",
            "target": "self",
        }
    

    def action_set_email (self):
        template = self.env.ref("oc_compras.template_oc_email")
        ctx = {
                'default_model': 'oc.compras',  # Modelo actual
                'default_res_ids': [self.id],  # ID del registro
                'default_use_template': True,
                'default_template_id': template.id,
                'default_composition_mode': 'comment',  # Modo de composición
                'force_email': True,
            }

        return {
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mail.compose.message',
                'views': [(False, 'form')],
                'view_id': False,
                'target': 'new',
                'context': ctx,
            }


    def action_post_cotizacion(self):
        self.ensure_one()
        if not self.cotizacion_id:
            return
        if self.cotizacion_id.state != 'draft' and self.cotizacion_id.state != 'sent':
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Error",
                    "message": "La cotización ya fue confirmada.",
                    "type": "danger",
                    "sticky": False,
                },
            }
        self.cotizacion_id.action_confirm()

    def action_create_invoice(self):
        self.ensure_one()
        # Validar que existe cotizacion_id
        if not self.cotizacion_id:
            return

        # Llamar el método que genera la factura desde sale.order
        # Dependiendo de tu versión:
        # invoice = self.cotizacion_id._create_invoices()
        # O si existe otro método:
        invoice = self.cotizacion_id._create_invoices()

        # Una vez creada la factura (invoice), se retorna la acción para mostrarla
        action = self.env.ref("account.action_move_out_invoice_type").read()[0]
        if invoice:
            action["views"] = [(self.env.ref("account.view_move_form").id, "form")]
            action["res_id"] = invoice.id
        return action

    @api.model
    def create(self, vals):
        vals["name"] = self.env["ir.sequence"].next_by_code("oc.compras")
        if "state" in vals:
            self.write_ruta_estado()
        return super(OrdenCompras, self).create(vals)

    def write(self, vals):
        result = super(OrdenCompras, self).write(vals)
        # self.write_oc()
        # if "oc" in vals:
        #     self.write_oc()
        if "cotizacion_id" in vals:
            self.write_oc_cotizacion()
            self.registrar_cotizacion()
            self.delete_cotizacion()
        if "state" in vals:
            self.write_ruta_estado()
            if self.state.secuencia == 8:
                self.notificacion_facturar()
        if "guia_id" in vals:
            self.registrar_guia()
        if "factura_sunat" in vals:
            self._update_estado_factura()
        return result

    def _update_estado_factura(self):
        for record in self:
            if record.factura_sunat:
                estado = self.env.ref(
                    "oc_compras.estado_facturado", raise_if_not_found=False
                )
                record.state = estado.id

    @api.depends("oc")
    def _compute_oc_existente(self):
        for record in self:
            # Verificar si el campo 'oc' está definido
            if record.oc:
                # Busca la OC en la cotización
                oc_cotizacion = self.env["oc.compras"].search([("oc", "=", record.oc)])
                record.oc_existente = any(oc.id != record.id for oc in oc_cotizacion)
            else:
                # Asignar False si 'oc' no está definido
                record.oc_existente = False

    @api.depends("cotizacion_id")
    def delete_cotizacion(self):
        for record in self:
            # Busca las cotizaciones vinculadas a esta OC
            cotizaciones = self.env["sale.order"].search([("oc_id", "=", record.id)])

            # Si tiene cotización vinculada, procesamos la desvinculación
            if record.cotizacion_id:
                for cotizacion in cotizaciones:
                    # Desvincula la OC de la cotización encontrada si no es la misma
                    if record.cotizacion_id.id != cotizacion.id:
                        cotizacion.write({"oc_id": False})
            elif not record.cotizacion_id:
                # Si no hay cotización vinculada, seguimos con el proceso de desvinculación
                for cotizacion in cotizaciones:
                    cotizacion.write({"oc_id": False})

    def write_ruta_estado(self):
        for record in self:
            estado = str(record.ruta_estado)
            estado_actual = str(record.state.name)
            if estado_actual not in estado:
                estado = str(estado) + f" - { str(estado_actual) }"
                record.ruta_estado = estado

    def notificacion_facturar(self):
        group = self.env.ref(
            "oc_compras.group_user_facturacion", raise_if_not_found=False
        )
        users = self.env["res.users"].search([("groups_id", "in", [group.id])])
        partners = users.mapped("partner_id")
        for record in self:
            record.message_post(
                body=_(
                    "🔔 La Orden de Compra %s ha sido actualizada. Entró en la etapa lista para Facturar"
                )
                % (record.name),
                subject=_("Actualización de Orden de Compra"),
                subtype_xmlid="mail.mt_comment",
                partner_ids=partners.ids,
            )

    def write_oc_cotizacion(self):
        for record in self:
            if record.cotizacion_id:
                record.cliente = record.cotizacion_id.partner_id.id
                # record.ot_servicio = record.cotizacion_id.ots.id

    @api.onchange("oc","cotizacion_id")
    def registrar_cotizacion(self):
        for record in self:
            if record.cotizacion_id:
                record.cotizacion_id.oc_id = record.id
                if record.oc:
                    record.cotizacion_id.client_order_ref = record.oc
                estado_atencion = self.env.ref(
                    "oc_compras.estado_atencion", raise_if_not_found=False
                )
                if estado_atencion:
                    record.state = estado_atencion.id
    @api.depends('cotizacion_id')
    def _compute_cotizacion_preview_html(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for record in self:
            if record.cotizacion_id:
                url = f"{base_url}/web#id={record.cotizacion_id.id}&view_type=form&model=sale.order"
                record.cotizacion_preview_html = f'<iframe src="{url}" width="100%" height="400px" style="border:1px solid #ccc;"></iframe>'
            else:
                record.cotizacion_preview_html = "<p>No hay vista previa disponible.</p>"



    def registrar_guia(self):
        if self.guia_id:
            self.state = self.env.ref(
                "oc_compras.estado_guia_firmada_registrada", raise_if_not_found=False
            ).id

    @api.model
    def _read_group_stage_ids(self, states, domain, order):
        return self.env["estado.orden"].search([], order=order)

    def create_cotizacion(self):
        for record in self:
            if record.cliente:
                coti = self.env["sale.order"].create(
                    {"partner_id": record.cliente.id, "oc_id": record.id}
                )
                record.cotizacion_id = coti.id

                return {
                    "type": "ir.actions.act_window",
                    "view_mode": "form",
                    "res_model": "sale.order",
                    "res_id": coti.id,
                    "target": "current",
                }
            else:
                raise UserError(
                    _("Antes de crear una cotizacion tienes que registrar un cliente")
                )