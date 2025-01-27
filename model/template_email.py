from odoo import fields, models, _
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime
def set_email (smtp_server, smtp_port, user,password,destino,subject, name_oc):
    mensaje = MIMEMultipart()
    modificado_asunto = f"Registro Exitoso! la OC: { subject } fue registrado"
    mensaje['Subject'] = modificado_asunto
    mensaje["FROM"] = user
    mensaje["TO"] = destino
    fecha_hoy = datetime.datetime.now().strftime("%d/%m/%Y")

    contenido= f"""
    <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Registro Exitoso</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    margin: 0;
                    padding: 20px;
                    background-color: #f9f9f9;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #ffffff;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                }}
                .header {{
                    font-size: 20px;
                    font-weight: bold;
                    margin-bottom: 20px;
                }}
                .content {{
                    margin-bottom: 20px;
                }}
                .footer {{
                    font-size: 12px;
                    color: #777;
                }}
                .highlight {{
                    color: #007BFF;
                    font-weight: bold;
                }}
                .button {{
                    display: inline-block;
                    padding: 10px 15px;
                    font-size: 14px;
                    color: #fff;
                    background-color: #007BFF;
                    text-decoration: none;
                    border-radius: 5px;
                    margin-top: 10px;
                }}
                .button:hover {{
                    background-color: #0056b3;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">¡Registro Exitoso!</div>
                <div class="content">
                    Estimado/a <strong>{destino}</strong>,
                    <p>
                        Nos complace informarle que la Orden de Compra (OC) con el número
                        <span class="highlight">{subject}</span> ha sido registrada exitosamente en nuestro sistema.
                    </p>
                    <p><strong>Detalles del registro:</strong></p>
                    <ul>
                        <li><strong>Número de OC:</strong> {name_oc}</li>
                        <li><strong>Fecha de registro:</strong> {fecha_hoy}</li>
                        <li><strong>Estado:</strong> Registrada exitosamente</li>
                    </ul>
                </div>
            </div>
        </body>
        </html>
    """
    mensaje.attach(MIMEText( contenido, 'html'))
    try: 
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(user, password)
        server.sendmail(user, destino, mensaje.as_string())
        return True
    except Exception as e :
        return False