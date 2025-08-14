from datetime import timedelta, datetime

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from werkzeug.urls import url_encode
from datetime import date


class Attribution(models.Model):
    _inherit = 'hr.leave.allocation'
    _description = "Attribution de Congé"
    _order = 'id desc'

    def action_send_email_notifier(self, temp):
        """Envoie un email avec un lien direct vers la demande après création."""
        self.ensure_one()

        # Base URL
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")

        # Récupération dynamique du menu et de l'action
        try:
            action_id = self.env.ref("hr_holidays.hr_leave_allocation_action_allocation").id
            menu_id = self.env.ref("hr_holidays.menu_allocation_request").id
        except ValueError:
            action_id = False
            menu_id = False

        # Construction du lien dynamique
        lien_demande = f"{base_url}/web#id={self.id}&cids=1&menu_id={menu_id}&action={action_id}&model=hr.leave.allocation&view_type=form"

        # Récupération du template
        template = self.env.ref(f"vacances.{temp}")

        if not template:
            raise UserError(_("Le modèle d'email '%s' est introuvable.") % temp)

        # On passe le lien dans le contexte pour l'utiliser dans le template
        ctx = {
            'default_model': 'hr.leave.allocation',
            'default_res_id': self.id,
            'default_use_template': bool(template.id),
            'default_template_id': template.id,
            'force_send': True,
            'lien_demande': lien_demande,  # Variable dispo dans QWeb
        }

        # Envoi de l'email
        self.with_context(ctx).message_post_with_template(template.id)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _("Un email a été envoyé avec le lien de la demande."),
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

    @api.model_create_multi
    def create(self, vals_list):
        holidays = super(Attribution, self.with_context(mail_create_nosubscribe=True)).create(vals_list)
        for holiday in holidays:
            holiday.action_send_email_notifier("email_template_drh_allocation_conge")
            partners_to_subscribe = set()
            if holiday.employee_id.user_id:
                partners_to_subscribe.add(holiday.employee_id.user_id.partner_id.id)
            if holiday.validation_type == 'officer':
                partners_to_subscribe.add(holiday.employee_id.parent_id.user_id.partner_id.id)
                partners_to_subscribe.add(holiday.employee_id.leave_manager_id.partner_id.id)
            holiday.message_subscribe(partner_ids=tuple(partners_to_subscribe))
            if not self._context.get('import_file'):
                holiday.activity_update()
            if holiday.validation_type == 'no':
                if holiday.state == 'draft':
                    holiday.action_confirm()
                    holiday.action_validate()
        return holidays

    def get_manager(self, groupe):
        drh = []
        users = self.env['res.users'].sudo().search([])
        for user in users:
            if user.has_group(groupe):
                employe = self.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)
                if employe:
                    drh.append(employe.work_email)
        return ';'.join(drh)

    def get_drh(self):
        return self.get_manager('vacances.group_conge_drh')
