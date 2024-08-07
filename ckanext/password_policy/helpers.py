from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
from builtins import int
from future import standard_library
standard_library.install_aliases()
import re
import ckan.plugins.toolkit as toolkit
from ckan.authz import is_sysadmin
from ckan.common import _
from ckan.lib.redis import connect_to_redis
from ckan.common import config, g


def increment_user_login_count(username):
    redis_conn = connect_to_redis()
    user_cached = redis_conn.get(username)
    if user_cached is None:
        require_sysadmin = toolkit.asbool(
            config.get("ckanext.password_policy.require_sysadmin_unlock", False)
        )
        expiry = None if require_sysadmin else \
            config.get('ckanext.password_policy.user_locked_time', 600)
        # user will be cached in redis with count 1
        redis_conn.set(username, 1, ex=expiry)
    else:
        # user allready cached in redis, incrementing login count
        redis_conn.incr(username)

    failed_logins_count = int(redis_conn.get(username))

    return failed_logins_count


def user_locked_out(username):
    redis_conn = connect_to_redis()
    user_cached = redis_conn.get(username)

    if user_cached is None:
        return False

    return int(user_cached) >= \
        int(config.get('ckanext.password_policy.failed_logins', 3))


def clear_login_count(username):

    redis_conn = connect_to_redis()
    redis_conn.delete(username)
    return None


def get_password_length(username=None):
    user = username or g.user
    if is_sysadmin(user):
        return int(
            config.get('ckanext.password_policy.password_length_sysadmin', 18)
        )
    return int(
        config.get('ckanext.password_policy.password_length', 10)
    )


def requirements_message(password_length=None, username=None):
    if not password_length:
        password_length = get_password_length(username)

    return _('Your password must be {} characters or '
             'longer and contain uppercase, lowercase, digit, '
             'and special character ( !#$%&\'()*+,-./[\\]^_`{{|}}~@" ). '
             'Your password may not contain your username '
             'or part of your full name.'.format(password_length))


def custom_password_check(password, username="", fullname=""):
    """
    Verify the strength of 'password'
    Returns a dict indicating the wrong criteria
    A password is considered strong if:
        length is at least the configured minimum length
        1 digit or more
        1 symbol or more
        1 uppercase letter or more
        1 lowercase letter or more
    """
    if not username and hasattr(g, "user") and g.user:
        username = g.user

    if not fullname and hasattr(g, "userobj") and g.userobj:
        fullname = g.userobj.fullname

    password_length = get_password_length(username)

    # calculating the length
    length_error = len(password) < password_length

    # searching for digits
    digit_error = re.search(r"\d", password) is None

    # searching for uppercase
    uppercase_error = re.search(r"[A-Z]", password) is None

    # searching for lowercase
    lowercase_error = re.search(r"[a-z]", password) is None

    # searching for symbols
    symbol_error = re.search(r"[ !#$%&'()*+,-./[\\\]^_`{|}~@"+r'"]', password) is None

    # searching for username or fullname
    username_error = username and re.search(username.lower(),
                                            password.lower()) is not None

    fullname_error = False
    if fullname:
        for name_part in fullname.lower().split(" "):
            if re.search(name_part, password.lower()) is not None:
                fullname_error = True
                break

    # overall result
    password_ok = not (
            length_error
            or digit_error
            or uppercase_error
            or lowercase_error
            or symbol_error
            or username_error
            or fullname_error
    )

    return {
        'password_ok': password_ok,
        'length_error': length_error,
        'digit_error': digit_error,
        'uppercase_error': uppercase_error,
        'lowercase_error': lowercase_error,
        'symbol_error': symbol_error,
        'username_error': username_error,
        'fullname_error': fullname_error,
    }


def lockout_message():
    require_sysadmin = toolkit.asbool(
        config.get("ckanext.password_policy.require_sysadmin_unlock", False)
    )
    failed_logins = config.get('ckanext.password_policy.failed_logins')

    if require_sysadmin:
        return "You failed {} attempts to login and you have been locked out. " \
               "Contact a sysadmin to re-enable you to login.".format(
                    failed_logins)

    lockout = config.get('ckanext.password_policy.user_locked_time')
    time_to_int = int(lockout)

    if time_to_int >= 60:
        time_in_minutes = time_to_int//60
        alert = "You failed {} attempts to login and you have been locked out " \
                "for {} minutes. Try again later or contact a sysadmin.".format(
                    failed_logins, time_in_minutes)
        return alert
    else:
        alert = "You failed {} attempts to login and you have been locked out " \
                "for {} seconds. Try again later or contact a sysadmin.".format(
                    failed_logins, time_to_int)
        return alert
