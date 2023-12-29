# Generated by Django 4.2.8 on 2023-12-29 15:58

import uuid

import django.db.models.deletion
from django.db import migrations, models

import authentik.core.models
import authentik.lib.utils.time


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("authentik_policies", "0011_policybinding_failure_result_and_more"),
        ("authentik_core", "0032_group_roles"),
    ]

    operations = [
        migrations.CreateModel(
            name="RACPropertyMapping",
            fields=[
                (
                    "propertymapping_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="authentik_core.propertymapping",
                    ),
                ),
                ("static_settings", models.JSONField(default=dict)),
            ],
            options={
                "verbose_name": "RAC Property Mapping",
                "verbose_name_plural": "RAC Property Mappings",
            },
            bases=("authentik_core.propertymapping",),
        ),
        migrations.CreateModel(
            name="RACProvider",
            fields=[
                (
                    "provider_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="authentik_core.provider",
                    ),
                ),
                ("settings", models.JSONField(default=dict)),
                (
                    "auth_mode",
                    models.TextField(
                        choices=[("static", "Static"), ("prompt", "Prompt")], default="prompt"
                    ),
                ),
                (
                    "connection_expiry",
                    models.TextField(
                        default="hours=8",
                        help_text="Determines how long a session lasts. Default of 0 means that the sessions lasts until the browser is closed. (Format: hours=-1;minutes=-2;seconds=-3)",
                        validators=[authentik.lib.utils.time.timedelta_string_validator],
                    ),
                ),
            ],
            options={
                "verbose_name": "RAC Provider",
                "verbose_name_plural": "RAC Providers",
            },
            bases=("authentik_core.provider",),
        ),
        migrations.CreateModel(
            name="Endpoint",
            fields=[
                (
                    "policybindingmodel_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="authentik_policies.policybindingmodel",
                    ),
                ),
                ("name", models.TextField()),
                ("host", models.TextField()),
                (
                    "protocol",
                    models.TextField(choices=[("rdp", "Rdp"), ("vnc", "Vnc"), ("ssh", "Ssh")]),
                ),
                ("settings", models.JSONField(default=dict)),
                (
                    "auth_mode",
                    models.TextField(choices=[("static", "Static"), ("prompt", "Prompt")]),
                ),
                (
                    "property_mappings",
                    models.ManyToManyField(
                        blank=True, default=None, to="authentik_core.propertymapping"
                    ),
                ),
                (
                    "provider",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="authentik_providers_rac.racprovider",
                    ),
                ),
            ],
            options={
                "verbose_name": "RAC Endpoint",
                "verbose_name_plural": "RAC Endpoints",
            },
            bases=("authentik_policies.policybindingmodel", models.Model),
        ),
        migrations.CreateModel(
            name="ConnectionToken",
            fields=[
                (
                    "expires",
                    models.DateTimeField(default=authentik.core.models.default_token_duration),
                ),
                ("expiring", models.BooleanField(default=True)),
                (
                    "connection_token_uuid",
                    models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False),
                ),
                ("token", models.TextField(default=authentik.core.models.default_token_key)),
                ("settings", models.JSONField(default=dict)),
                (
                    "endpoint",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="authentik_providers_rac.endpoint",
                    ),
                ),
                (
                    "provider",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="authentik_providers_rac.racprovider",
                    ),
                ),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="authentik_core.authenticatedsession",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
