# import datetime
from datetime import timezone, timedelta

from odoo import fields, models, api, _
from datetime import datetime, time
from odoo.exceptions import ValidationError


class Ferier(models.Model):
    _name = "vacances.ferier"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Jours de Fériés"

    party_id = fields.Many2one('vacances.party', string='Fête')
    date_star = fields.Date(string='Date de début')
    date_end = fields.Date(string='Date de Fin')
    date_debut = fields.Datetime(string="Date de départ", compute="_compute_date", required=True,
                                  default=fields.datetime.now(), tracking=True, )
    date_fin = fields.Datetime(string="Date de retour", required=True,)
    number_of_days_party = fields.Integer(string="Nombre de jour", store=True,
                                          readonly=False, copy=False, tracking=True, )
    # number_of_days_party = fields.Integer(string="Nombre de jour")

    def name_get(self):
        party = []
        for record in self:
            rec_name = "%s" % (record.party_id.name)
            party.append((record.id, rec_name))
        return party

    @api.depends('date_star')
    def _compute_date(self):
        for record in self:
            if record.date_star:
                record.date_debut = datetime.combine(record.date_star, time.min) + timedelta(hours=8)

    @api.onchange('date_end')
    def _onchange_date_fin(self):
        for record in self:
            if record.date_end:
                record.date_fin = datetime.combine(record.date_end, time.min) + timedelta(hours=17)

    @api.onchange('date_debut', 'date_fin')
    def _onchange_number_of_days(self):
        for holiday in self:
            if holiday.date_debut and holiday.date_fin:
                holiday.number_of_days_party = self.env['hr.leave']._get_number_of_days(holiday.date_debut, holiday.date_fin, self.env.user.employee_id.id)['days']
            else:
                holiday.number_of_days_party = 0

    @api.constrains('date_star', 'date_end')
    def _check_date_end(self):
        for record in self:
            if record.date_end < record.date_star:
                raise ValidationError(_("La date de fin ne doit pas inférieur"))

    # @api.constrains('number_of_days_party')
    # def _check_number_of_days_party(self):
    #     for record in self:
    #         if record.number_of_days_party <= 0 :
    #             raise ValidationError(_("Le nombre de jour doit être supérieur à 0"))

