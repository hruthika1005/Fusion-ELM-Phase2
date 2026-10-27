import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("elm", "0004_leave_request_substitute"),
    ]

    operations = [
        migrations.CreateModel(
            name="LeaveCancellationRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("requested_by_user_id", models.IntegerField(db_index=True)),
                ("reason", models.TextField()),
                ("status", models.CharField(choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")], default="pending", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("leave_request", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="cancellation_requests", to="elm.leaverequest")),
            ],
        ),
    ]
