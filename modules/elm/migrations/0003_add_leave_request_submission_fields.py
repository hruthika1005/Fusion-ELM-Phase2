from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("elm", "0002_align_user_id_schema"),
    ]

    operations = [
        migrations.AddField(
            model_name="leaverequest",
            name="reason",
            field=models.TextField(default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="leaverequest",
            name="half_day_session",
            field=models.CharField(
                blank=True,
                choices=[
                    ("first", "First half"),
                    ("second", "Second half"),
                ],
                default="",
                max_length=6,
            ),
        ),
    ]
