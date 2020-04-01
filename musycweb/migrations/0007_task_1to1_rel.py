# Generated by Django 3.0.3 on 2020-04-01 23:33

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('django_celery_results', '0007_remove_taskresult_hidden'),
        ('musycweb', '0006_task_batch'),
    ]

    operations = [
        migrations.AlterField(
            model_name='datasettask',
            name='task',
            field=models.OneToOneField(db_constraint=False, on_delete=django.db.models.deletion.CASCADE, to='django_celery_results.TaskResult', to_field='task_id'),
        ),
    ]
