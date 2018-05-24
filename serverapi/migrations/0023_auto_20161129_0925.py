# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('serverapi', '0022_auto_20161128_1314'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExpenseDocument',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('docfile', models.FileField(null=True, upload_to='documents/%Y/%m/%d', blank=True)),
            ],
        ),
        migrations.RemoveField(
            model_name='roadshowexpense',
            name='docfile',
        ),
        migrations.AddField(
            model_name='expensedocument',
            name='expense',
            field=models.ForeignKey(related_name='expense_documents', blank=True, to='serverapi.RoadshowExpense', null=True),
        ),
    ]
