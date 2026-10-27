import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("elm", "0005_leave_cancellation_request")]

    operations = [
        migrations.CreateModel(
            name="LeaveExtensionRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("requested_by_user_id", models.IntegerField(db_index=True)),
                ("requested_end_date", models.DateField()),
                ("reason", models.TextField()),
                ("status", models.CharField(choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")], default="pending", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("leave_request", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="extension_requests", to="elm.leaverequest")),
            ],
        ),
    ]
