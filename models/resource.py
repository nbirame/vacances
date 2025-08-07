# import datetime
from datetime import timezone, timedelta

from odoo import fields, models, api, _
from datetime import datetime, time
from odoo.exceptions import ValidationError


class FerierResource(models.Model):
    _inherit = "resource.calendar.leaves"

    party_id = fields.Many2one('vacances.party', string='Fête')
    date_star = fields.Date(string='Date de début')
    date_end = fields.Date(string='Date de Fin')
    date_from = fields.Datetime(string="Date de départ", required=True, )
    date_to = fields.Datetime(string="Date de retour", required=True, )
    number_of_days_party = fields.Integer(string="Nombre de jour", store=True,
                                          readonly=False, copy=False, tracking=True, )

    def name_get(self):
        party = []
        for record in self:
            rec_name = "%s" % (record.party_id.name)
            party.append((record.id, rec_name))
        return party

    @api.onchange('date_star')
    def _onchange_date_from(self):
        for record in self:
            if record.date_star:
                record.date_from = datetime.combine(record.date_star, time.min) + timedelta(hours=8)

    @api.onchange('date_end')
    def _onchange_date_to(self):
        for record in self:
            if record.date_end:
                record.date_to = datetime.combine(record.date_end, time.min) + timedelta(hours=17)

    @api.onchange('date_from', 'date_to')
    def _onchange_number_of_days(self):
        for holiday in self:
            if holiday.date_from and holiday.date_to:
                holiday.number_of_days_party = \
                self.env['hr.leave']._get_number_of_days(holiday.date_from, holiday.date_to,
                                                         self.env.user.employee_id.id)['days']
            else:
                holiday.number_of_days_party = 0