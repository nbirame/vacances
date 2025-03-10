from odoo import models, fields, api


class Recapitulation(models.Model):
    _name="vacances.recapitulation"
    _description="Tableau de bord des congé"

    allocated_days = fields.Float(
        string='Nombre total de jours alloués',
        compute='_compute_leave_info',
        store=False  # ou True si vous voulez stocker en BDD
    )
    used_days = fields.Float(
        string='Nombre de jours déjà pris',
        compute='_compute_leave_info',
        store=False
    )
    remaining_days = fields.Float(
        string='Nombre de jours restants',
        compute='_compute_leave_info',
        store=False
    )
    user_id = fields.Many2one('res.users', string='Utilisateur')

    @api.depends()
    def _compute_leave_info(self):
        """
        Pour chaque employé, on calcule le total alloué, le total pris et le restant.
        """
        for employee in self:
            # 1) Calculer le total alloué (dans hr.leave.allocation)
            #    pour l'employé, dans un état validé,
            #    éventuellement sur la période en cours.
            allocations = self.env['hr.leave.allocation'].search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'validate'),  # ou 'validate', selon Odoo
            ])
            total_allocated = sum(alloc.number_of_days for alloc in allocations)

            # 2) Calculer le total consommé (dans hr.leave) pour l'employé
            #    sur les congés validés.
            leaves_taken = self.env['hr.leave'].search([
                ('employee_id', '=', employee.id),
                ('state', 'in', ['drh', 'sg', 'ag', 'directeur', 'validate']),  # 'validate' = congés validés
            ])
            total_used = sum(leave.number_of_days for leave in leaves_taken)

            # 3) Restant = alloué - utilisé
            employee.allocated_days = total_allocated
            employee.used_days = total_used
            employee.remaining_days = total_allocated - total_used
