# Generated manually

import pytz
from datetime import datetime, timedelta, date
from django.db import migrations, transaction
from django.contrib.auth import get_user_model
from django.utils import timezone


def setup_test(apps, schema_editor):
    Meeting = apps.get_model("tutor", "Meeting")
    MeetingMembership = apps.get_model("tutor", "MeetingMembership")
    TimeSlot = apps.get_model("tutor", "TimeSlot")
    Subject = apps.get_model("tutor", "Subject")
    Sector = apps.get_model("tutor", "Sector")
    AccountType = apps.get_model("tutor", "AccountType")
    BackgroundCheckRequest = apps.get_model("tutor", "BackgroundCheckRequest")
    OrientationTraining = apps.get_model("tutor", "OrientationTraining")
    TutorTraining = apps.get_model("tutor", "TutorTraining")
    RoleplayTraining = apps.get_model("tutor", "RoleplayTraining")
    TutorRequest = apps.get_model("tutor", "TutorRequest")
    Meeting = apps.get_model("tutor", "Meeting")
    MeetingMembership = apps.get_model("tutor", "MeetingMembership")

    User = apps.get_model("auth", "User")
    Profile = apps.get_model("tutor", "Profile")

    # --- Create Tutor Trainer
    tutor_trainer_user = User.objects.create_user(
        username="test_tutor_trainer",
        email="testtutortrainer@thecitytutors.org",
        password="asdfasdf",
    )
    tutor_trainer_profile = Profile.objects.create(
        user=tutor_trainer_user,
        full_name="Test Tutor Trainer",
        nickname="Test Tutor Trainer",
        onboarded=True,
        account_type=AccountType.objects.get(display="Tutor-Trainer"),
        phone_number="5162342605",
    )
    # --- Create Tutee ---
    tutee_user = User.objects.create_user(
        username="test_tutee",
        email="testtutee@thecitytutors.org",
        password="asdfasdf",
    )
    tutee_profile = Profile.objects.create(
        user=tutee_user,
        full_name="Test Tutee",
        nickname="Test Tutee",
        sector=Sector.objects.get(display="Elementary School"),
        onboarded=True,
        account_type=AccountType.objects.get(display="K-12-Tutee"),
        phone_number="5162342605",
    )
    tutee_profile.available.set(TimeSlot.objects.all())
    # --- Create Tutor ---
    for subject in ("Social Studies", "Math", "English"):
        tutor_user = User.objects.create_user(
            username=f"test_tutor_{subject.lower()}",
            email="testtutor@thecitytutors.org",
            password="asdfasdf",
        )
        sector_elementary = Sector.objects.get(display="Elementary School")
        subject_object = Subject.objects.get(
            display=subject, sector=sector_elementary
        )
        tutor_profile = Profile.objects.create(
            user=tutor_user,
            full_name=f"Test Tutor ({subject})",
            nickname=f"Test Tutor ({subject})",
            onboarded=True,
            account_type=AccountType.objects.get(display="Tutor"),
            phone_number="5162342605",
            offered_hours=5,
            tutee_contact="Join my zoom room: ...",
        )
        background_check_request = BackgroundCheckRequest.objects.create(
            user=tutor_user,
            status="Approved",
        )
        tutor_profile.available.set(TimeSlot.objects.all())
        tutor_profile.offered_subjects.set([subject_object])
        tutor_profile.offered_sectors.set([sector_elementary])
        OrientationTraining.objects.create(
            user=tutor_user,
            tutor_role="",
            instructor_does="",
            tutor_does="",
            tutor_trainer=tutor_trainer_profile,
            tutor_trainer_rating=1,
            training_practical=1,
            overall_quality_rating=1,
            suggestions="",
        )
        TutorTraining.objects.create(
            user=tutor_user,
            what_is_minimalism="",
            resources_for_control="",
            video_conference_applications="",
            facial_and_body_language="",
            speaking_and_language="",
        )
        RoleplayTraining.objects.create(
            user=tutor_user,
            what_difficulties="",
            what_strategies="",
            what_could_you_have_done_better="",
            how_did_tutor_help="",
            what_did_you_learn="",
            how_can_tutor_improve="",
        )
    # --- Tutor Request ---
    subject_social_studies = Subject.objects.get(
        display="Social Studies", sector=sector_elementary
    )
    request = TutorRequest.objects.create(
        user=tutee_user,
        hours=1,
        subject=subject_social_studies,
        timestamp=timezone.now(),
    )
    meeting = Meeting.objects.create(
        scheduled_time_slot=TimeSlot.objects.get(pk=2),  # not representative
        scheduled_start=timezone.now(),
        subject=subject_social_studies,
    )
    meeting.requests.add(request)
    membership = MeetingMembership(
        user=tutor_user,
        user_role="Tutor",
        meeting=meeting,
        status="Confirmed",
    )
    membership.save()
    membership = MeetingMembership(
        user=tutee_user,
        user_role="Tutee",
        meeting=meeting,
        status="Confirmed",
    )
    membership.save()


class Migration(migrations.Migration):

    dependencies = [
        ("tutor", "0002_manual"),
    ]

    operations = [
        migrations.RunPython(setup_test),
    ]
