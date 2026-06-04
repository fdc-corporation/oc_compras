# -*- coding: utf-8 -*-

from odoo import _, models, fields, api
from odoo.exceptions import UserError


# ============================================================
# ESTADOS
# ============================================================
class EstadoOrden(models.Model):
    _name = "estado.orden"
    _description = "Estados de la Orden de Compras"

    name = fields.Char(string="Nombre")
    secuencia = fields.Integer(string="Secuencia")
    fold = fields.Boolean(
        string="Plegar en flujo",
        default=False,
        store=True,
    )


# ============================================================
# ADJUNTOS
# ============================================================
class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    def download_file(self):
        self.ensure_one()

        return {
            "type": "ir.actions.act_url",
            "url": "/download_refresh/%s" % self.id,
            "target": "new",
        }


# ============================================================
# ORDEN DE COMPRAS
# ============================================================
class OrdenCompras(models.Model):
    _name = "oc.compras"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Orden de Compras"

    name = fields.Char(string="N° de orden de compra")
    creado_por = fields.Many2one(
        "res.users",
        string="Creado por",
        default=lambda self: self.env.user,
    )
    compania = fields.Many2one(
        "res.company",
        string="Compañia",
        default=lambda self: self.env.company,
    )
    fecha_creacion = fields.Date(
        string="Fecha de creacion",
        default=lambda self: fields.Date.today(),
    )
    de = fields.Char(string="De", tracking=True)
    asunto = fields.Char(string="Asunto")
    tarea = fields.Char(string="Asunto")
    body = fields.Html(string="Contenido")
    documentos = fields.Many2many("ir.attachment", string="Adjuntos")
    cliente = fields.Many2one("res.partner", string="Cliente")
    celular = fields.Char(related="cliente.mobile", string="Celular", store=True)
    correo = fields.Char(related="cliente.email", string="Correo", store=True)

    cotizacion_id = fields.One2many(
        "sale.order",
        "oc_id",
        string="Cotización",
    )
    factura = fields.One2many(
        "account.move",
        "oc_id",
        string="Factura",
    )

    state = fields.Many2one(
        "estado.orden",
        string="Estado",
        tracking=True,
        required=True,
        group_expand="_group_expand_stages",
        default=lambda self: self.env["estado.orden"].search([], limit=1),
    )

    oc = fields.Char(string="N° de OC")
    guia_firmada_ids = fields.One2many(
        "guia.firmada",
        "oc_id",
        string="Guías Firmadas",
    )
    ruta_estado = fields.Text(
        string="Ruta de Estados",
        default="Nueva Solicitud",
    )
    guia_generada = fields.One2many(
        "stock.picking",
        "oc_id",
        string="Guia Generada",
    )

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
        string="active_alert",
        compute="_compute_oc_existente",
    )

    is_sunat = fields.Boolean(string="Es una factura Sunat?")
    factura_sunat = fields.Char(string="Factura Sunat")

    tarea_mant = fields.One2many(
        "tarea.mantenimiento",
        "oc_id",
        string="Tareas mantenimiento",
    )
    ot_servicio = fields.One2many(
        "maintenance.request",
        "order_compra",
        string="OT Mantenimiento",
    )

    facturas_cantidad = fields.Integer(compute="_total_facturas")
    cotizacion_cantidad = fields.Integer(compute="_total_cotizaciones")
    tareas_cantidad = fields.Integer(compute="_total_tareas_mant")
    compras_cantidad = fields.Integer(compute="_total_compras")
    servicios_cantidad = fields.Integer(compute="_total_servicios")
    guias_cantidad = fields.Integer(compute="_total_guias")

    fold = fields.Boolean(related="state.fold")
    is_finalizado = fields.Boolean(
        string="La OC esta finalizado",
        help="La OC ya esta finalizado",
    )

    cotizacion_preview_html = fields.Html(
        string="Vista Previa",
        compute="_compute_cotizacion_preview_html",
    )

    active = fields.Boolean(default=True)

    compras_id = fields.One2many(
        "purchase.order",
        "oc_id",
        string="OC proveedor",
    )

    observaciones = fields.Text(string="Observaciones")

    sale_is_draft = fields.Boolean(
        string="Las cotizaciones estan en borrador?",
        compute="_get_vaue_sale_state",
    )

    # ============================================================
    # COMPUTES
    # ============================================================
    def _get_vaue_sale_state(self):
        for record in self:
            if not record.cotizacion_id:
                record.sale_is_draft = False
                continue

            record.sale_is_draft = all(
                sale.state in ["draft", "sent"]
                for sale in record.cotizacion_id
            )

    @api.model
    def _group_expand_stages(self, stages, domain, order):
        return self.env["estado.orden"].search([], order=order)

    def _total_facturas(self):
        for record in self:
            record.facturas_cantidad = len(record.factura)

    def _total_cotizaciones(self):
        for record in self:
            record.cotizacion_cantidad = len(record.cotizacion_id)

    def _total_servicios(self):
        for record in self:
            record.servicios_cantidad = len(record.ot_servicio)

    def _total_guias(self):
        for record in self:
            record.guias_cantidad = len(record.guia_generada)

    def _total_compras(self):
        for record in self:
            record.compras_cantidad = len(record.compras_id)

    def _total_tareas_mant(self):
        for record in self:
            record.tareas_cantidad = len(record.tarea_mant)

    @api.depends("oc")
    def _compute_oc_existente(self):
        for record in self:
            if record.oc:
                oc_cotizacion = self.env["oc.compras"].search([
                    ("oc", "=", record.oc)
                ])
                record.oc_existente = any(
                    oc.id != record.id
                    for oc in oc_cotizacion
                )
            else:
                record.oc_existente = False

    # ============================================================
    # HELPERS
    # ============================================================
    def _get_action_for_records(self, name, res_model, records):
        self.ensure_one()

        if not records:
            return {
                "type": "ir.actions.act_window",
                "name": name,
                "res_model": res_model,
                "view_mode": "tree,form",
                "domain": [("id", "=", False)],
                "context": {"create": False},
            }

        if len(records) == 1:
            return {
                "type": "ir.actions.act_window",
                "name": name,
                "res_model": res_model,
                "view_mode": "form",
                "res_id": records.id,
                "context": {"create": False},
            }

        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": res_model,
            "view_mode": "tree,form",
            "domain": [("id", "in", records.ids)],
            "context": {"create": False},
        }

    def _set_state_by_xmlid(self, xmlid):
        estado = self.env.ref(xmlid, raise_if_not_found=False)
        if not estado:
            return False

        for record in self:
            record.state = estado.id

        return estado

    # ============================================================
    # SMART BUTTONS
    # ============================================================
    def action_view_factura(self):
        self.ensure_one()
        return self._get_action_for_records(
            "Facturas",
            "account.move",
            self.factura,
        )

    def action_view_compras(self):
        self.ensure_one()
        return self._get_action_for_records(
            "Compras Proveedor",
            "purchase.order",
            self.compras_id,
        )

    def action_view_tareas(self):
        self.ensure_one()
        return self._get_action_for_records(
            "Tareas de Mantenimiento",
            "tarea.mantenimiento",
            self.tarea_mant,
        )

    def action_view_cotizaciones(self):
        self.ensure_one()
        return self._get_action_for_records(
            "Ventas",
            "sale.order",
            self.cotizacion_id,
        )

    def action_view_servicios(self):
        self.ensure_one()
        return self._get_action_for_records(
            "Ordenes de Servicios",
            "maintenance.request",
            self.ot_servicio,
        )

    def action_view_guia(self):
        self.ensure_one()
        return self._get_action_for_records(
            "Guías Electronicas",
            "stock.picking",
            self.guia_generada,
        )

    # ============================================================
    # EMAIL
    # ============================================================
    def action_set_email(self):
        self.ensure_one()

        template = self.env.ref(
            "oc_compras.template_oc_email",
            raise_if_not_found=False,
        )

        ctx = {
            "default_model": "oc.compras",
            "default_res_ids": [self.id],
            "default_use_template": bool(template),
            "default_template_id": template.id if template else False,
            "default_composition_mode": "comment",
            "force_email": True,
        }

        return {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "mail.compose.message",
            "views": [(False, "form")],
            "view_id": False,
            "target": "new",
            "context": ctx,
        }

    # ============================================================
    # COTIZACIÓN
    # ============================================================
    def action_post_cotizacion(self):
        self.ensure_one()

        if not self.cotizacion_id:
            return False

        ventas_confirmables = self.cotizacion_id.filtered(
            lambda s: s.state in ["draft", "sent"]
        )

        if not ventas_confirmables:
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

        for sale in ventas_confirmables:
            needs_equipo = any(
                sale.is_servicio and not line.id_equipo
                for line in sale.order_line
            )

            if needs_equipo:
                return {
                    "name": "Confirmacion de venta",
                    "type": "ir.actions.act_window",
                    "res_model": "wizard.sale.order",
                    "view_mode": "form",
                    "target": "new",
                    "context": {"default_order_id": sale.id},
                }

            sale.action_confirm()

        return True

    def action_create_invoice(self):
        self.ensure_one()

        if not self.cotizacion_id:
            return False

        invoices = self.cotizacion_id._create_invoices()

        action = self.env.ref("account.action_move_out_invoice_type").read()[0]

        if len(invoices) == 1:
            action["views"] = [(self.env.ref("account.view_move_form").id, "form")]
            action["res_id"] = invoices.id
        else:
            action["domain"] = [("id", "in", invoices.ids)]
            action["view_mode"] = "tree,form"

        return action

    # ============================================================
    # CREATE / WRITE
    # ============================================================
    @api.model
    def create(self, vals):
        vals["name"] = self.env["ir.sequence"].next_by_code("oc.compras")
        record = super(OrdenCompras, self).create(vals)

        if "state" in vals:
            record.write_ruta_estado()

        if "cotizacion_id" in vals:
            record.action_update_data()

        return record

    def write(self, vals):
        result = super(OrdenCompras, self).write(vals)

        for record in self:
            if "state" in vals:
                record.write_ruta_estado()

                if record.state and record.state.secuencia == 8:
                    record.notificacion_facturar()

            if "factura_sunat" in vals:
                record._update_estado_factura()

            if "cotizacion_id" in vals:
                record.action_update_data()

        return result

    def _update_estado_factura(self):
        estado = self.env.ref(
            "oc_compras.estado_facturado",
            raise_if_not_found=False,
        )

        if not estado:
            return

        for record in self:
            if record.factura_sunat:
                record.state = estado.id

    def write_ruta_estado(self):
        for record in self:
            if not record.state:
                continue

            ruta_actual = record.ruta_estado or ""
            estado_actual = record.state.name or ""

            if estado_actual and estado_actual not in ruta_actual:
                record.ruta_estado = "%s - %s" % (
                    ruta_actual,
                    estado_actual,
                )

    def notificacion_facturar(self):
        group = self.env.ref(
            "oc_compras.group_user_facturacion",
            raise_if_not_found=False,
        )

        if not group:
            return

        users = self.env["res.users"].search([
            ("groups_id", "in", [group.id])
        ])
        partners = users.mapped("partner_id")

        for record in self:
            record.message_post(
                body=_(
                    "🔔 La Orden de Compra %s ha sido actualizada. Entró en la etapa lista para Facturar"
                ) % record.name,
                subject=_("Actualización de Orden de Compra"),
                subtype_xmlid="mail.mt_comment",
                partner_ids=partners.ids,
            )

    # ============================================================
    # ONCHANGE
    # ============================================================
    def write_oc_cotizacion(self):
        for record in self:
            if record.cotizacion_id:
                record.cliente = record.cotizacion_id[:1].partner_id.id

    @api.onchange("oc", "cotizacion_id")
    def registrar_cotizacion(self):
        estado_atencion = self.env.ref(
            "oc_compras.estado_atencion",
            raise_if_not_found=False,
        )

        for record in self:
            if not record.cotizacion_id:
                continue

            record.cotizacion_id.write({
                "oc_id": record.id,
                "client_order_ref": record.oc or False,
            })

            if estado_atencion:
                record.state = estado_atencion.id

    @api.model
    def _read_group_stage_ids(self, states, domain, order):
        return self.env["estado.orden"].search([], order=order)

    # ============================================================
    # VALIDACIÓN OT MANTENIMIENTO
    # ============================================================
    def validar_ot_mantenimiento(self, coti):
        """
        Corrige singleton:
        coti.ots puede tener varias tareas.
        Por eso se usa coti.ots.ids y dominio 'in'.
        """
        for record in self:
            if not coti or not coti.ots:
                continue

            tareas = coti.ots

            ordenes_trabajo = self.env["maintenance.request"].search([
                ("tarea", "in", tareas.ids)
            ])

            factura = self.env["account.move"].search([
                ("invoice_origin", "=", coti.name),
                ("state", "=", "posted"),
            ], limit=1)

            state_fac = self.env["maintenance.stage"].search([
                ("is_finalizado", "=", True)
            ], limit=1)

            tareas.write({
                "oc_id": record.id
            })

            if ordenes_trabajo:
                ordenes_trabajo.write({
                    "order_compra": record.id
                })

                estado = self.env.ref(
                    "oc_compras.estado_servicios",
                    raise_if_not_found=False,
                )

                if estado:
                    record.state = estado.id

                if factura and state_fac:
                    ordenes_trabajo.write({
                        "stage_id": state_fac.id
                    })

    # ============================================================
    # ACTUALIZAR DATA
    # ============================================================
    def action_update_data(self):
        for record in self:
            for coti in record.cotizacion_id:
                coti.client_order_ref = record.oc

                grupo = self.env["procurement.group"].search([
                    ("name", "=", coti.name)
                ], limit=1)

                if not grupo:
                    if coti.ots:
                        record.validar_ot_mantenimiento(coti)
                    continue

                compras = self.env["purchase.order"].search([
                    ("origin", "=", coti.name)
                ])

                entregas = self.env["stock.picking"].search([
                    ("group_id", "=", grupo.id)
                ])

                factura = self.env["account.move"].search([
                    ("invoice_origin", "=", coti.name),
                    ("state", "=", "posted"),
                ], limit=1)

                # ------------------------------------------------
                # COMPRAS
                # ------------------------------------------------
                for compra in compras:
                    compra.oc_id = record.id

                    if compra.state == "cancel":
                        compra.oc_id = False
                        continue

                    if compra.state in ("draft", "sent"):
                        estado = self.env.ref(
                            "oc_compras.estado_proveedor_solicitud",
                            raise_if_not_found=False,
                        )

                    elif compra.state == "purchase":
                        estado = self.env.ref(
                            "oc_compras.estado_solicitud_aceptada",
                            raise_if_not_found=False,
                        )

                    else:
                        recepcion = self.env["stock.picking"].search([
                            ("group_id", "=", grupo.id),
                            ("picking_type_id.code", "=", "incoming"),
                            ("state", "=", "done"),
                            ("return_ids", "=", False),
                        ], limit=1)

                        if recepcion:
                            recepcion.oc_id = record.id
                            estado = self.env.ref(
                                "oc_compras.estado_producto_almacen",
                                raise_if_not_found=False,
                            )
                        else:
                            estado = False

                    if estado:
                        record.state = estado.id

                # ------------------------------------------------
                # ENTREGAS
                # ------------------------------------------------
                for entrega in entregas:
                    entrega.oc_id = record.id

                if entregas:
                    estado = self.env.ref(
                        "oc_compras.estado_entrega_atencion",
                        raise_if_not_found=False,
                    )

                    if estado:
                        record.state = estado.id

                    entrega_out = self.env["stock.picking"].search([
                        ("group_id", "=", grupo.id),
                        ("picking_type_id.code", "=", "outgoing"),
                        ("state", "=", "done"),
                        ("return_ids", "=", False),
                    ], limit=1)

                    if entrega_out and entrega_out.pe_guide_number != "/":
                        estado = self.env.ref(
                            "oc_compras.estado_guia_generado",
                            raise_if_not_found=False,
                        )

                        if estado:
                            record.state = estado.id

                        if coti.ots:
                            record.validar_ot_mantenimiento(coti)

                # ------------------------------------------------
                # FACTURA
                # ------------------------------------------------
                if factura:
                    estado = self.env.ref(
                        "oc_compras.estado_facturado",
                        raise_if_not_found=False,
                    )

                    if estado:
                        record.state = estado.id

                    factura.oc_id = record.id

                    if factura.payment_state == "paid":
                        estado = self.env.ref(
                            "oc_compras.estado_factura_cancelada",
                            raise_if_not_found=False,
                        )

                        if estado:
                            record.state = estado.id

                    if coti.ots:
                        record.validar_ot_mantenimiento(coti)

                # ------------------------------------------------
                # OTS sin entregas ni factura
                # ------------------------------------------------
                if not entregas and not factura and coti.ots:
                    record.validar_ot_mantenimiento(coti)