from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckanext.password_policy.views as views
import ckan.lib.navl.dictization_functions as df
import ckanext.password_policy.helpers as h
from six import string_types
from ckan.common import _, config

Missing = df.Missing
missing = df.missing


def user_custom_password_validator(key, data, errors, context):
    value = data[key]
    valid_pass = h.custom_password_check(value)
    password_length = config.get('ckanext.password_policy.password_length')

    if isinstance(value, Missing):
        pass
    elif not isinstance(value, string_types):
        errors[('password',)].append(_('Passwords must be strings'))
    elif value == '':
        pass
    elif not valid_pass['password_ok']:
        errors[('password',)].append(_('Your password must be {} characters or '
                                       'longer and contain uppercase, lowercase, '
                                       'digit and special character'.format(password_length)))


class PasswordPolicyPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IValidators)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.IAuthenticator, inherit=True)
    plugins.implements(plugins.ITemplateHelpers)



    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic',
            'password_policy')

    def get_validators(self):
        return {'user_custom_password_validator': user_custom_password_validator}

    def get_blueprint(self):
        return views.get_blueprints()


    def get_helpers(self):
        return {'lockout_time': h.lockout_time}

