# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2017-01-12 11:40
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('serverapi', '0034_auto_20170112_0904'),
    ]

    operations = [
        migrations.AlterField(
            model_name='meetingsummary',
            name='comment_date',
            field=models.CharField(blank=True, max_length=125, null=True),
        ),
    ]
