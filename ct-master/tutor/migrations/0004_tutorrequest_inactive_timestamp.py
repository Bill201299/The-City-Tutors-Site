# Generated by Django 3.2.5 on 2022-02-18 17:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tutor', '0003_auto_20220217_1656'),
    ]

    operations = [
        migrations.AddField(
            model_name='tutorrequest',
            name='inactive_timestamp',
            field=models.DateTimeField(blank=True, default=None, null=True),
        ),
    ]
