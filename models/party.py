from odoo import models, fields


class Party(models.Model):
    _name = "vacances.party"
    _description = "Fête"

    name = fields.Char(string="Fête")
    type_fete = fields.Selection([
        ('fete_religieuse', 'Fête Religieuse'),
        ('fete_decret', 'Fête Décret'),
        ('autre', 'Autre'),
    ], store=True, string="Type de Fête", default="fete_religieuse")
