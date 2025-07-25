from odoo import models, fields, api, _
import imaplib
import email
from email.header import decode_header
import logging
import os
import base64
from . import template_email
from odoo.exceptions import UserError
import re

_logger = logging.getLogger(__name__)


class ServidorCorreos(models.Model):
    _name = "servidor.correos"
    _description = "Servidores de Correos"

    name = fields.Char(string="Nombre del Servidor", required=True)
    correo = fields.Char(string="Correo Electrónico")
    password = fields.Char(string="Contraseña")
    imap = fields.Char(string="Servidor IMAP")
    fecha_solicitud = fields.Date(
        string="Fecha Solicitud", default=lambda self: fields.Date.today()
    )
    creado_por = fields.Many2one("res.users", string="Creado por", required=True)
    compania = fields.Many2one("res.company", string="Compañía")
    estado = fields.Char(string="Estado", readonly=True)
    smtp = fields.Char(
        string="Servidor SMTP",
    )
    smtp_port = fields.Integer(string="Puerto SMTP", default=587)

    @api.model
    def create(self, vals):
        if "creado_por" not in vals:
            vals["creado_por"] = self.env.user.id
        if "compania" not in vals:
            vals["compania"] = self.env.company.id
        return super(ServidorCorreos, self).create(vals)

    def probar_conexion(self):
        for record in self:
            try:
                # Crear conexión
                imap = imaplib.IMAP4_SSL(record.imap)
                # Iniciar sesión
                imap.login(record.correo, record.password)

                # Verificar si puede seleccionar la bandeja de entrada
                status, mensajes = imap.select("INBOX")

                if status == "OK":
                    record.estado = "Conexión establecida"
                    return {
                        "status": "success",
                        "message": "Conexión establecida exitosamente.",
                        "mensajes": mensajes,
                    }
                else:
                    record.estado = "No se pudo conectar"
                    return {
                        "status": "error",
                        "message": "No se pudo conectar al servidor IMAP.",
                    }

            except imaplib.IMAP4.error as e:
                logging.error(f"Error de autenticación IMAP: {e}")
                record.estado = "Error de autenticación"
                return {
                    "status": "error",
                    "message": "Error de autenticación. Verifica el correo y la contraseña.",
                }

            except Exception as e:
                record.estado = "Error al conectarse al servidor"
                logging.error(f"Error al conectarse al servidor IMAP: {e}")

    def obtener_oc(self):
        for record in self.env["servidor.correos"].search(
            [("estado", "=", "Conexión establecida")]
        ):
            try:
                # Conectar al servidor IMAP
                imap = imaplib.IMAP4_SSL(record.imap)
                imap.login(record.correo, record.password)
                imap.select("INBOX")

                # Buscar correos no leídos
                status, mensajes = imap.search(None, "UNSEEN")
                if status != "OK":
                    continue

                for num in mensajes[0].split():
                    # Obtener cada mensaje no leído
                    res, mensaje = imap.fetch(num, "(RFC822)")
                    for respuesta in mensaje:
                        if isinstance(respuesta, tuple):
                            msg = email.message_from_bytes(respuesta[1])

                            # Decodificar el asunto
                            subject, encoding = decode_header(msg["Subject"])[0]
                            if isinstance(subject, bytes):
                                subject = subject.decode(
                                    encoding or "utf-8", errors="replace"
                                )

                            # Decodificar el remitente
                            from_ = msg.get("From")
                            if isinstance(from_, bytes):
                                from_ = from_.decode("utf-8", errors="replace")

                            # Obtener el correo electrónico del remitente
                            match = re.search(r'<(.*?)>', from_)
                            email_user = match.group(1) if match else from_

                            valores_oc = [
                                "OC", "Order", "Orden", "Orden ", "orden", "orden ",
                                "orden de compra", "Orden de Compra", "Orden de compra",
                                "Purchase", "PO", "ORDEN DE COMPRA", "oc", "oc: ", "oc:"
                            ]

                            # Verificar si el asunto contiene palabras clave
                            if any(valor in subject for valor in valores_oc):
                                user = self.env["res.users"].sudo().search([
                                    ("login", "=", email_user),
                                    ("share", "=", False)
                                ], limit=1)

                                orden_compra = self.env["oc.compras"].create({
                                    "de": from_,
                                    "creado_por": user.id if user else 1,
                                    "asunto": subject,
                                    "body": "",  # Se completará más adelante
                                })

                                # Obtener cuerpo y adjuntos
                                html_body = ""
                                if msg.is_multipart():
                                    for part in msg.walk():
                                        content_type = part.get_content_type()
                                        content_disposition = str(part.get("Content-Disposition"))

                                        # Obtener el cuerpo en HTML
                                        if content_type == "text/html" and "attachment" not in content_disposition:
                                            html_body = part.get_payload(decode=True).decode(
                                                "utf-8", errors="replace"
                                            )

                                        # Procesar archivos adjuntos
                                        if "attachment" in content_disposition:
                                            nombre_archivo = part.get_filename()
                                            archivo = part.get_payload(decode=True)

                                            if archivo:
                                                archivo_base64 = base64.b64encode(archivo).decode("utf-8")
                                                adjunto = self.env["ir.attachment"].create({
                                                    "name": nombre_archivo,
                                                    "type": "binary",
                                                    "datas": archivo_base64,
                                                    "res_model": "oc.compras",
                                                    "res_id": orden_compra.id,
                                                    "public": True,
                                                })
                                                orden_compra.documentos = [(4, adjunto.id)]

                                # Asignar el cuerpo del mensaje
                                orden_compra.body = html_body

                                # Confirmación de recepción (opcional)
                                if orden_compra:
                                    try:
                                        response = template_email.set_email(
                                            record.smtp,
                                            record.smtp_port,
                                            record.correo,
                                            record.password,
                                            from_,
                                            subject,
                                            orden_compra.name,
                                        )
                                    except Exception as send_err:
                                        _logger.error("Error al enviar confirmación de recepción: %s", send_err)

            except Exception as e:
                _logger.error("Error al obtener OC: %s", str(e))
