# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-09-01 08:15
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('serverapi', '0003_auto_20160830_1117'),
    ]

    operations = [
        migrations.CreateModel(
            name='MeetingUser',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('meeting_mode_other', models.CharField(blank=True, max_length=250, null=True)),
            ],
        ),
        migrations.RemoveField(
            model_name='meeting',
            name='meeting_mode',
        ),
        migrations.RemoveField(
            model_name='meeting',
            name='meeting_mode_other',
        ),
        migrations.RemoveField(
            model_name='meeting',
            name='users',
        ),
        migrations.AddField(
            model_name='meetinguser',
            name='meeting',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='serverapi.Meeting'),
        ),
        migrations.AddField(
            model_name='meetinguser',
            name='meeting_mode',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='serverapi.MeetingMode'),
        ),
        migrations.AddField(
            model_name='meetinguser',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]
