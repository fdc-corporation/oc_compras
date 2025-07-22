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
    de = fields.Char(string="De", tracking=True)
    asunto = fields.Char(string="Asunto")
    tarea = fields.Char(string="Asunto")
    body = fields.Html(string="Contenido")
    documentos = fields.Many2many("ir.attachment", string="Adjuntos")
    cliente = fields.Many2one("res.partner", string="Cliente")
    celular = fields.Char(related="cliente.mobile", string="Celular", store=True)
    correo = fields.Char(related="cliente.email", string="Correo", store=True)
    cotizacion_id = fields.One2many("sale.order", "oc_id", string="Cotización")
    factura = fields.One2many("account.move", 'oc_id', string="Factura")
    state = fields.Many2one(
        "estado.orden",
        string="Estado",
        tracking=True,
        required=True,group_expand='_group_expand_stages',
        default=lambda self: self.env["estado.orden"].search([], limit=1),
    )
    oc = fields.Char(string="N° de OC")
    guia_firmada_ids = fields.One2many(
            'guia.firmada',
            'oc_id',
            string='Guías Firmadas'
        )
    ruta_estado = fields.Text(string="Ruta de Estados", default="Nueva Solicitud")
    guia_generada = fields.One2many("stock.picking", 'oc_id', string="Guia Generada")
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
    tarea_mant = fields.One2many("tarea.mantenimiento", "oc_id", string="Treas mantenimiento")
    ot_servicio = fields.One2many("maintenance.request", "order_compra", string="OT Mantenimiento")
    facturas_cantidad = fields.Integer(compute="_total_facturas")
    cotizacion_cantidad = fields.Integer(compute="_total_cotizaciones")
    tareas_cantidad = fields.Integer(compute="_total_tareas_mant")
    compras_cantidad = fields.Integer(compute="_total_compras")
    servicios_cantidad = fields.Integer(compute="_total_servicios")
    guias_cantidad = fields.Integer(compute="_total_guias")
    fold = fields.Boolean(related="state.fold")
    is_finalizado = fields.Boolean(string="La OC esta finalizado", help='La OC ya esta finalizado')
    cotizacion_preview_html = fields.Html(string="Vista Previa", compute="_compute_cotizacion_preview_html")
    active = fields.Boolean(default=True)
    compras_id = fields.One2many("purchase.order", "oc_id", string="OC proveedor")
    
    
    @api.model
    def _group_expand_stages(self, stages, domain, order):
        return self.env['estado.orden'].search([], order=order)


    def _total_facturas(self):
        self.facturas_cantidad = len(self.factura)

    def _total_cotizaciones(self):
        self.cotizacion_cantidad = len(self.cotizacion_id)

    def _total_servicios(self):
        self.servicios_cantidad = len(self.ot_servicio)

    def _total_guias(self):
        self.guias_cantidad = len(self.guia_generada)


    def _total_compras(self):
        self.compras_cantidad = len(self.compras_id)
    def _total_tareas_mant(self):
        self.tareas_cantidad = len(self.tarea_mant)

    def action_view_factura(self):
        if len(self.factura) > 1 :
            return {
                "type": "ir.actions.act_window",
                "name": "Facturas",
                "domain": [("id", "in", self.factura.ids)],
                "view_type": "tree",
                "view_mode": "tree",
                "res_model": "account.move",
                "context": "{'create' : False}",
            }
        return {
            "type": "ir.actions.act_window",
            "name": "Facturas",
            "view_mode": "form",
            "res_model": "account.move",
            "res_id": self.factura.id,
            "context": "{'create' : False}",
        }

    def action_view_compras(self):
        if len(self.compras_id) > 1 :
            return {
                "type": "ir.actions.act_window",
                "name": "Compras Proveedor",
                "domain": [("id", "in", self.compras_id.ids)],
                "view_type": "tree",
                "view_mode": "tree",
                "res_model": "purchase.order",
                "context": "{'create' : False}",
            }
        return {
            "type": "ir.actions.act_window",
            "name": "Compras Proveedor",
            "view_mode": "form",
            "res_model": "purchase.order",
            "res_id": self.compras_id.id,
            "context": "{'create' : False}",
        }

    def action_view_tareas(self):
        if len(self.tarea_mant) > 1 :
            return {
                "type": "ir.actions.act_window",
                "name": "Tareas de Mantenimiento",
                "domain": [("id", "in", self.tarea_mant.ids)],
                "view_type": "tree",
                "view_mode": "tree",
                "res_model": "tarea.mantenimiento",
                "context": "{'create' : False}",
            }
        return {
            "type": "ir.actions.act_window",
            "name": "Tareas de Mantenimiento",
            "view_mode": "form",
            "res_model": "tarea.mantenimiento",
            "res_id": self.tarea_mant.id,
            "context": "{'create' : False}",
        }


    def action_view_cotizaciones(self):
        if len(self.cotizacion_id) > 1:
            return {
                "type": "ir.actions.act_window",
                "name": "Ventas",
                "domain": [("id", "in", self.cotizacion_id.ids)],
                "view_type": "tree",
                "view_mode": "tree",
                "res_model": "sale.order",
                "context": "{'create' : False}",
            } 
        return {
            "type": "ir.actions.act_window",
            "name": "Ventas",
            "view_mode": "form",
            "res_model": "sale.order",
            "res_id": self.cotizacion_id.id,
            "context": "{'create' : False}",
        }

    def action_view_servicios(self):
        if len(self.ot_servicio) > 1:
            return {
                "type": "ir.actions.act_window",
                "name": "Ordenes de Servicios",
                "domain": [("id", "in", self.ot_servicio.ids)],
                "view_type": "tree",
                "view_mode": "tree",
            "res_model": "maintenance.request",
                "context": "{'create' : False}",
            } 
        return {
            "type": "ir.actions.act_window",
                "name": "Ordenes de Servicios",
            "view_mode": "form",
            "res_model": "maintenance.request",
            "res_id": self.ot_servicio.id,
            "context": "{'create' : False}",
        }

    def action_view_guia(self):
        if len(self.guia_generada) > 1:
            return {
                "type": "ir.actions.act_window",
                "name": "Guías Electronicas",
                "domain": [("id", "in", self.guia_generada.ids)],
                "view_type": "tree",
                "view_mode": "tree",
                "res_model": "stock.picking",
                "context": "{'create' : False}",
            } 
        return {
            "type": "ir.actions.act_window",
            "name": "Guías Electronicas",
            "view_mode": "form",
            "res_model": "stock.picking",
            "res_id": self.guia_generada.id,
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
        if "cotizacion_id" in vals:
            self.action_update_data()

        return super(OrdenCompras, self).create(vals)

    def write(self, vals):
        result = super(OrdenCompras, self).write(vals)
        if "state" in vals:
            self.write_ruta_estado()
            if self.state.secuencia == 8:
                self.notificacion_facturar()
        if "guia_id" in vals:
            self.registrar_guia()
        if "factura_sunat" in vals:
            self._update_estado_factura()
        if "cotizacion_id" in vals:
            self.action_update_data()
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

    def registrar_guia(self):
        if self.guia_id:
            self.state = self.env.ref(
                "oc_compras.estado_guia_firmada_registrada", raise_if_not_found=False
            ).id

    @api.model
    def _read_group_stage_ids(self, states, domain, order):
        return self.env["estado.orden"].search([], order=order)


    def validar_ot_mantenimiento(self, coti):
        for record in self:
            orden_trabajo = self.env["maintenance.request"].search([
                ("tarea", "=", coti.ots.id)
            ], limit=1)
            factura = self.env["account.move"].search([
                    ("invoice_origin", "=", coti.name),
                    ("state", "=", "posted")
                ], limit=1)
            state_fac = self.env["maintenance.stage"].srarch([("is_finalizado", "=", True)], limit=1)
            print("DATOS DE MANTEWNIMEINTO OC ------------------------->")
            print(orden_trabajo)
            print(orden_trabajo.name)
            print(coti.name)
            print(coti.ots)
            print(coti.ots.oc_id)
            print(state_fac.name)
            coti.ots.oc_id = record.id

            if orden_trabajo:
                orden_trabajo.order_compra = record.id
                estado = self.env.ref('oc_compras.estado_servicios', raise_if_not_found=False)
                record.state = estado.id
                if factura:
                    record.orden_trabajo.stage_id = state_fac.id


    def action_update_data(self):
        for record in self:
            for coti in record.cotizacion_id:
                grupo = self.env["procurement.group"].search([("name", "=", coti.name)], limit=1)
                if grupo:
                    compras = self.env["purchase.order"].search([("origin", "=", coti.name)])
                    entregas = self.env["stock.picking"].search([("group_id", "=", grupo.id)])
                    print("DATOSSSS GLOBALES OC COMPRAS----------------------->")
                    print([("group_id", "=", grupo.id)])
                    print([("group_id", "=", grupo.name)])
                    print(entregas)
                    factura = self.env["account.move"].search([
                        ("invoice_origin", "=", coti.name),
                        ("state", "=", "posted")
                    ], limit=1)

                    # --- COMPRAS ---
                    for compra in compras:
                        compra.oc_id = record.id
                        if compra.state == 'cancel':
                            compra.oc_id = None
                            continue  # no hacer nada con compras canceladas

                        if compra.state in ('draft', 'sent'):
                            estado = self.env.ref('oc_compras.estado_proveedor_solicitud', raise_if_not_found=False)
                        elif compra.state == 'purchase':
                            estado = self.env.ref('oc_compras.estado_solicitud_aceptada', raise_if_not_found=False)
                        else:
                            recepcion = self.env["stock.picking"].search([
                                ("group_id", "=", grupo.id),
                                ("picking_type_id.code", "=", "incoming"),
                                ("state", "=", "done"),
                                ("return_ids", "=", False)
                            ], limit=1)
                            if recepcion:
                                recepcion.oc_id = record.id
                                estado = self.env.ref('oc_compras.estado_producto_almacen', raise_if_not_found=False)
                            else:
                                estado = False
                        if estado:
                            record.state = estado.id

                    # --- ENTREGAS ---
                    for entrega in entregas:
                        entrega.oc_id = record.id

                    if entregas:
                        estado = self.env.ref('oc_compras.estado_entrega_atencion', raise_if_not_found=False)
                        record.state = estado.id

                        entrega_out = self.env["stock.picking"].search([
                            ("group_id", "=", grupo.id),
                            ("picking_type_id.code", "=", "outgoing"),
                            ("state", "=", "done"),
                            ("return_ids", "=", False)
                        ], limit=1)

                        if entrega_out and entrega_out.pe_guide_number != '/':
                            estado = self.env.ref('oc_compras.estado_guia_generado', raise_if_not_found=False)
                            record.state = estado.id
                            if coti.ots:
                                self.validar_ot_mantenimiento(coti)

                    # --- FACTURA ---
                    if factura:
                        estado = self.env.ref('oc_compras.estado_facturado', raise_if_not_found=False)
                        record.state = estado.id
                        factura.oc_id = record.id
                        if factura.payment_state == 'paid':
                            estado = self.env.ref('oc_compras.estado_factura_cancelada', raise_if_not_found=False)
                            record.state = estado.id

                        if coti.ots:
                            self.validar_ot_mantenimiento(coti)

                    # --- OTS sin entregas ni factura ---
                    if not entregas and not factura and coti.ots:
                        self.validar_ot_mantenimiento(coti)
