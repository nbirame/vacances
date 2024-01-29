from odoo import models, fields, api


class Dashbord(models.Model):
    _name = 'hr.leave.report'
    _description = "Dashboard des congés acquis"

    # number_of_days_allocate = fields.Float(string="Nombre de Jours acquis")
    # # number_of_days_taken = fields.Float(string="Nombre de Jours pris", _compute="_compute_number_of_days_taken")
    # # number_of_days_remaining= fields.Float(string="Nombre de Jours restant", _compute="_compute_number_of_days_remaining")
    #
    # # @api.depends()
    # def number_of_days_allocate(self):
    #     current_employee = self.env.user.employee_id.id
    #     report = self.env['hr.leave.report'].sudo().search([('employee_id', '=', current_employee)], limit=1)
    #     self.write({'number_of_days_allocate': report.number_of_days})
    #     return report.number_of_days

