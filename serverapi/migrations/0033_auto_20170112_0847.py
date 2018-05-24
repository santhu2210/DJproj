# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2017-01-12 08:47
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('serverapi', '0032_meeting_company_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='roadshowflight',
            name='state',
            field=models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AddField(
            model_name='roadshowhotel',
            name='state',
            field=models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AddField(
            model_name='roadshowrental',
            name='confirmation_code',
            field=models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AddField(
            model_name='roadshowrental',
            name='state',
            field=models.CharField(blank=True, max_length=250, null=True),
        ),
    ]