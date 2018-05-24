# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('serverapi', '0008_auto_20161006_1311'),
    ]

    operations = [
        migrations.AlterField(
            model_name='roadshowexpense',
            name='created_by',
            field=models.ForeignKey(related_name='userexpenses', blank=True, to=settings.AUTH_USER_MODEL, null=True),
        ),
        migrations.AlterField(
            model_name='roadshowexpense',
            name='expense_title',
            field=models.CharField(max_length=150, null=True, blank=True),
        ),
    ]
