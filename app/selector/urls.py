from django.conf.urls import url

import views

urlpatterns = [
    url(r'^index', views.index, name='index'),
    url(r'^choose', views.choose, name='choose'),
    url(r'^$', views.index, name='index'),
]
