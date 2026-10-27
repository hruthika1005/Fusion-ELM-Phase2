import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("elm", "0006_leave_extension_request")]
    operations = [
        migrations.CreateModel(
            name="LeaveResumption",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("submitted_by_user_id", models.IntegerField(db_index=True)),
                ("actual_resumption_date", models.DateField()),
                ("details", models.TextField()),
                ("status", models.CharField(choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")], default="pending", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("leave_request", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="resumptions", to="elm.leaverequest")),
            ],
        ),
    ]
