# Generated by Django 3.2.5 on 2022-03-17 23:28

from django.db import migrations

def update_timeslots(apps, schema_editor):
    TimeSlot = apps.get_model("tutor", "TimeSlot")

    for time_slot in TimeSlot.objects.all():
        time_slot.display = time_slot.display.replace(",", "")
        time_slot.save()


class Migration(migrations.Migration):

    dependencies = [
        ('tutor', '0012_auto_20220310_1942'),
    ]

    operations = [
        migrations.RunPython(update_timeslots),
    ]
