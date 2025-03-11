from odoo import models, fields, api


class Recapitulation(models.Model):
    _name="vacances.recapitulation"
    _description="Tableau de bord des congé"

    name = fields.Char(string='Label')
    value = fields.Float(string='Valeur')

    @api.model
    def _compute_leave_data(self):
        """
        Calcule le total de congés alloués, déjà pris et restant.
        S'appuie sur hr.leave.allocation et hr.leave (validé).
        """
        # 1) Récupérer toutes les allocations (total alloué)
        allocations = self.env['hr.leave.allocation'].search([])
        total_allocation = sum(a.number_of_days for a in allocations)

        # 2) Récupérer tous les congés validés (jours pris)
        leaves_taken = self.env['hr.leave'].search([('state', '=', 'validate')])
        total_taken = sum(l.number_of_days for l in leaves_taken)

        # 3) Calculer le restant
        remaining = total_allocation - total_taken

        return {
            'total_allocation': total_allocation,
            'total_taken': total_taken,
            'remaining': remaining,
        }

    @api.model
    def action_update_leave_report(self):
        """
        Supprime les anciennes données du rapport, recalcule
        et crée 3 lignes correspondant aux 3 segments du camembert.
        """
        # Supprimer les éventuels enregistrements précédents
        self.search([]).unlink()

        data = self._compute_leave_data()
        lines = [
            {'name': 'Total Alloué', 'value': data['total_allocation']},
            {'name': 'Pris', 'value': data['total_taken']},
            {'name': 'Restant', 'value': data['remaining']},
        ]

        for line in lines:
            self.create(line)