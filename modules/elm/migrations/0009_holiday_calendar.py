import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("elm", "0008_leave_balances")]
    operations = [
        migrations.CreateModel(
            name="HolidayCalendar",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("year", models.PositiveIntegerField(unique=True)),
                ("is_published", models.BooleanField(default=False)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="Holiday",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField()),
                ("name", models.CharField(max_length=150)),
                ("is_restricted", models.BooleanField(default=False)),
                ("calendar", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="holidays", to="elm.holidaycalendar")),
            ],
            options={"constraints": [models.UniqueConstraint(fields=("calendar", "date"), name="elm_holiday_once_per_calendar_day")]},
        ),
    ]
