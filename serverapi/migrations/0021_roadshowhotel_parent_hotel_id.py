# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('serverapi', '0020_category_color'),
    ]

    operations = [
        migrations.AddField(
            model_name='roadshowhotel',
            name='parent_hotel_id',
            field=models.IntegerField(default=0),
        ),
    ]
