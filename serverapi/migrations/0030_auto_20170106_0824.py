# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2017-01-06 08:24
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('serverapi', '0029_userprofile'),
    ]

    operations = [
        migrations.AddField(
            model_name='meeting',
            name='company_twitter_url',
            field=models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AddField(
            model_name='meeting',
            name='user_linkedin_url',
            field=models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AddField(
            model_name='meeting',
            name='user_twitter_url',
            field=models.CharField(blank=True, max_length=250, null=True),
        ),
    ]
