# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('serverapi', '0013_meetinguser_distance'),
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50, null=True, blank=True)),
                ('company', models.ForeignKey(to='serverapi.Company')),
            ],
        ),
        migrations.AddField(
            model_name='roadshowexpense',
            name='company',
            field=models.ForeignKey(related_name='company_expense', default='', to='serverapi.Company'),
            preserve_default=False,
        ),
    ]
