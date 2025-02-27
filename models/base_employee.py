# models/hr_employee_base_inherit.py

import datetime
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round

class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    # Vous redéclarez ici les champs mentionnés,
    # ou vous pouvez simplement ajouter/étendre s'ils n'existaient pas déjà.


    current_leave_state = fields.Selection(
        compute='_compute_leave_status',
        string="Current Time Off Status",
        selection=[
            ('draft', 'New'),
            ('confirm', 'Confirmé'),
            ('refuse', 'Refused'),
            ('validate1', 'Waiting Second Approval'),
            ('validate', 'Validé'),
            ('cancel', 'Cancelled')
        ]
    )
