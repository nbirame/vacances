# -*- coding: utf-8 -*-
{
    'name': "Congés",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Module de gestion des Congés
    """,

    'author': "Birame NDIAYE",
    'website': "https://nbirameblog.odoo.com/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Hr',
    'version': '15.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'base_import', 'hr', 'hr_holidays', 'website'],

    # always loaded
    'data': [
        'security/conge_security.xml',
        'security/ir.model.access.csv',
        'views/ferier_view.xml',
        'data/email_notifier.xml',
        'report/report_agent_on_leave.xml',
        'report/report_template_agent_on_leave.xml',
        'views/agent_on_leave.xml',
        'views/actions.xml',
        'views/party_view.xml',
        'views/views.xml',
        'views/dashbord_view.xml',
        'views/dashbord_conge_view.xml',
        'views/agent_view.xml',
        # 'views/leave_template.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
    'license': 'LGPL-3',
}
