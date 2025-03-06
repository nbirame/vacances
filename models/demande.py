from datetime import timedelta, datetime

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from werkzeug.urls import url_encode


class Demande(models.Model):
    _inherit = 'hr.leave'
    _description = "Demande de Congé"
    _order = 'id desc'

    state = fields.Selection(selection_add=[
        ('draft', 'Brouillon'),
        ('confirm', 'Confirmé'),
        ('chefDep', 'Validation Chef Departement'),
        ('refuse', 'Refusé'),
        ('directeur', 'Validation Directeur'),
        ('drh', 'Validation DRH'),
        ('sg', 'Validation SG'),
        ('ag', 'Validation AG'),
        ('validate', 'validé'),
    ])
    type_jour = fields.Selection([
        ('jour', 'Entière'),
        ('demi-jour', 'Demi journée')
    ], store=True, tracking=True, copy=False, string="Journée"
    )
    can_validate = fields.Boolean('Can Validate', compute='_compute_can_validate')
    allocated_days = fields.Float(string="Jours alloués")
    used_days = fields.Float(
        string='Nombre de jours déjà pris',
        store=False
    )
    # remaining_days = fields.Float(
    #     string='Nombre de jours restants',
    #     store=False
    # )

    @api.model_create_multi
    def create(self, vals_list):
        """ Override to avoid automatic logging of creation """
        if not self._context.get('leave_fast_create'):
            leave_types = self.env['hr.leave.type'].browse(
                [values.get('holiday_status_id') for values in vals_list if values.get('holiday_status_id')])
            mapped_validation_type = {leave_type.id: leave_type.leave_validation_type for leave_type in leave_types}

            for values in vals_list:
                employee_id = values.get('employee_id', False)
                leave_type_id = values.get('holiday_status_id')
                # Handle automatic department_id
                if not values.get('department_id'):
                    values.update({'department_id': self.env['hr.employee'].browse(employee_id).department_id.id})

                # Handle no_validation
                if mapped_validation_type[leave_type_id] == 'no_validation':
                    values.update({'state': 'confirm'})

                if 'state' not in values:
                    # To mimic the behavior of compute_state that was always triggered, as the field was readonly
                    values['state'] = 'confirm' if mapped_validation_type[leave_type_id] != 'no_validation' else 'draft'

                # Handle double validation
                if mapped_validation_type[leave_type_id] == 'both':
                    self._check_double_validation_rules(employee_id, values.get('state', False))
                user = self.env['res.users'].sudo().search([('employee_id', '=', employee_id)], limit=1)
                # for user in users:
                if user.has_group('vacances.group_conge_directeur'):
                    values.update({'state': 'drh'})
                    self.action_send_email_notifier("email_template_drh_conge")
                elif user.has_group('vacances.group_conge_chef_service'):
                    values.update({'state': 'directeur'})
                    self.action_send_email_notifier("email_template_chefDep_conge")
                elif user.has_group('vacances.group_conge_drh'):
                    values.update({'state': 'sg'})
                    self.action_send_email_notifier("email_template_SG_conge")
                elif user.has_group('vacances.group_conge_sg'):
                    values.update({'state': 'ag'})
                    self.action_send_email_notifier("email_template_AG_conge")
                elif user.has_group('vacances.group_conge_AG'):
                    values.update({'state': 'validate'})
                else:
                    values.update({'state': 'confirm'})

        holidays = super(Demande, self.with_context(mail_create_nosubscribe=True)).create(vals_list)

        for holiday in holidays:
            if not self._context.get('leave_fast_create'):
                # Everything that is done here must be done using sudo because we might
                # have different create and write rights
                # eg : holidays_user can create a leave request with validation_type = 'manager' for someone else
                # but they can only write on it if they are leave_manager_id
                holiday_sudo = holiday.sudo()
                holiday_sudo.add_follower(employee_id)
                if holiday.validation_type == 'manager':
                    holiday_sudo.message_subscribe(partner_ids=holiday.employee_id.leave_manager_id.partner_id.ids)
                if holiday.validation_type == 'no_validation':
                    # Automatic validation should be done in sudo, because user might not have the rights to do it by himself
                    holiday_sudo.action_validate()
                    holiday_sudo.message_subscribe(partner_ids=[holiday._get_responsible_for_approval().partner_id.id])
                    holiday_sudo.message_post(body=_("The time off has been automatically approved"),
                                              subtype_xmlid="mail.mt_comment")  # Message from OdooBot (sudo)
                elif not self._context.get('import_file'):
                    holiday_sudo.activity_update()
        return holidays

    def action_confirm(self):
        # if self.filtered(lambda holiday: holiday.state != 'draft'):
        #     raise UserError(_('Time off request must be in Draft state ("To Submit") in order to confirm it.'))
        current_employee = self.env.user.employee_id.id
        user = self.env['res.users'].sudo().search([('employee_id', '=', current_employee)], limit=1)
        # for user in users:
        if user.has_group('vacances.group_conge_directeur'):
            self.sudo().write({'state': 'drh'})
            self.action_send_email_notifier("email_template_drh_conge")
        elif user.has_group('vacances.group_conge_chef_service'):
            self.update({'state': 'directeur'})
            self.action_send_email_notifier("email_template_directeur_conge")
        elif user.has_group('vacances.group_conge_drh'):
            self.sudo().write({'state': 'sg'})
            self.action_send_email_notifier("email_template_SG_conge")
        elif user.has_group('vacances.group_conge_sg'):
            self.sudo().write({'state': 'ag'})
            self.action_send_email_notifier("email_template_AG_conge")
        elif user.has_group('vacances.group_conge_AG'):
            self.sudo().write({'state': 'validate'})
        else:
            self.sudo().write({'state': 'chefDep'})
            self.action_send_email_notifier("email_template_chefDep_conge")
        # self.sudo().write({'state': 'chefDep'})
        holidays = self.filtered(lambda leave: leave.validation_type == 'no_validation')
        if holidays:
            # Automatic validation should be done in sudo, because user might not have the rights to do it by himself
            holidays.sudo().action_validate()
        self.activity_update()
        return True

    def action_drh(self):
        self.write({'state': 'sg'})
        self.action_send_email_notifier("email_template_SG_conge")
        # self.action_send_email_notifier("email_template_drh_conge")

    def action_sg(self):
        self.write({'state': 'ag'})
        self.action_send_email_notifier("email_template_AG_conge")
        # self.action_send_email_notifier("email_template_SG_conge")

    def action_ag(self):
        self.write({'state': 'validate'})
        self.action_send_email_notifier("email_template_AG_conge")

    def action_annuler(self):
        self.write({'state': 'refuse'})
        self.action_send_email_notifier("email_template_rejeter_conge")

    # def action_chef(self):
    #     self.write({'state': 'chef'})
    #     self.action_send_email_notifier("email_template_chefService_conge")

    def action_chefDep(self):
        self.write({'state': 'directeur'})
        self.action_send_email_notifier("email_template_directeur_conge") # email_template_drh_conge
        # self.action_send_email_notifier("email_template_chefDep_conge")

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_directeur(self):
        self.action_send_email_notifier("email_template_drh_conge")
        self.write({'state': 'drh'})

    def action_validate(self):
        current_employee = self.env.user.employee_id
        leaves = self._get_leaves_on_public_holiday()
        if leaves:
            raise ValidationError(
                _('The following employees are not supposed to work during that period:\n %s') % ','.join(
                    leaves.mapped('employee_id.name')))

        if any(holiday.state not in ['confirm', 'directeur', 'drh', 'sg',
                                     'ag', 'chefDep', 'validate'] and holiday.validation_type != 'no_validation' for holiday
               in self):
            raise UserError(_('Time off request must be confirmed in order to approve it.'))

        self.write({'state': 'validate'})
        # self.action_send_email_notifier("email_template_reponse_conge")
        leaves_second_approver = self.env['hr.leave']
        leaves_first_approver = self.env['hr.leave']

        for leave in self:
            if leave.validation_type == 'both':
                leaves_second_approver += leave
            else:
                leaves_first_approver += leave

            if leave.holiday_type != 'employee' or \
                    (leave.holiday_type == 'employee' and len(leave.employee_ids) > 1):
                employees = leave._get_employees_from_holiday_type()

                conflicting_leaves = self.env['hr.leave'].with_context(
                    tracking_disable=True,
                    mail_activity_automation_skip=True,
                    leave_fast_create=True
                ).search([
                    ('date_from', '<=', leave.date_to),
                    ('date_to', '>', leave.date_from),
                    ('state', 'not in', ['cancel', 'refuse']),
                    ('holiday_type', '=', 'employee'),
                    ('employee_id', 'in', employees.ids)])

                if conflicting_leaves:
                    # YTI: More complex use cases could be managed in master
                    if leave.leave_type_request_unit != 'day' or any(
                            l.leave_type_request_unit == 'hour' for l in conflicting_leaves):
                        raise ValidationError(_('You can not have 2 time off that overlaps on the same day.'))

                    # keep track of conflicting leaves states before refusal
                    target_states = {l.id: l.state for l in conflicting_leaves}
                    conflicting_leaves.action_refuse()
                    split_leaves_vals = []
                    for conflicting_leave in conflicting_leaves:
                        if conflicting_leave.leave_type_request_unit == 'half_day' and conflicting_leave.request_unit_half:
                            continue

                        # Leaves in days
                        if conflicting_leave.date_from < leave.date_from:
                            before_leave_vals = conflicting_leave.copy_data({
                                'date_from': conflicting_leave.date_from.date(),
                                'date_to': leave.date_from.date() + timedelta(days=-1),
                                'state': target_states[conflicting_leave.id],
                            })[0]
                            before_leave = self.env['hr.leave'].new(before_leave_vals)
                            before_leave._compute_date_from_to()
                            if before_leave.date_from < before_leave.date_to:
                                split_leaves_vals.append(before_leave._convert_to_write(before_leave._cache))
                        if conflicting_leave.date_to > leave.date_to:
                            after_leave_vals = conflicting_leave.copy_data({
                                'date_from': leave.date_to.date() + timedelta(days=1),
                                'date_to': conflicting_leave.date_to.date(),
                                'state': target_states[conflicting_leave.id],
                            })[0]
                            after_leave = self.env['hr.leave'].new(after_leave_vals)
                            after_leave._compute_date_from_to()
                            # Could happen for part-time contract, that time off is not necessary
                            # anymore.
                            if after_leave.date_from < after_leave.date_to:
                                split_leaves_vals.append(after_leave._convert_to_write(after_leave._cache))

                    split_leaves = self.env['hr.leave'].with_context(
                        tracking_disable=True,
                        mail_activity_automation_skip=True,
                        leave_fast_create=True,
                        leave_skip_state_check=True
                    ).create(split_leaves_vals)

                    split_leaves.filtered(lambda l: l.state in 'validate')._validate_leave_request()

                values = leave._prepare_employees_holiday_values(employees)
                leaves = self.env['hr.leave'].with_context(
                    tracking_disable=True,
                    mail_activity_automation_skip=True,
                    leave_fast_create=True,
                    no_calendar_sync=True,
                    leave_skip_state_check=True,
                ).create(values)

                leaves._validate_leave_request()

        leaves_second_approver.write({'second_approver_id': current_employee.id})
        leaves_first_approver.write({'first_approver_id': current_employee.id})

        employee_requests = self.filtered(lambda hol: hol.holiday_type == 'employee')
        employee_requests._validate_leave_request()
        if not self.env.context.get('leave_fast_create'):
            employee_requests.filtered(lambda holiday: holiday.validation_type != 'no_validation').activity_update()
        return True

    @api.depends('employee_id', 'state')
    def _compute_can_validate(self):
        current_employee = self.env.user.employee_id.id
        user = self.env['res.users'].sudo().search([('employee_id', '=', current_employee)], limit=1)
        leaves = self.env['hr.leave'].sudo().search([])
        # for user in users:
        if user.has_group('vacances.group_conge_directeur'):
            for leave_can in leaves:
                if leave_can.state == "drh":
                    self.can_validate =True

    @api.depends('date_from', 'date_to', 'employee_id', 'type_jour')
    def _compute_number_of_days(self):
        for holiday in self:
            if holiday.date_from and holiday.date_to:
                fete = self.env["vacances.ferier"].sudo().search([])
                if fete:
                    for jour_fete in fete:
                        if holiday.date_from <= jour_fete.date_debut <= jour_fete.date_fin <= holiday.date_to:
                            number_day_party_one = holiday._get_number_of_days(holiday.date_from, jour_fete.date_debut,
                                                                               holiday.employee_id.id)['days']
                            number_day_party_two = holiday._get_number_of_days(jour_fete.date_fin, holiday.date_to,
                                                                               holiday.employee_id.id)['days']
                            if holiday.type_jour == 'demi-jour':
                                holiday.number_of_days = (number_day_party_one + number_day_party_two) / 2
                            else:
                                holiday.number_of_days = number_day_party_one + number_day_party_two
                            # print(holiday.number_of_days)
                        else:
                            if holiday.type_jour == 'demi-jour':
                                nombre = \
                                holiday._get_number_of_days(holiday.date_from, holiday.date_to, holiday.employee_id.id)[
                                    'days']
                                holiday.number_of_days = nombre / 2
                            else:
                                holiday.number_of_days = \
                                    holiday._get_number_of_days(holiday.date_from, holiday.date_to,
                                                                holiday.employee_id.id)[
                                        'days']
                else:
                    if holiday.type_jour == 'demi-jour':
                        number_day = \
                        holiday._get_number_of_days(holiday.date_from, holiday.date_to, holiday.employee_id.id)['days']
                        holiday.number_of_days = number_day / 2
                    else:
                        holiday.number_of_days = \
                            holiday._get_number_of_days(holiday.date_from, holiday.date_to, holiday.employee_id.id)[
                                'days']
            else:
                if holiday.type_jour == 'demi-jour':
                    holiday.number_of_days = holiday.number_of_days = \
                        (holiday._get_number_of_days(holiday.date_from, holiday.date_to, holiday.employee_id.id)[
                            'days']) / 2
                else:
                    holiday.number_of_days = holiday.number_of_days = \
                        holiday._get_number_of_days(holiday.date_from, holiday.date_to, holiday.employee_id.id)[
                            'days']

    def action_send_email_notifier(self, temp):
        send_notification = "Vous avec une nouvelle demande de congé"
        # template = self.env.ref("demande.email_template_conge")
        template = self.env.ref("vacances.%s" % temp)
        if template:
            self.env["mail.template"].browse(template.id).sudo().send_mail(
                self.id, force_send=True
            )
            self.env["mail.mail"].sudo().process_email_queue()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'message': send_notification,
                    'next': {
                        'type': 'ir.actions.act_window_close'
                    },
                }
            }

    def get_url(self, id):
        # url = f'http://95.111.239.216:1010/web#id={id}&cids=1&model=hr.leave&view_type=form'
        base_url = self.env["ir.config_parameter"].get_param("web.base.url")
        url = f'{base_url}/web#id={id}&cids=1&model=hr.leave&view_type=form'
        return url

    def get_email(self, param):
        if param.employee_parent_id.parent_id.user_id.employee_parent_id.parent_id.user_id.employee_parent_id.parent_id.user_id.work_email:
            return param.employee_parent_id.parent_id.user_id.work_email
        else:
            return param.employee_parent_id.parent_id.user_id.work_email

    def get_manager(self, groupe):
        drh = []
        users = self.env['res.users'].sudo().search([])
        for user in users:
            if user.has_group(groupe):
                employe = self.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)
                if employe:
                    drh.append(employe.work_email)
        return ';'.join(drh)

    def get_sg(self):
        return self.get_manager('vacances.group_conge_sg')

    def get_drh(self):
        return self.get_manager('vacances.group_conge_drh')

    def get_ag(self):
        return self.get_manager('vacances.group_conge_AG')

    def get_chefDepartment(self):
        current_employee = self.env.user.employee_id.id
        user = self.env['res.users'].sudo().search([('employee_id', '=', current_employee)], limit=1)
        # for user in users:
        if user.has_group('vacances.group_service'):
            return user.employee_parent_id.parent_id.user_id.work_email
        else:
            return user.employee_parent_id.work_email

    # def get_directeur(self):
    #     current_employee = self.env.user.employee_id.id
    #     user = self.env['res.users'].sudo().search([('employee_id', '=', current_employee)], limit=1)
    #     # for user in users:
    #     if user.has_group('vacances.group_service'):
    #         return user.employee_parent_id.parent_id.user_id.work_email
    #     else:
    #         return user.employee_parent_id.parent_id.user_id.work_email

    def get_directeur(self):
        # Récupération de l'employé courant
        employee = self.env.user.employee_id
        if not employee:
            return False  # Pas d'employé relié à l'utilisateur

        # Vérifier si l'utilisateur est dans un service ou un département
        if self.env.user.has_group('vacances.group_service'):
            # L'utilisateur est dans un service
            # -> On doit remonter 3 fois (service -> département -> direction)
            # On vérifie que les parents existent à chaque étape pour éviter les erreurs
            directeur = (
                    employee.parent_id
                    and employee.parent_id.parent_id
                    and employee.parent_id.parent_id.parent_id
            )
        else:
            # L'utilisateur est dans un département
            # -> On remonte 2 fois (département -> direction)
            directeur = (
                    employee.parent_id
                    and employee.parent_id.parent_id
            )

        # On renvoie l'email s'il existe
        return directeur.user_id.work_email if directeur and directeur.user_id else False

    @api.depends_context('uid')
    def _compute_description(self):
        self.check_access_rights('read')
        self.check_access_rule('read')

        is_officer = self.user_has_groups('hr_holidays.group_hr_holidays_user')

        for leave in self:
            # if is_officer or leave.user_id == self.env.user or leave.employee_id.leave_manager_id == self.env.user:
            #     leave.name = leave.sudo().private_name
            # else:
            leave.name = leave.sudo().private_name

    def get_agent_on_leave(self):
        list_leaves = []
        date_today = datetime.today()
        leaves = self.env['hr.leave'].sudo().search([])
        for leave in leaves:
            if leave.date_from <= date_today <= leave.date_to:
                list_leaves.append(leave)
        return list_leaves

    def report_print(self):
        return self.env.ref("vacances.report_conge_leave").report_action(self)

    def _check_approval_update(self, state):
        """ Check if target state is achievable. """
        if self.env.is_superuser():
            return

        current_employee = self.env.user.employee_id
        is_officer = self.env.user.has_group('hr_holidays.group_hr_holidays_user')
        is_manager = self.env.user.has_group('hr_holidays.group_hr_holidays_manager')

        for holiday in self:
            val_type = holiday.validation_type

            if not is_manager and state != 'confirm':
                if state == 'draft':
                    if holiday.state == 'refuse':
                        raise UserError(_('Only a Time Off Manager can reset a refused leave.'))
                    if holiday.date_from and holiday.date_from.date() <= fields.Date.today():
                        raise UserError(_('Only a Time Off Manager can reset a started leave.'))
                    if holiday.employee_id != current_employee:
                        raise UserError(_('Only a Time Off Manager can reset other people leaves.'))
                else:
                    if val_type == 'no_validation' and current_employee == holiday.employee_id:
                        continue
                    # use ir.rule based first access check: department, members, ... (see security.xml)
                    holiday.check_access_rule('write')

                    # This handles states validate1 validate and refuse
                    # if holiday.employee_id == current_employee:
                    #     raise UserError(_('Only a Time Off Manager can approve/refuse its own requests.'))

                    if (state == 'directeur' and val_type == 'both') and holiday.holiday_type == 'employee':
                        if not is_officer and self.env.user != holiday.employee_id.leave_manager_id:
                            raise UserError(_('You must be either %s\'s manager or Time off Manager to approve this '
                                              'leave') % (holiday.employee_id.name))

                    if (state == 'validate' and val_type == 'manager') and self.env.user != (
                            holiday.employee_id | holiday.sudo().employee_ids).leave_manager_id:
                        if holiday.employee_id:
                            employees = holiday.employee_id
                        else:
                            employees = ', '.join(
                                holiday.employee_ids.filtered(lambda e: e.leave_manager_id != self.env.user).mapped(
                                    'name'))
                        raise UserError(_('You must be %s\'s Manager to approve this leave', employees))

                    if not is_officer and (
                            state == 'validate' and val_type == 'hr') and holiday.holiday_type == 'employee':
                        raise UserError(_('You must either be a Time off Officer or Time off Manager to approve this '
                                          'leave'))
