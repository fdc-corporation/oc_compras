from odoo import http
from odoo.http import request
from urllib.parse import quote

class DownloadRefreshController(http.Controller):

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