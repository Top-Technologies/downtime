{
    'name': 'Manufacturing Downtime Management',
    'version': '1.0',
    'category': 'Manufacturing',
    'summary': 'Log and manage manufacturing downtime with notifications',
    'depends': ['mrp', 'mail', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'data/mrp_downtime_sequence.xml',
        'views/mrp_downtime_reason_views.xml',
        'views/mrp_downtime_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
}
