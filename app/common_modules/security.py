# -*- coding: utf-8 -*-
#------------------------------------------------------------
# Name:        security
# Author:      alexey.sychov@gameloft.com
# Created:     08-09-2016
# Description: Security decorators
#------------------------------------------------------------

from django.shortcuts import render

from common_modules import amsettings


def admin_use_only(func):
    """ Stop users without access to admin panel.
    """
    def func2(request, *args, **kargs):
        admin_name = request.session.get('gameloft_user_name', '').lower()
        if admin_name in amsettings.ADMINS:
            return func(request, *args, **kargs)
        else:
            return render(request, 'common_modules/error.html',
                       {'msg':'You are not allowed to use admin tool.',
                        'text':'ask AM producer to add you into admins list.'})
    func2.__name__ = func.__name__
    func2.__doc__ = func.__doc__
    return func2


def limited_access(application_name):
    """ Stop users without access to application.
    """
    def inner_decor(func):
        """
        """
        def func2(request, *args, **kargs):
            if not access_granted(request, application_name):
                return render(request, 'common_modules/error.html',
                        {'msg':'You are not allowed to use this tool.',
                         'text':'ask AM produser to add you into users list.'})
            else:
                return func(request, *args, **kargs)

        func2.__name__ = func.__name__
        func2.__doc__ = func.__doc__
        return func2

    return inner_decor


def access_granted(request, application_name, config=None):
    """Verify, is access granted to this app for current user.
    """
    if not config:
        config = amsettings.get_access_config()
    user_name = request.session.get('gameloft_user_name', '').lower()

    if user_name == 'desktop@tool':
        return True
    if ((config[application_name]['limited_access']) and
              (user_name not in config[application_name]['credentials_list'])):
        return False
    else:
        return True


def is_admin(request):
    """Verify, is access granted to use admin panel.
    """
    user_name = request.session.get('gameloft_user_name', '').lower()
    if user_name in amsettings.ADMINS:
        return True
    else:
        return False