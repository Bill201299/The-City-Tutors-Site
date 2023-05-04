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
    Subject,
    Meeting,
    MeetingMembership,
    TimeSlot,
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
from tutor.queries import (
    get_requests_requiring_exit_ticket,
    get_chained_meetings,
)
from tutor.cron import (
    query_unconfirmed_tutors,
    cancel_unconfirmed_tutors,
    query_unconfirmed_students,
    cancel_unconfirmed_students,
)


class CancelUnconfirmedTutorsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tutor = TutorFactory().user
        cls.tutee = K12TuteeProfileFactory().user
        cls.meeting = Meeting.objects.create(
            active=True,
            scheduled_start=timezone.now()+dt.timedelta(hours=1),
            subject=Subject.objects.get(pk=1),
            scheduled_time_slot=TimeSlot.objects.get(pk=1),
        )
        cls.meeting.created_at = timezone.now()-dt.timedelta(hours=73)
        cls.meeting.save()
        cls.tutor_membership = MeetingMembership.objects.create(
            meeting=cls.meeting,
            user=cls.tutor,
            status='Pending Confirmation',
            user_role='Tutor',
        )
        cls.tutee_membership = MeetingMembership.objects.create(
            meeting=cls.meeting,
            user=cls.tutee,
            status='Confirmed',
            confirmation_timestamp=timezone.now()-dt.timedelta(hours=1),
            user_role='Tutee',
        )

    def test_query_tutor_memberships(self):
        memberships = query_unconfirmed_tutors()
        self.assertIn(self.tutor_membership.id, list(memberships.values_list('id', flat=True)))

    def test_cancel_unconfirmed_tutors(self):
        cancel_unconfirmed_tutors()


class CancelUnconfirmedStudentsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tutor = TutorFactory().user
        cls.tutee = K12TuteeProfileFactory().user
        cls.meeting = Meeting.objects.create(
            active=True,
            scheduled_start=timezone.now()+dt.timedelta(hours=1),
            subject=Subject.objects.get(pk=1),
            scheduled_time_slot=TimeSlot.objects.get(pk=1),
        )
        cls.meeting.created_at = timezone.now()-dt.timedelta(hours=73)
        cls.meeting.save()
        cls.tutor_membership = MeetingMembership.objects.create(
            meeting=cls.meeting,
            user=cls.tutor,
            status='Confirmed',
            user_role='Tutor',
        )
        cls.tutee_membership = MeetingMembership.objects.create(
            meeting=cls.meeting,
            user=cls.tutee,
            status='Pending Confirmation',
            confirmation_timestamp=timezone.now()-dt.timedelta(hours=1),
            user_role='Tutee',
        )
        cls.tutor_membership.created_at = timezone.now()-dt.timedelta(hours=73)
        cls.tutee_membership.created_at = timezone.now()-dt.timedelta(hours=73)
        cls.tutor_membership.save()
        cls.tutee_membership.save()
        cls.tutor_request = TutorRequest.objects.create(
            user=cls.tutee,
            subject=Subject.objects.get(pk=1),
            meeting=cls.meeting,
            timestamp=timezone.now()-dt.timedelta(hours=74)
        )

    def test_query_tutee_memberships(self):
        memberships = query_unconfirmed_students()
        self.assertIn(self.tutee_membership.id, list(memberships.values_list('id', flat=True)))

    def test_cancel_unconfirmed_tutors(self):
        cancel_unconfirmed_students()


# class ExitTicketFunctionTest(TestCase):
#     @classmethod
#     def setUpTestData(cls):
#         cls.tutor = TutorFactory().user
#         cls.tutee = K12TuteeProfileFactory(grade_level=None).user
#         cls.meeting3 = create_past_meeting(cls.tutee, cls.tutor)
#         cls.tutor_request = cls.meeting3.tutorrequest_set.all().first()

#         cls.meeting2 = create_previous_linked_meeting(cls.tutee, cls.tutor, cls.meeting3)
#         cls.meeting1 = create_previous_linked_meeting(cls.tutee, cls.tutor, cls.meeting2)

#     def test_get_requests_requiring_exit_ticket(self):
#         requests_requiring_exit_ticket = get_requests_requiring_exit_ticket(self.tutee)
#         self.assertEqual(requests_requiring_exit_ticket.first(), self.tutor_request)

#     def test_get_chained_meetings(self):
#         meetings = get_chained_meetings(self.tutor_request.meeting)
#         self.assertEqual(len(meetings), 3)

#     def test_no_requests_requiring_ticket_for_future_meeting(self):
#         tutee = CollegeTuteeProfileFactory().user
#         meeting = create_past_meeting(tutee, self.tutor)
#         tutor_request = meeting.tutorrequest_set.all().first()
#         meeting2 = create_next_linked_meeting(tutee, self.tutor, meeting, future=True)
#         requests_requiring_exit_ticket = get_requests_requiring_exit_ticket(tutee)

#         self.assertQuerysetEqual(requests_requiring_exit_ticket, TutorRequest.objects.none())


# class CancelUnconfirmedStudentsTest(TestCase):
#     @classmethod
#     def setUpTestData(cls):
#         cls.tutor = User.objects.get(username='cocotutor')
#         cls.student = User.objects.get(username='cocotutee')
#         cls.request = TutorRequest.objects.create(
#             user=student,
#             subject=Subject.objects.get(id=1),
#             notes='Please help',
#             timestamp=timezone.now()-dt.timedelta(days=4)
#         )
#         cls.meeting = Meeting.objects.create(
#             scheduled_time_slot=TimeSlot.objects.get(id=1),
#             scheduled_start=timezone.now()+dt.timedelta(days=1),
#             created_at=timezone.now()-dt.timedelta(days=4),
#             subject=subject.objects.get(id=1),
#         )

#     def test_meeting_status(self):
#         cls.

