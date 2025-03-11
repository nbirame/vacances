from odoo import models, fields, api

class Recapitulation(models.Model):
    _name = "vacances.recapitulation"
    _description = "Tableau de bord des congés (camembert dynamique)"

    name = fields.Selection([
        ('total_allocation', 'Total Alloué'),
        ('pris', 'Pris'),
        ('restant', 'Restant'),
    ], string='Label', required=True)

    # Champ calculé
    value = fields.Float(
        string='Valeur',
        compute='_compute_value',
        store=False,  # ou True si vous voulez l'enregistrer en base
    )

    user_id = fields.Many2one('res.users', string='Utilisateur', help="Facultatif : filtrer par utilisateur")

    @api.depends('name', 'user_id')
    def _compute_value(self):
        """
        Recalcule la valeur 'value' en fonction :
        - de la sélection 'name' (pour savoir si c'est 'total_allocation', 'pris', ou 'restant')
        - éventuellement de user_id si vous souhaitez filtrer par utilisateur
        """
        for rec in self:
            # 1) Filtrer éventuellement par user_id (trouver l'employé lié à l'utilisateur)
            #    ou bien prendre tout si user_id est vide.
            if rec.user_id:
                employees = self.env['hr.employee'].search([('user_id', '=', rec.user_id.id)])
                allocations = self.env['hr.leave.allocation'].search([
                    ('employee_id', 'in', employees.ids),
                ])
                leaves_taken = self.env['hr.leave'].search([
                    ('employee_id', 'in', employees.ids),
                    ('state', '=', 'validate')  # ou 'approved' selon config
                ])
            else:
                # Pas de filtre par user => toutes les allocations, tous les congés validés
                allocations = self.env['hr.leave.allocation'].search([])
                leaves_taken = self.env['hr.leave'].search([('state', '=', 'validate')])

            # 2) Calculer total alloué, total pris et restant
            total_allocation = sum(a.number_of_days for a in allocations)
            total_taken = sum(l.number_of_days for l in leaves_taken)
            remaining = total_allocation - total_taken

            # 3) Affecter la valeur selon l’option 'name'
            if rec.name == 'total_allocation':
                rec.value = total_allocation
            elif rec.name == 'pris':
                rec.value = total_taken
            elif rec.name == 'restant':
                rec.value = remaining
            else:
                rec.value = 0.0
