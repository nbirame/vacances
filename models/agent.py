# -*- coding: utf-8 -*-
from odoo import models, fields, api

class EmployeeInherit(models.Model):
    _inherit = 'hr.employee'

    allocation_ids = fields.One2many(
        'hr.leave.allocation',
        'employee_id',
        string='Allocations'
    )
    leave_ids = fields.One2many(
        'hr.leave',
        'employee_id',
        string='Congés'
    )

    # Champs calculés : nombre total de jours alloués, pris, restants
    allocated_days = fields.Float(
        string='Nombre total de jours alloués',
        compute='_compute_leave_info',
        store=True
    )
    used_days = fields.Float(
        string='Nombre de jours déjà pris',
        compute='_compute_leave_info',
        store=True
    )
    remaining_days = fields.Float(
        string='Nombre de jours restants',
        compute='_compute_leave_info',
        store=True
    )

    @api.depends(
        'allocation_ids',
        'leave_ids'
    )
    def _compute_leave_info(self):
        """
        Calcule en temps réel (et stocke en base) :
        - allocated_days = total des allocations validées
        - used_days = total des congés validés
        - remaining_days = différence
        Pour chaque employé.
        """
        for employee in self:
            # Filtrer allocations validées
            allocations_valides = employee.allocation_ids.filtered(
                lambda a: a.state == 'validate'
            )
            total_allocated = sum(a.number_of_days for a in allocations_valides)

            # Filtrer congés validés
            leaves_valides = employee.leave_ids.filtered(
                lambda l: l.state in ['drh', 'sg', 'ag', 'directeur', 'validate']
            )
            total_used = sum(l.number_of_days for l in leaves_valides)

            # Affecter les champs
            employee.allocated_days = total_allocated
            employee.used_days = total_used
            employee.remaining_days = total_allocated - total_used