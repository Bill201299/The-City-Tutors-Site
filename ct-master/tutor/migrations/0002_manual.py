# Generated manually
import time
from datetime import datetime
from calendar import day_name

from django.db import migrations, transaction
from tutor.models import get_time_slots, get_subjects, get_sites, get_sectors, get_genders, get_ethnicities, get_pronouns, get_account_types, get_site_locations, get_site_tier, get_tiers


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
        nongroup_subjects, group_subjects = get_subjects(sector)
        for subject, _ in nongroup_subjects:
            Subject.objects.create(display=subject, sector=sector_obj)
        for subject, _ in group_subjects:
            Subject.objects.create(display=subject, sector=sector_obj, group_sessions=True)
    Tier = apps.get_model("tutor", "Tier")
    for tier, pool_hrs, indiv_hrs, subjs, subj_hrs in get_tiers():
        Tier.objects.create(display=tier, max_pooled_hours=pool_hrs, max_individual_hours=indiv_hrs, max_subjects=subjs, max_hours_per_subj=subj_hrs)
    Site = apps.get_model("tutor", "Site")
    SiteLocation = apps.get_model("tutor", "SiteLocation")
    for site, _ in get_sites():
        site_tier = get_site_tier(site)
        site_obj = Site.objects.create(display=site, tier=Tier.objects.get(display=site_tier))
        for site_location, _ in get_site_locations(site):
            site_location_obj = SiteLocation.objects.create(display=site_location, site=site_obj)
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
