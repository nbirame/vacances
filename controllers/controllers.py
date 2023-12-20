# *- coding: utf-8 -*-

from odoo import http
from odoo.http import request


class Conge(http.Controller):

    @http.route('/conge/', website=True, auth='user', groups='conge.group_conge_AG')
    def list(self, **kw):
        objects = request.env['hr.leave'].get_agent_on_leave()
        return request.render('vacances.listing', {
            'objects': objects
        })
