import datetime as dt

from django.contrib.auth import get_user_model
from django.db.models import F, Q, Count, BooleanField, ExpressionWrapper, DurationField, OuterRef, Subquery
from django.test import TestCase
from django.utils import timezone

from .models import (
    Site,
    OrientationTraining,
    TutorTraining,
    RoleplayTraining,
    BackgroundCheckRequest,
    Issue,
    TuteeIssue,
    HarassIssue,
    Profile,
    Meeting,
    MeetingMembership,
    TutorRequest,
    AccountType,
    Subject,
    Sector,
    TimeSlot,
    TuteeAssessment,
    Site
)
from .cron  import cancel_unconfirmed
User = get_user_model()

class CancelTestCase(TestCase):
    def setUp(self):
        # Case A
        request_timestamp = timezone.now()-dt.timedelta(hours=24)
        scheduled_start = request_timestamp+dt.timedelta(hours=36)

        tutor_user = User.objects.create_user(
            username="test_tutor",
        )
        subject_reading = Subject.objects.get(
            display="Reading", sector=Sector.objects.get(display="Elementary School")
        )
        tutee_user = User.objects.create_user(
            username="test_tutee",
        )
    
        meeting_A = Meeting.objects.create(
            scheduled_time_slot=TimeSlot.objects.get(pk=2),
            scheduled_start=scheduled_start,
            subject=subject_reading,
        )
        meeting_A.members.add(tutee_user, through_defaults={
            "user_role": "Tutee",
            "status": "Pending Confirmation",
        })
        meeting_A.members.add(tutor_user, through_defaults={
            "user_role": "Tutor",
            "status": "Confirmed",
        })
        request = TutorRequest.objects.create(
            user=tutee_user,
            subject=subject_reading,
            timestamp=request_timestamp,
            meeting=meeting_A,
        )

        # Case B
        scheduled_start = timezone.now()+dt.timedelta(hours=12)
        request_timestamp = scheduled_start-dt.timedelta(hours=35)

        meeting_B = Meeting.objects.create(
            scheduled_time_slot=TimeSlot.objects.get(pk=2),
            scheduled_start=scheduled_start,
            subject=subject_reading,
        )
        meeting_B.members.add(tutee_user, through_defaults={
            "user_role": "Tutee",
            "status": "Pending Confirmation",
        })
        meeting_B.members.add(tutor_user, through_defaults={
            "user_role": "Tutor",
            "status": "Confirmed",
        })
        request = TutorRequest.objects.create(
            user=tutee_user,
            subject=subject_reading,
            timestamp=request_timestamp,
            meeting=meeting_B,
        )

    def test_cancel_unconfirmed(self):
        time_between = ExpressionWrapper(
            F('meeting__scheduled_start') - F('request_timestamp'),
            output_field=DurationField()
        )

        user_request = TutorRequest.objects.filter(user=OuterRef("user"), meeting=OuterRef("meeting"))

        unconfirmed_memberships = (MeetingMembership.objects
            .annotate(
                request_timestamp=Subquery(user_request.values("timestamp"))
            )
            .filter(status="Pending Confirmation", user_role="Tutee")
            .annotate(time_between=time_between)
        )

        memberships = unconfirmed_memberships.filter(
            (
                Q(time_between__gte=dt.timedelta(hours=36)) &
                Q(meeting__tutorrequest__timestamp__lte=timezone.now()-dt.timedelta(hours=24))
            ) |
            (
                Q(time_between__lt=dt.timedelta(hours=36)) &
                Q(meeting__scheduled_start__lte=timezone.now()+dt.timedelta(hours=12))
            )
        ).distinct()

        membership_response = MeetingMembership.objects.filter(user_role="Tutee")
        self.assertEqual(list(membership_response), list(memberships))
