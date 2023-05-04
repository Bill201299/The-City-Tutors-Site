# Generated manually
import time
from datetime import datetime
from calendar import day_name

from django.db import migrations, transaction
from tutor.models import get_time_slots, get_subjects, get_sites, get_sectors, get_genders, get_ethnicities, get_pronouns, get_account_types


def add_questions(apps, schema_editor):
    TimeSlot = apps.get_model("tutor", "TimeSlot")
    for time_slot, _ in get_time_slots():
        split = time_slot.split(", ")
        day_str = split[0]
        time_str = split[1]
        day_int = time.strptime(day_str, "%A").tm_wday
        time_int = int(datetime.strptime(time_str, "%I%p").strftime('%H'))
        TimeSlot.objects.create(display=time_slot, day=day_int, time=time_int)
    Subject = apps.get_model("tutor", "Subject")
    Sector = apps.get_model("tutor", "Sector")
    for sector, _ in get_sectors():
        sector_obj = Sector.objects.create(display=sector)
        for subject, _ in get_subjects(sector):
            Subject.objects.create(display=subject, sector=sector_obj)
    Site = apps.get_model("tutor", "Site")
    for site, _ in get_sites():
        Site.objects.create(display=site)
    Gender = apps.get_model("tutor", "Gender")
    for gender, _ in get_genders():
        Gender.objects.create(display=gender)
    Ethnicity = apps.get_model("tutor", "Ethnicity")
    for ethnicity, _ in get_ethnicities():
        Ethnicity.objects.create(display=ethnicity)
    Pronouns = apps.get_model("tutor", "Pronouns")
    for pronouns, _ in get_pronouns():
        Pronouns.objects.create(display=pronouns)
    AccountType = apps.get_model("tutor", "AccountType")
    for account_type, _ in get_account_types():
        AccountType.objects.create(display=account_type)

class Migration(migrations.Migration):

    dependencies = [
        ("tutor", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(add_questions),
    ]
