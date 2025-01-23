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
        string="Colapsar en Kanban", default=False
    )  # Para colapsar columnas


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
    factura = fields.Many2one("account.move", string="Factura")
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
    prioridad = fields.Selection(
        [
            ("muy_baja", "Muy baja"),
            ("baja", "Baja"),
            ("media", "Media"),
            ("alta", "Alta"),
        ],
        string="Prioridad",
    )
    fecha_solicitud = fields.Date(string="Fecha de Solicitud")
    oc_existente = fields.Boolean(string="active_alert", compute="_compute_oc_existente")
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

        return result

    @api.depends("oc")
    def _compute_oc_existente(self):
        for record in self:
            if record.oc:
                print(record.oc)
                # Busca la OC en la cotización
                oc_cotizacion = self.env["oc.compras"].search([("oc", "=", record.oc)])
                print("----------------DATOS DE LAS OC------------------------")
                print("OC : ", oc_cotizacion)
                # Si la OC existe en la cotización, vincula la OC con la cotización
                if any(oc.id != record.id for oc in oc_cotizacion):
                    print("TRUE")
                    record.oc_existente = True
                else:
                    print("FALSE")
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
            estado = self.ruta_estado
            estado_actual = record.state.name
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

    def registrar_cotizacion(self):
        for record in self:
            if record.cotizacion_id:
                record.cotizacion_id.oc_id = record.id
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
