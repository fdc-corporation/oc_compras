{
    'name': 'Gestor de Ordener de Compras',
    'version': '1.0',
    'description': 'Gestor de ordenes de compras',
    'summary': '',
    'author': 'Yostin Palacios',
    'website': '',
    'license': 'LGPL-3',
    'category': 'Sales',
    'depends': [
        'base',
        'sale',
        'account'
    ],
    'data': [
        'security/ir.model.access.csv',
        'view/index_tamplete.xml',
        'view/servidor-menu.xml',
        'view/code/ir.cron.xml',
        'view/sale.xml',
    ],
   
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3', 
}