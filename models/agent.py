# -*- coding: utf-8 -*-
from odoo import models, fields, api

class EmployeeInherit(models.Model):
    _inherit = 'hr.employee'

    allocated_days = fields.Float(
        string='Nombre total de jours alloués',
        compute='_compute_leave_info',
        store=True  # ou True si vous voulez stocker en BDD
    )
    used_days = fields.Float(
        string='Nombre de jours déjà pris',
        store=True
    )
    remaining_days = fields.Float(
        string='Nombre de jours restants',
        compute='_compute_leave_info',
        store=True
    )

    @api.onchange('allocated_days', 'used_days', 'remaining_days')
    def onchange_used_days(self):
        for employee in self:
            # 1) Calculer le total alloué (dans hr.leave.allocation)
            #    pour l'employé, dans un état validé,
            #    éventuellement sur la période en cours.
            allocations = self.env['hr.leave.allocation'].search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'validate'),  # ou 'validate', selon Odoo
            ])
            # total_allocated = sum(alloc.number_of_days for alloc in allocations)

            # 2) Calculer le total consommé (dans hr.leave) pour l'employé
            #    sur les congés validés.
            leaves_taken = self.env['hr.leave'].search([
                ('employee_id', '=', employee.id),
                ('state', 'in', ['drh','sg','ag','directeur','validate']),  # 'validate' = congés validés
            ])
            total_used = sum(leave.number_of_days for leave in leaves_taken)

            # 3) Restant = alloué - utilisé
            # employee.allocated_days = total_allocated
            employee.used_days = total_used
            # employee.remaining_days = total_allocated - total_used


    @api.depends()
    def _compute_leave_info(self):
        for employee in self:
            allocations = self.env['hr.leave.allocation'].search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'validate'),  # ou 'validate', selon Odoo
            ])
            total_allocated = sum(alloc.number_of_days for alloc in allocations)
            leaves_taken = self.env['hr.leave'].search([
                ('employee_id', '=', employee.id),
                ('state', 'in', ['drh','sg','ag','directeur','validate']),  # 'validate' = congés validés
            ])
            total_used = sum(leave.number_of_days for leave in leaves_taken)

            # 3) Restant = alloué - utilisé
            employee.allocated_days = total_allocated
            employee.used_days = total_used
            employee.remaining_days = total_allocated - total_used
