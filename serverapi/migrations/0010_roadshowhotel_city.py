# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('serverapi', '0009_auto_20161006_1629'),
    ]

    operations = [
        migrations.AddField(
            model_name='roadshowhotel',
            name='city',
            field=models.CharField(max_length=250, null=True, blank=True),
        ),
    ]
