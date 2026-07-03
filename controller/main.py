from odoo import http
from odoo.http import request
from urllib.parse import quote
import base64
class DownloadRefreshController(http.Controller):

    @http.route(
        "/control/guias/add/<int:guia_id>",
        type="http",
        auth="public",
        website=True,
        csrf=False,
    )
    def get_view_guias_id(self, guia_id, **kwargs):
        guia = request.env["stock.picking"].sudo().browse(guia_id)

        if not guia.exists():
            return request.not_found()

        mensaje = kwargs.get("mensaje")
        error = kwargs.get("error")

        return request.render(
            "oc_compras.template_guia_publica",
            {
                "guia": guia,
                "imagenes": guia.guia_firmada_ids,
                "mensaje": mensaje,
                "error": error,
            },
        )

    @http.route(
        "/control/guias/add/<int:guia_id>/upload",
        type="http",
        auth="public",
        website=True,
        methods=["POST"],
        csrf=False,
    )
    def upload_imagen_guia(self, guia_id, **kwargs):
        guia = request.env["stock.picking"].sudo().browse(guia_id)

        if not guia.exists():
            return request.not_found()

        archivos = request.httprequest.files.getlist("imagenes")

        if not archivos or all(f.filename == "" for f in archivos):
            return request.redirect(
                f"/control/guias/add/{guia_id}?error=No+se+seleccionó+ninguna+imagen"
            )

        subidos = 0
        for archivo in archivos:
            if archivo and archivo.filename:
                datos = base64.b64encode(archivo.read()).decode("utf-8")
                request.env["stock.picking.guia.imagen"].sudo().create({
                    "picking_id": guia.id,
                    "imagen": datos,
                    "nombre": archivo.filename,
                })
                subidos += 1

        return request.redirect(
            f"/control/guias/add/{guia_id}?mensaje={subidos}+imagen(es)+subida(s)+correctamente"
        )

    @http.route('/download_refresh/<int:attachment_id>', type='http', auth='user')
    def download_refresh(self, attachment_id, **kwargs):
        attachment = request.env['ir.attachment'].sudo().browse(attachment_id)
        if not attachment.exists():
            return request.not_found()

        # Codificar correctamente el nombre del archivo para la URL
        download_url = '/web/content/%s/%s?download=true' % (attachment.id, quote(attachment.name))

        # HTML con JavaScript para descargar el archivo y refrescar la página
        html = """
        <html>
            <head>
                <title>Descargando...</title>
            </head>
            <body>
                <script type="text/javascript">
                    // Iniciar la descarga
                    window.location.href = "{download_url}";

                    // Esperar un segundo y refrescar la página original
                    setTimeout(function(){{
                        window.opener.location.reload();
                        window.close();
                    }}, 1000);
                </script>
                <p>La descarga debería comenzar automáticamente. Si no, haz <a href="{download_url}">clic aquí</a>.</p>
            </body>
        </html>
        """.format(download_url=download_url)

        return html

    @http.route(['/my/compras/ordenes'], auth="user", website=True, type="http")
    def get_ordenes (self, **kwargs):
        user_partner = request.env.user.partner_id
        # Obtener todos las OC de los clientes 
        if user_partner :
            domain = [("cliente", "=", user_partner.id )]
            ordenes = request.env["oc.compras"].sudo().search(domain)

            return request.render("oc_compras.ordenes_compra_portal", {"ordenes": ordenes})

    @http.route(['/my/compras/orden/<int:id_oc>'], auth="user", website=True, type="http")
    def get_state_oc (self, id_oc):
        oc = request.env["oc.compras"].sudo().browse(id_oc)
        return request.render("oc_compras.oc_state_secuencia", {
            "oc" : oc,
        })