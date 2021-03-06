# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2017-01-30 10:44
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('serverapi', '0037_auto_20170125_1104'),
    ]

    operations = [
        migrations.CreateModel(
            name='CompanyLinkedIn',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=250, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('specialities', models.TextField(blank=True, null=True)),
                ('founded', models.CharField(blank=True, max_length=10, null=True)),
                ('street', models.CharField(blank=True, max_length=250, null=True)),
                ('city', models.CharField(blank=True, max_length=50, null=True)),
                ('state', models.CharField(blank=True, max_length=50, null=True)),
                ('zipcode', models.CharField(blank=True, max_length=10, null=True)),
                ('country', models.CharField(blank=True, max_length=50, null=True)),
                ('industry', models.CharField(blank=True, max_length=150, null=True)),
                ('website', models.CharField(blank=True, max_length=100, null=True)),
                ('follower_count', models.CharField(blank=True, max_length=10, null=True)),
                ('company_type', models.CharField(blank=True, max_length=150, null=True)),
                ('profile_url', models.CharField(blank=True, max_length=250, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='CompanyTwitter',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=250, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('follower_count', models.CharField(blank=True, max_length=10, null=True)),
                ('statuses', models.CharField(blank=True, max_length=150, null=True)),
                ('location', models.CharField(blank=True, max_length=250, null=True)),
                ('website', models.CharField(blank=True, max_length=150, null=True)),
                ('profile_pic', models.CharField(blank=True, max_length=250, null=True)),
                ('profile_url', models.CharField(blank=True, max_length=250, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='MeetingCompanyLinkedIn',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('company_linkedin', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='serverapi.CompanyLinkedIn')),
                ('meeting', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='serverapi.Meeting')),
            ],
        ),
        migrations.CreateModel(
            name='MeetingCompanyTwitter',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('company_twitter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='serverapi.CompanyTwitter')),
                ('meeting', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='serverapi.Meeting')),
            ],
        ),
    ]
