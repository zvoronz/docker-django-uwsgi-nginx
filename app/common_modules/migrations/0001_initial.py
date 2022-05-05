# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Access',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('application', models.CharField(max_length=30)),
                ('limited_access', models.BooleanField(default=False)),
                ('credentials_list', models.TextField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
