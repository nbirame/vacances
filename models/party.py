from odoo import models, fields


class Party(models.Model):
    _name = "vacances.party"
    _description = "Fête"

    name = fields.Char(string="Fête")
