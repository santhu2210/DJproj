# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('serverapi', '0010_roadshowhotel_city'),
    ]

    operations = [
        migrations.AddField(
            model_name='roadshowhotel',
            name='distance_next',
            field=models.IntegerField(default=0, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='roadshowhotel',
            name='distance_prev',
            field=models.IntegerField(default=0, null=True, blank=True),
        ),
    ]
