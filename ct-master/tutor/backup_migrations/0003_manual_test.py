# Generated manually

import pytz
from datetime import datetime, timedelta, date
from django.db import migrations, transaction
from django.contrib.auth import get_user_model
from django.utils import timezone


def setup_test(apps, schema_editor):
    Meeting = apps.get_model("tutor", "Meeting")
    MeetingMembership = apps.get_model("tutor", "MeetingMembership")
    TuteeAssessment = apps.get_model("tutor", "TuteeAssessment")
    TimeSlot = apps.get_model("tutor", "TimeSlot")
    Subject = apps.get_model("tutor", "Subject")
    Sector = apps.get_model("tutor", "Sector")
    Site = apps.get_model("tutor", "Site")
    AccountType = apps.get_model("tutor", "AccountType")
    BackgroundCheckRequest = apps.get_model("tutor", "BackgroundCheckRequest")

    User = apps.get_model("auth", "User")
    Profile = apps.get_model("tutor", "Profile")
    admin = User.objects.create_superuser("admin", "admin@ct.com", "123")
    admin_profile = Profile.objects.create(user=admin, full_name="Admin", account_type=AccountType.objects.get(display="Admin"))
    admin_profile.available.add(TimeSlot.objects.get(pk=1))
    admin_profile.available.add(TimeSlot.objects.get(pk=2))
    BackgroundCheckRequest.objects.create(user=admin, status="Approved")
    tutor = User.objects.create_user(
        username="tutor", email="a@gmail.com", password="123"
    )
    Profile.objects.create(user=tutor, full_name="Test Tutor", account_type=AccountType.objects.get(display="Tutor"))
    tutee = User.objects.create_user(
        username="tutee", email="b@gmail.com", password="123"
    )
    Profile.objects.create(user=tutee, full_name="Test Tutee", account_type=AccountType.objects.get(display="K-12-Tutee"))

    tutors = [
        (
            User.objects.create_user(
                username="tutor_terry", email="terry@gmail.com", password="123"
            ),
            "Elementary School",
            ["Math"],
            [1, 2],
            "Terry Terrific",
        ),
        (
            User.objects.create_user(
                username="tutor_garret", email="garret@gmail.com", password="123"
            ),
            "Elementary School",
            ["English", "Math"],
            [2, 3],
            "Garret Garvery",
        ),
        (
            User.objects.create_user(
                username="tutor_winston", email="winston@gmail.com", password="123"
            ),
            "Middle School",
            ["Math"],
            [3, 4],
            "Winston Winner",
        ),
    ]
    tutees = [
        (
            User.objects.create_user(
                username="tutee_mabel", email="mabel@gmail.com", password="123"
            ),
            "Elementary School",
            ["English", "Math"],
            [2, 3],
            "Mabel Marble",
            "Children's Aid",
        ),
        (
            User.objects.create_user(
                username="tutee_delia", email="delia@gmail.com", password="123"
            ),
            "Elementary School",
            ["English", "Math"],
            [3, 4],
            "Delilah Danger",
            "Henry Street Settlement",
        ),
        (
            User.objects.create_user(
                username="tutee_sam", email="sam@gmail.com", password="123"
            ),
            "Middle School",
            ["Math"],
            [4, 1],
            "Sam Saw",
            "Colin Powell",
        ),
    ]

    meeting = Meeting.objects.create(scheduled_time_slot=TimeSlot.objects.get(pk=1))
    membership = MeetingMembership(user=tutee, user_role="Tutee", meeting=meeting)
    membership.save()
    membership = MeetingMembership(user=tutor, user_role="Tutor", meeting=meeting)
    membership.save()

    session_dates = [
        datetime(2021, 10, 25, 16, 32, 11, 342380, tzinfo=pytz.UTC),
        datetime(2021, 10, 31, 17, 3, 23, 129821, tzinfo=pytz.UTC),
        datetime(2021, 11, 1, 15, 58, 10, 221122, tzinfo=pytz.UTC),
    ]

    for tutor, pop, subjs, avails, full_name in tutors:
        profile = Profile.objects.create(user=tutor, full_name=full_name, account_type=AccountType.objects.get(display="Tutor"))
        BackgroundCheckRequest.objects.create(user=tutor, status="Approved")
        sector_obj = Sector.objects.get(display=pop)
        for subj in subjs:
            profile.offered_subjects.add(Subject.objects.get(display=subj, sector=sector_obj))
        for avail in avails:
            profile.available.add(TimeSlot.objects.get(pk=avail))
        profile.offered_sectors.add(sector_obj)
        profile.can_speak_english = True
        profile.offered_hours = 3
        profile.save()

    for tutee, pop, subjs, avails, full_name, site in tutees:
        profile = Profile.objects.create(user=tutee, full_name=full_name, account_type=AccountType.objects.get(display="K-12-Tutee"))
        for avail in avails:
            profile.available.add(TimeSlot.objects.get(pk=avail))
        profile.sector = Sector.objects.get(display=pop)
        profile.can_speak_english = True
        profile.requested_hours = 3
        profile.site = Site.objects.get(display=site)
        profile.save()

    meeting = Meeting.objects.create(scheduled_time_slot=TimeSlot.objects.get(pk=2))
    membership = MeetingMembership(
        user=tutors[0][0], user_role="Tutor", meeting=meeting
    )
    membership.save()
    membership = MeetingMembership(
        user=tutees[1][0], user_role="Tutee", meeting=meeting
    )
    membership.save()


class Migration(migrations.Migration):

    dependencies = [
        ("tutor", "0001_initial"),
        ("tutor", "0002_manual"),
    ]

    operations = [
        migrations.RunPython(setup_test),
    ]
