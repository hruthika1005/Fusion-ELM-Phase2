from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("elm", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="leaverequest",
            name="user",
        ),
        migrations.AddField(
            model_name="leaverequest",
            name="user_id",
            field=models.IntegerField(
                db_index=True,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="leaverequest",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name="leaverequest",
            name="user_id",
            field=models.IntegerField(db_index=True),
        ),
    ]