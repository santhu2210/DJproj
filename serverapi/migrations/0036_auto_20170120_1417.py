# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2017-01-20 14:17
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('serverapi', '0035_auto_20170112_1140'),
    ]

    operations = [
        migrations.RenameField(
            model_name='roadshowrental',
            old_name='state',
            new_name='from_state',
        ),
        migrations.AddField(
            model_name='roadshowrental',
            name='to_state',
            field=models.CharField(blank=True, max_length=250, null=True),
        ),
    ]
