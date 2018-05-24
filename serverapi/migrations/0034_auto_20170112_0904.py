# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2017-01-12 09:04
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('serverapi', '0033_auto_20170112_0847'),
    ]

    operations = [
        migrations.AddField(
            model_name='roadshowflight',
            name='destination_flight_code',
            field=models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AddField(
            model_name='roadshowflight',
            name='source_flight_code',
            field=models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AddField(
            model_name='roadshowrental',
            name='is_prepaid',
            field=models.NullBooleanField(default=None),
        ),
    ]