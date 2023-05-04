# Generated by Django 3.2.5 on 2022-07-19 09:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tutor', '0020_auto_20220519_1900'),
    ]

    operations = [
        migrations.AddField(
            model_name='tutorrequest',
            name='created_by',
            field=models.TextField(choices=[('User', 'User'), ('Site', 'Site')], default='User'),
        ),
        migrations.AlterField(
            model_name='meetingmembership',
            name='cancel_reason',
            field=models.TextField(blank=True, choices=[('', '----'), ('User', 'User'), ('Site', 'Site'), ('Cancelled Request', 'Cancelled Request'), ('Unconfirmed', 'Unconfirmed')], default='', null=True),
        ),
        migrations.AlterField(
            model_name='tutorrequest',
            name='cancel_reason',
            field=models.TextField(blank=True, choices=[('', '----'), ('User', 'User'), ('Unconfirmed', 'Unconfirmed'), ('Site', 'Site')], default='', null=True),
        ),
    ]