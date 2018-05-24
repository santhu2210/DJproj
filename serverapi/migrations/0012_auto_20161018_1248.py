# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('serverapi', '0011_auto_20161011_1010'),
    ]

    operations = [
        migrations.AddField(
            model_name='meetinguser',
            name='date_of_travel',
            field=models.CharField(max_length=250, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='meetinguser',
            name='from_address',
            field=models.CharField(max_length=250, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='meetinguser',
            name='from_city',
            field=models.CharField(max_length=250, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='meetinguser',
            name='time_to_travel_min',
            field=models.CharField(max_length=250, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='meetinguser',
            name='to_address',
            field=models.CharField(max_length=250, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='meetinguser',
            name='to_city',
            field=models.CharField(max_length=250, null=True, blank=True),
        ),
    ]
