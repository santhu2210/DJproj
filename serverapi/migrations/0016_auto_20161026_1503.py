# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('serverapi', '0015_auto_20161026_1443'),
    ]

    operations = [
        migrations.AlterField(
            model_name='roadshowexpense',
            name='docfile',
            field=models.FileField(null=True, upload_to='documents/%Y/%m/%d', blank=True),
        ),
    ]
