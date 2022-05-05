from django.shortcuts import render, HttpResponseRedirect
from django.contrib.auth import authenticate, login, logout
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required

from forms import Authorize
from common_modules import fedClass
from common_modules.security import access_granted, is_admin
from common_modules.amsettings import APPLICATIONS, get_access_config

import urllib2

# Create your views here.


def index(request):
    """ Authorize.
    """
    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse('choose'))
    if request.method == 'POST':
        form = Authorize(request.POST)
        if form.is_valid():
            gameloft_login = form.cleaned_data['login']
            isLoggined, refresh_token = fedClass.fedLogin(gameloft_login, form.cleaned_data['password'], version='0.0.9')
            if isLoggined:
                user = authenticate(username='generic_user',password='general_')
                login(request, user)
                request.session['gameloft_user_name'] = gameloft_login
                request.session['refresh_token'] = refresh_token
                if form.cleaned_data['redirect']:
                    return HttpResponseRedirect(form.cleaned_data['redirect'])
                else:
                    return HttpResponseRedirect('/choose/')
            else:
                return render(request, 'selector/index.html', {'form':form.as_p,
                                                            'request':request})
        else:
            return render(request, 'selector/index.html', {'form':form.as_p,
                                                            'request':request})
    else:
        form = Authorize()
        return render(request, 'selector/index.html', {'form':form.as_p,
                                                            'request':request})

@login_required
def choose(request):
    """ Choose one of the tools.
    """
    config = get_access_config()
    allowed = [app for app in config if access_granted(request, app, config)]
    return render(request, 'selector/choose.html',
                                                {'request':request,
                                                 'allowed':allowed,
                                                 'is_admin':is_admin(request)})

@login_required
def choose_env(request):
    """ Choose one of the environment for TLE tool.
    """
    if request.session.get('refresh_token') is None:
        logout(request)
        form = Authorize()
        return render(request, 'selector/index.html', {'form': form.as_p,
                                                       'request': request})
    else:
        fed = fedClass.Federation('0.0.9')
        try:
            result = fed.askJanusForRefreshToken(request.session['refresh_token'])
            token = result['access_token']
            request.session['refresh_token'] = result['refresh_token']
        except urllib2.HTTPError as err:
            if err.code == 401:
                logout(request)
                form = Authorize()
                return render(request, 'selector/index.html', {'form': form.as_p,
                                                       'request': request})
            else:
                raise err

        return render(request, 'selector/choose_env.html',
                      {
                        'token':token
                      })