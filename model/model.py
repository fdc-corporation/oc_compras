from odoo import _,models, fields, api
from datetime import datetime
from odoo.exceptions import UserError

# class AdjuntosCorreo (models.Model):
#     _name = 'adjuntos.correo'
#     _description = 'Adjuntos de Correos'

#     name = fields.Char(string="Nombre")
#     archivo = fields.Binary(string="Archivo")

class ir_attachment (models.Model):
    _inherit = 'ir.attachment'
    _description = 'Archivos adjuntos'

    # @api.multi
    def download_file(self):
        # Aquí se puede implementar la lógica para la descarga del archivo
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % (self.id),
            'target': 'self',
        }
class OrdenCompras(models.Model):
    _name = 'oc.compras'
    _description = 'Orden de Compras'

    sequence        = fields.Char(string="N° de orden de compra")
    creado_por      = fields.Many2one('res.users', string="Creado por")
    # cotizacion_id = fields.Many2one('sale.order', string="Cotizacion", readonly=True)
    compania        = fields.Many2one('res.company', string="Compañia")
    fecha_solicitud = fields.Date(string="Fecha Solicitud", default=lambda self: fields.Date.today())
    de = fields.Char(string="De")
    # destino = fields.Char(string="Destinatario")
    asunto = fields.Char(string="Asunto")
    body = fields.Html(string="Contenido")
    # adjuntos = fields.Many2many('adjuntos.correo', string="Adjuntos")
    documentos = fields.Many2many('ir.attachment', string="Adjuntos")
    cliente = fields.Many2one('res.partner', string="Cliente")
    cotizacion_id = fields.Many2one('sale.order', string="Cotizacion")
    factura = fields.Many2one('account.move', string="Factura")
    state = fields.Selection([
        ('nueva', 'Nueva solicitud'),
        ('atencion', 'En atención'),
        ('finalizado', 'Finalizado'),
    ], string="Estado", default='nueva')
    oc = fields.Char(string="N° de OC")


    @api.model
    def create(self, vals):
        vals['sequence'] = self.env['ir.sequence'].next_by_code('oc.compras')
        if 'creado_por' not in vals:
            vals['creado_por'] = self.env.user.id
        if 'compania' not in vals:
            vals['compania'] = self.env.company.id
        return super(OrdenCompras, self).create(vals)


    def create_cotizacion (self):
        for record in self:
            if record.cliente : 
                coti = self.env['sale.order'].create({
                    'partner_id' : record.cliente.id,
                    'oc_id' : record.id
                })
                record.cotizacion_id = coti.id
                
                return {
                    'type' : 'ir.actions.act_window',
                    'view_mode' : 'form',
                    'res_model' : 'sale.order',
                    'res_id' : coti.id,
                    'target' : 'current',
                }
            else : 
                raise UserError(_("Antes de crearuna cotizacion tienes que registrar un cliente"))

