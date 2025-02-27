from odoo import models, fields, api


class EmployeeLeaveDashboard(models.Model):
    _name = 'employee.leave.dashboard'
    _description = 'Tableau de Bord des Congés des Employés'

    employee_id = fields.Many2one('hr.employee', string='Employé', required=True)
    total_leave_days = fields.Float(string='Total Jours Congé', compute='_compute_leave_days')
    used_leave_days = fields.Float(string='Jours Pris', compute='_compute_leave_days')
    remaining_leave_days = fields.Float(string='Jours Restants', compute='_compute_leave_days')

    @api.depends('employee_id')
    def _compute_leave_days(self):
        for record in self:
            leave_allocations = self.env['hr.leave.allocation'].search([('employee_id', '=', record.employee_id.id)])
            leave_taken = self.env['hr.leave'].search(
                [('employee_id', '=', record.employee_id.id), ('state', '=', 'validate')])

            total_days = sum(leave_allocations.mapped('number_of_days'))
            used_days = sum(leave_taken.mapped('number_of_days'))
            remaining_days = total_days - used_days

            record.total_leave_days = total_days
            record.used_leave_days = used_days
            record.remaining_leave_days = remaining_days


class EmployeeLeaveDashboardView(models.Model):
    _inherit = 'employee.leave.dashboard'

    def get_leave_chart_data(self):
        data = []
        for record in self.search([]):
            data.append({
                'employee': record.employee_id.name,
                'total': record.total_leave_days,
                'used': record.used_leave_days,
                'remaining': record.remaining_leave_days,
            })
        return data




class EmployeeLeaveDashboardView(models.Model):
    _inherit = 'employee.leave.dashboard'

    def get_chart_view(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'employee_leave_dashboard',
            'context': {'leave_data': self.get_leave_chart_data()},
        }

