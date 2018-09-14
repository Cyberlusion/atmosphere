# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-05-17 16:34
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def move_projects_to_project(apps, schema_editor):
    Project = apps.get_model('core', 'Project')
    for project in Project.objects.all():
        for instance in project.instances.all():
            instance.project = project
            instance.save()
        for volume in project.volumes.all():
            volume.project = project
            volume.save()
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0088_set_project_leaders_and_authors'),
    ]

    operations = [
        migrations.AlterField(
            model_name='project',
            name='created_by',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='projects',
                to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.RunPython(
            move_projects_to_project, reverse_code=migrations.RunPython.noop
        ),
        migrations.RemoveField(
            model_name='project',
            name='instances',
        ),
        migrations.RemoveField(
            model_name='project',
            name='volumes',
        ),
    ]
