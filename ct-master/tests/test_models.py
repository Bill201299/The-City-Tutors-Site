import datetime as dt
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from tutor.models import (
    ExitTicket,
    ExitTicketEasy,
    ExitTicketMedium,
    ExitTicketDifficult,
    GradeLevel,
    TutorRequest,
    MeetingMembership,
)
from tutor.factories import (
    K12TuteeProfileFactory,
    CollegeTuteeProfileFactory,
    TutorFactory,
    TutorRequestFactory,
    ScheduledMeetingFactory,
    PastMeetingFactory,
    MeetingMembershipFactory,
    create_past_meeting,
    create_previous_linked_meeting,
    create_next_linked_meeting,
)

class MeetingMembershipModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tutor = TutorFactory().user
        cls.tutee = K12TuteeProfileFactory().user
        cls.meeting = create_past_meeting(cls.tutee, cls.tutor)

    def test_tutee_confirmation_limit(self):
        tutee_membership = MeetingMembership.objects.get(
            user=self.tutee,
            meeting=self.meeting
        )
        limit = tutee_membership.confirmation_limit
        self.assertEqual(
            self.meeting.created_at+dt.timedelta(hours=48),
            limit
        )

    def test_tutor_confirmation_limit(self):
        tutor_membership = MeetingMembership.objects.get(
            user=self.tutor,
            meeting=self.meeting
        )
        limit = tutor_membership.confirmation_limit
        self.assertEqual(
            self.meeting.created_at+dt.timedelta(hours=72),
            limit
        )
