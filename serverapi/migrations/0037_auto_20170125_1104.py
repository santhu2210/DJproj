# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2017-01-25 11:04
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('serverapi', '0036_auto_20170120_1417'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='designation',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
