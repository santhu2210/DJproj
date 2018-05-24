# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('serverapi', '0012_auto_20161018_1248'),
    ]

    operations = [
        migrations.AddField(
            model_name='meetinguser',
            name='distance',
            field=models.IntegerField(default=0, null=True, blank=True),
        ),
    ]
