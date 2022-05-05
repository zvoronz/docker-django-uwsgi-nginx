from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseBadRequest

import json

from common_modules import amsettings
from models import Access
from security import admin_use_only

# Create your views here.

@login_required
@admin_use_only
def admin_panel(request):
    """Admin panel for configuration settings.
    """
    # make table of 3 cols
    access_list, temp = [], []
    for q in xrange(len(amsettings.APPLICATIONS)):
        temp.append(Access.objects.get(application=amsettings.APPLICATIONS[q]))
        if len(temp) >= 3:
            access_list.append(temp)
            temp = []
    if temp:
        access_list.append(temp)

    return render(request, 'common_modules/index.html',
                                      {'access_list':access_list})


@login_required
@admin_use_only
def save_settings(request):
    """Save G4 settings
    """
    if request.method <> 'POST':
        return render(request, 'common_modules/error.html',
                                            {'msg':'Incorrect method',
                                             'text':'only POST method allowed'})
    try:
        json_obj = request.POST['json_obj']
    except:
        return HttpResponseBadRequest('No JSON received')

    options = json.loads(json_obj)
    if ('access' not in options):
        return HttpResponseBadRequest('Invalid JSON')

    Access.set_access_rules(options['access'])

    reload(amsettings)
    return HttpResponse('Ok')

