# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2017-01-10 11:23
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('serverapi', '0030_auto_20170106_0824'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='designation',
            field=models.CharField(blank=True, max_length=14, null=True),
        ),
    ]
