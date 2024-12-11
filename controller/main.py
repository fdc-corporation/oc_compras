from odoo import http
from odoo.http import request

class DownloadRefreshController(http.Controller):

    @http.route('/download_refresh/<int:attachment_id>', type='http', auth='user')
    def download_refresh(self, attachment_id, **kwargs):
        attachment = request.env['ir.attachment'].sudo().browse(attachment_id)
        if not attachment.exists():
            return request.not_found()

        download_url = '/web/content/%s/%s?download=true' % (attachment.id, attachment.name)

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
