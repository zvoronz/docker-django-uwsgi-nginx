from django.conf.urls import url

import views

urlpatterns = [
    url(r'^$', views.admin_panel, name='admin_panel'),
    url(r'^save/settings', views.save_settings, name='save_settings'),
]
