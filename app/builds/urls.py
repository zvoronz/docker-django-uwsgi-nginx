from django.conf.urls import url

import views

urlpatterns = [
    url(r'^$', views.index, name='builds'),
    url(r'upload/$', views.simple_upload, name='upload'),
    url(r'^delete/(?P<version>.+)', views.delete, name='delete'),
    url(r'^(?P<version>.+)/$', views.build, name='build')
]
