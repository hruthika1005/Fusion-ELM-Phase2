import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("elm", "0007_leave_resumption")]
    operations = [
        migrations.CreateModel(
            name="LeaveBalance",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("user_id", models.IntegerField(db_index=True)),
                ("leave_type", models.CharField(choices=[("CL", "CL"), ("RH", "RH"), ("SCL", "SCL"), ("EL", "EL"), ("COL", "COL"), ("VL", "VL")], max_length=10)),
                ("year", models.PositiveIntegerField()),
                ("entitled_days", models.DecimalField(decimal_places=1, default=0, max_digits=6)),
                ("carried_forward_days", models.DecimalField(decimal_places=1, default=0, max_digits=6)),
                ("used_days", models.DecimalField(decimal_places=1, default=0, max_digits=6)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"constraints": [models.UniqueConstraint(fields=("user_id", "leave_type", "year"), name="elm_balance_per_year"), models.CheckConstraint(condition=models.Q(("entitled_days__gte", 0), ("carried_forward_days__gte", 0), ("used_days__gte", 0)), name="elm_balance_non_negative")]},
        ),
        migrations.CreateModel(
            name="LeaveAccountEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("days", models.DecimalField(decimal_places=1, max_digits=6)),
                ("kind", models.CharField(max_length=20)),
                ("note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("balance", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="entries", to="elm.leavebalance")),
                ("leave_request", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="account_entries", to="elm.leaverequest")),
            ],
        ),
    ]
