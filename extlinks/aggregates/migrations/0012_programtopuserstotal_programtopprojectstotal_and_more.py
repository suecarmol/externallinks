# Generated by Django 4.2.20 on 2025-03-26 18:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('organisations', '0008_alter_collection_id_alter_organisation_id_and_more'),
        ('programs', '0003_alter_program_id'),
        ('aggregates', '0011_aggregate_composite_indexes'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProgramTopUsersTotal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(max_length=235)),
                ('full_date', models.DateField()),
                ('on_user_list', models.BooleanField(default=False)),
                ('total_links_added', models.PositiveIntegerField()),
                ('total_links_removed', models.PositiveIntegerField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('program', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='programs.program')),
            ],
            options={
                'indexes': [models.Index(fields=['program_id', 'full_date', 'username'], name='aggregates__program_885240_idx'), models.Index(fields=['program_id', 'username'], name='aggregates__program_5e05d9_idx')],
            },
        ),
        migrations.CreateModel(
            name='ProgramTopProjectsTotal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('project_name', models.CharField(max_length=32)),
                ('full_date', models.DateField()),
                ('on_user_list', models.BooleanField(default=False)),
                ('total_links_added', models.PositiveIntegerField()),
                ('total_links_removed', models.PositiveIntegerField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('program', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='programs.program')),
            ],
            options={
                'indexes': [models.Index(fields=['program_id', 'full_date', 'project_name'], name='aggregates__program_ef06a4_idx'), models.Index(fields=['program_id', 'project_name'], name='aggregates__program_84ed52_idx')],
            },
        ),
        migrations.CreateModel(
            name='ProgramTopOrganisationsTotal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('full_date', models.DateField()),
                ('on_user_list', models.BooleanField(default=False)),
                ('total_links_added', models.PositiveIntegerField()),
                ('total_links_removed', models.PositiveIntegerField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('organisation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='organisations.organisation')),
                ('program', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='programs.program')),
            ],
            options={
                'indexes': [models.Index(fields=['program_id', 'full_date', 'organisation_id'], name='aggregates__program_0db533_idx'), models.Index(fields=['program_id', 'organisation_id'], name='aggregates__program_fae7db_idx')],
            },
        ),
    ]
