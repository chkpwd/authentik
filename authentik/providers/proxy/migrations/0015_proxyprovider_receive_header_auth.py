# Generated by Django 4.1.5 on 2023-01-17 10:28

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("authentik_providers_proxy", "0001_squashed_0014_proxy_v2"),
    ]

    operations = [
        migrations.AddField(
            model_name="proxyprovider",
            name="intercept_header_auth",
            field=models.BooleanField(
                default=True,
                help_text=(
                    "When enabled, this provider will intercept the authorization header and"
                    " authenticate requests based on its value."
                ),
            ),
        ),
    ]