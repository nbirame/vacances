# -*- coding: utf-8 -*-
from odoo import models, fields, api

class EmployeeVacationDashboard(models.Model):
    _name = 'employee.vacation.dashboard'
    _description = 'Tableau de bord des congés par employé'
    _order = 'employee_id'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employé',
        required=True,
    )
    total_allocated_days = fields.Float(
        string='Total de congés alloués',
        compute='_compute_vacation_data',
        store=False
    )
    used_days = fields.Float(
        string='Jours déjà pris',
        compute='_compute_vacation_data',
        store=False
    )
    remaining_days = fields.Float(
        string='Jours restants',
        compute='_compute_vacation_data',
        store=False
    )

    @api.depends('employee_id')
    def _compute_vacation_data(self):
        """
        Calcule les différents champs de congés
        total_allocated_days: somme des allocations validées
        used_days: somme des congés validés déjà pris
        remaining_days: différence entre total_allocated_days et used_days
        """
        for record in self:
            employee = record.employee_id
            if not employee:
                record.total_allocated_days = 0.0
                record.used_days = 0.0
                record.remaining_days = 0.0
                continue

            # Somme des jours alloués validés (hr.leave.allocation)
            allocations = self.env['hr.leave.allocation'].search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'validate'),  # ou 'validate' selon la config
            ])
            total_allocated = sum(allocation.number_of_days for allocation in allocations)

            # Somme des jours déjà pris, validés dans hr.leave
            leaves = self.env['hr.leave'].search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'validate'),  # congés validés
            ])
            used = sum(leave.number_of_days for leave in leaves)

            record.total_allocated_days = total_allocated
            record.used_days = used
            record.remaining_days = total_allocated - used
