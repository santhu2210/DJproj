# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('serverapi', '0016_auto_20161026_1503'),
    ]

    operations = [
        migrations.RenameField(
            model_name='meetinguser',
            old_name='time_to_travel_min',
            new_name='duration',
        ),
    ]
