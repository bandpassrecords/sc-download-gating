from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("gates", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="gatedtrack",
            name="soundcloud_artist_urn",
            field=models.CharField(blank=True, db_index=True, max_length=128),
        ),
        migrations.AddField(
            model_name="gatedtrack",
            name="soundcloud_artist_username",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="gatedtrack",
            name="require_follow",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="gateaccess",
            name="verified_follow",
            field=models.BooleanField(default=False),
        ),
    ]

