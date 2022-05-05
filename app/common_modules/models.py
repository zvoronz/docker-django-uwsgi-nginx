
from __future__ import unicode_literals

from django.db import models


class Access(models.Model):
    """Every custom application must have this access config.
    If limited_access is True, only people in json_credentials_list
    have access to this app.
    """
    application = models.CharField(max_length=30)
    limited_access = models.BooleanField(default=False)
    credentials_list = models.TextField()

    def __unicode__(self):
        return '"%s"' % (self.application)

    @staticmethod
    def init_applications(application_list):
        apps_names_base = [app.application for app
                                         in Access.objects.only("application")]
        for app_name in application_list:
            if app_name not in apps_names_base:
                Access(application=app_name).save()

    @staticmethod
    def set_access_rules(access_list):
        for q in access_list:
            application = q['application']
            instance_list = Access.objects.filter(application=application)
            if instance_list:
                instance = instance_list[0]
            else:
                instance = Access(application=application)
            instance.limited_access = q['limited_access']
            instance.credentials_list = q['credentials_list']
            instance.save()

    @staticmethod
    def get_access_config(applications):
        access_config = {}
        for application in Access.objects.filter(application__in=applications):
            app_name = application.application
            access_config[app_name] = {}
            access_config[app_name]['limited_access'
                                                 ] = application.limited_access
            raw_list = application.credentials_list.split('\n')
            stripped_list = [q.strip() for q in raw_list]
            access_config[app_name]['credentials_list'] = stripped_list
        return access_config
        
