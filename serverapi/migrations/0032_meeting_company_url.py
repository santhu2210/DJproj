# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2017-01-10 11:38
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('serverapi', '0031_userprofile_designation'),
    ]

    operations = [
        migrations.AddField(
            model_name='meeting',
            name='company_url',
            field=models.CharField(blank=True, max_length=250, null=True),
        ),
    ]
