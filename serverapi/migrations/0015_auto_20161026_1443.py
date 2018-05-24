# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('serverapi', '0014_auto_20161025_1241'),
    ]

    operations = [
        migrations.AddField(
            model_name='roadshowexpense',
            name='docfile',
            field=models.FileField(null=True, upload_to='documents/%Y/%m/%d'),
        ),
        migrations.AlterField(
            model_name='roadshowexpense',
            name='category',
            field=models.ForeignKey(related_name='expense_categories', default='', to='serverapi.Category'),
        ),
        migrations.AlterField(
            model_name='roadshowexpense',
            name='company',
            field=models.ForeignKey(related_name='company_expense', default='', to='serverapi.Company'),
        ),
    ]
