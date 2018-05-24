# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('serverapi', '0007_auto_20160908_0927'),
    ]

    operations = [
        migrations.AddField(
            model_name='roadshowexpense',
            name='category',
            field=models.CharField(max_length=150, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='roadshowexpense',
            name='currency_type',
            field=models.CharField(max_length=50, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='roadshowexpense',
            name='expense_date',
            field=models.DateField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='roadshowexpense',
            name='expense_notes',
            field=models.CharField(max_length=150, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='roadshowexpense',
            name='final_amount',
            field=models.CharField(max_length=50, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='roadshowexpense',
            name='minus_personal',
            field=models.CharField(max_length=50, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='roadshowexpense',
            name='payment_method',
            field=models.CharField(max_length=150, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='meetinguser',
            name='meeting',
            field=models.ForeignKey(related_name='meetingusers', to='serverapi.Meeting'),
        ),
    ]
