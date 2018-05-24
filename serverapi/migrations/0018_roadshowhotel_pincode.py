# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('serverapi', '0017_auto_20161114_1111'),
    ]

    operations = [
        migrations.AddField(
            model_name='roadshowhotel',
            name='pincode',
            field=models.CharField(max_length=250, null=True, blank=True),
        ),
    ]
