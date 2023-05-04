# Generated by Django 3.2.5 on 2021-11-28 19:25

from django.db import migrations
import re
import string
import random
from datetime import datetime




def setup_test(apps, schema_editor):
    User = apps.get_model("auth", "User")
    Profile = apps.get_model("tutor", "Profile")
    Pronouns = apps.get_model("tutor", "Pronouns")
    AccountType = apps.get_model("tutor", "AccountType")

    def create_user(record):
        username = record['id']
        email = record['email']
        password = "".join(random.choices(string.ascii_letters + string.digits + string.punctuation, k=8))
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
        )
        return user

    def create_profile(user, record):
        full_name = record['first'] + " " + record['last']
        nickname = record['first']
        pronouns = Pronouns.objects.get(display=record['pronouns'])
        account_type = AccountType.objects.get(display="Tutor-Trainer")
        profile = Profile.objects.create(
            user=user,
            full_name=full_name,
            nickname=nickname,
            account_type=account_type,
            pronouns=pronouns,
        )
        return profile

    records = [
        {
            "first": "Amna",
            "last": "Tahir",
            "pronouns": "She/hers/her",
            "email": "amnatahir1996@gmail.com",
            "id": "TT002",
        },
    ]

    for record in records:
        user = create_user(record)
        profile = create_profile(user, record)


class Migration(migrations.Migration):

    dependencies = [
        ('tutor', '0005_manual_migration'),
    ]

    operations = [
        migrations.RunPython(setup_test),
    ]
