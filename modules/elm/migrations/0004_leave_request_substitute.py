from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("elm", "0003_add_leave_request_submission_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="leaverequest",
            name="substitute_status",
            field=models.CharField(
                choices=[
                    ("not_required", "Not required"),
                    ("pending", "Awaiting response"),
                    ("accepted", "Accepted"),
                    ("declined", "Declined"),
                ],
                default="not_required",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="leaverequest",
            name="substitute_user_id",
            field=models.IntegerField(blank=True, db_index=True, null=True),
        ),
    ]
