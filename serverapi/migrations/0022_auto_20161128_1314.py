# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('serverapi', '0021_roadshowhotel_parent_hotel_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='meeting',
            name='notes',
            field=models.TextField(null=True, blank=True),
        ),
    ]
