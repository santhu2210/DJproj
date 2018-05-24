# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('serverapi', '0018_roadshowhotel_pincode'),
    ]

    operations = [
        migrations.AddField(
            model_name='roadshowflight',
            name='to_date',
            field=models.DateField(default=datetime.datetime(2016, 11, 23, 15, 11, 28, 286690, tzinfo=utc)),
            preserve_default=False,
        ),
    ]
