# Generated by Django 3.2.5 on 2022-05-21 22:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tutor', '0018_alter_meetingmembership_confirmation_timestamp'),
    ]

    operations = [
        migrations.AlterField(
            model_name='issue',
            name='type',
            field=models.TextField(choices=[('General', 'General'), ('Harrasment', 'Harrasment'), ('Bug Report', 'Bug Report'), ("My Tutor Didn't Show Up", "My Tutor Didn't Show Up")], default='General'),
        ),
    ]
