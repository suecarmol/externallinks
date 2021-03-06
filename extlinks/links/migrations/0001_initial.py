# Generated by Django 2.2 on 2019-05-20 14:01

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("organisations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="URLPattern",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("url", models.CharField(max_length=60)),
                (
                    "collection",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="url",
                        to="organisations.Collection",
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "URL patterns",
                "verbose_name": "URL pattern",
            },
        ),
        migrations.CreateModel(
            name="LinkSearchTotal",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("date", models.DateField(auto_now_add=True)),
                ("total", models.PositiveIntegerField()),
                (
                    "url",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="links.URLPattern",
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "LinkSearch totals",
                "verbose_name": "LinkSearch total",
            },
        ),
        migrations.CreateModel(
            name="LinkEvent",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("link", models.CharField(max_length=2083)),
                ("timestamp", models.DateTimeField()),
                ("domain", models.CharField(max_length=32)),
                ("username", models.CharField(max_length=255)),
                ("rev_id", models.PositiveIntegerField(null=True)),
                ("user_id", models.PositiveIntegerField()),
                ("page_title", models.CharField(max_length=255)),
                ("page_namespace", models.IntegerField()),
                ("event_id", models.CharField(max_length=36)),
                ("change", models.IntegerField(choices=[(0, "Removed"), (1, "Added")])),
                ("on_user_list", models.BooleanField(default=False)),
                (
                    "url",
                    models.ManyToManyField(
                        related_name="linkevent", to="links.URLPattern"
                    ),
                ),
            ],
            options={
                "get_latest_by": "timestamp",
            },
        ),
    ]
