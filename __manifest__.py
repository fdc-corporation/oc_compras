{
    'name': 'Gestor de Órdenes de Compras',
    'version': '1.0',
    'description': 'Gestor de órdenes de compras para facilitar la administración y control de procesos.',
    'summary': 'Módulo para gestión avanzada de órdenes de compra.',
    'author': 'Yostin Palacios',
    'website': 'https://example.com',  # Cambia a tu sitio web si aplica
    'license': 'LGPL-3',
    'category': 'Sales',
    'depends': [
        'base',
        'sale',
        'account',
        'stock',
        'purchase',
        'web',
        'website',
        'solse_pe_cpe_guias',
        'pmant',
        'maintenance',
        'custom_fpc_compras'
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'view/index_tamplete.xml',
        'view/estado_view.xml',
        'view/servidor-menu.xml',
        'view/code/ir.cron.xml',
        'view/herencia_view_iherit.xml',
        'data/estados_data_oc.xml',
        'view/web/state_secuancia_oc_view.xml',
        # VISTAS PARA PORTAL USUARIO
        'view/web/portal_template.xml',
        'view/web/template_ordenes_compra.xml',
        'view/guias/action_guias_vieew.xml',
        # TEMPLATE DE EMAIL
        'view/email/template_email_oc.xml',
        'view/sale/form_sale_order.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'oc_compras/static/src/css/oc_compras.css',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
