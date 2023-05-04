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

class TutorRequestViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tutor = TutorFactory().user
        cls.k12_tutee = K12TuteeProfileFactory(grade_level=None).user

    def test_exit_ticket_link_if_required_tickets(self):
        create_past_meeting(self.k12_tutee, self.tutor)
        self.client.login(username=self.k12_tutee.username, password="123")
        response = self.client.get(reverse("tutor:request-new"), follow=True)
        self.assertContains(response, "Go to Exit Ticket")

    def test_form_if_no_exit_tickets(self):
        self.client.login(username=self.k12_tutee.username, password="123")
        response = self.client.get(reverse("tutor:request-new"), follow=True)
        self.assertContains(response, "What do you need help with?")


class ExitTicketViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tutor = TutorFactory().user
        cls.k12_tutee = K12TuteeProfileFactory(grade_level=None).user

    def test_redirect_if_no_exit_ticket(self):
        self.client.login(username=self.k12_tutee.username, password="123")
        response = self.client.get(reverse("tutor:exit-ticket"), follow=True)
        self.assertRedirects(response, reverse("tutor:request"))

    def test_no_exit_ticket_for_recent_meetings(self):
        tutee = CollegeTuteeProfileFactory().user
        create_past_meeting(tutee, self.tutor, start_datetime=timezone.now()-dt.timedelta(days=2))

        self.client.login(username=tutee.username, password="123")
        response = self.client.get(reverse("tutor:exit-ticket"), follow=True)
        self.assertRedirects(response, reverse("tutor:request"))

    def test_grade_level_form_display(self):
        create_past_meeting(self.k12_tutee, self.tutor)
        self.client.login(username=self.k12_tutee.username, password="123")
        response = self.client.get(reverse("tutor:exit-ticket"), follow=True)
        self.assertContains(response, "student's grade level")

    def test_easy_exit_ticket(self):
        tutee = K12TuteeProfileFactory(grade_level=GradeLevel.objects.get(display="1st")).user
        create_past_meeting(tutee, self.tutor)
        
        self.client.login(username=tutee.username, password="123")
        response = self.client.get(reverse("tutor:exit-ticket"), follow=True)
        self.assertContains(response, "I like the tutor")

    def test_medium_exit_ticket(self):
        tutee = K12TuteeProfileFactory(grade_level=GradeLevel.objects.get(display="6th")).user
        create_past_meeting(tutee, self.tutor)

        self.client.login(username=tutee.username, password="123")
        response = self.client.get(reverse("tutor:exit-ticket"), follow=True)
        self.assertContains(response, "Did you like working with the tutor?")

    def test_difficult_exit_ticket_college_student(self):
        tutee = CollegeTuteeProfileFactory().user
        create_past_meeting(tutee, self.tutor)

        self.client.login(username=tutee.username, password="123")
        response = self.client.get(reverse("tutor:exit-ticket"), follow=True)
        self.assertContains(response, "How confident do you feel")

    def test_exit_ticket_with_multiple_meetings(self):
        tutee = CollegeTuteeProfileFactory().user
        meeting = create_past_meeting(tutee, self.tutor)
        tutor_request = meeting.tutorrequest_set.all().first()

        meeting2 = create_previous_linked_meeting(tutee, self.tutor, meeting)
        create_previous_linked_meeting(tutee, self.tutor, meeting2)

        self.client.login(username=tutee.username, password="123")
        response = self.client.get(reverse("tutor:exit-ticket"), follow=True)
        self.assertContains(response, "Exit Ticket for Sessions")

    def test_no_exit_ticket_for_chained_recent_meeting(self):
        tutee = CollegeTuteeProfileFactory().user
        meeting = create_past_meeting(tutee, self.tutor)
        tutor_request = meeting.tutorrequest_set.all().first()
        meeting2 = create_next_linked_meeting(tutee, self.tutor, meeting, future=True)

        self.client.login(username=tutee.username, password="123")
        response = self.client.get(reverse("tutor:exit-ticket"), follow=True)
        self.assertRedirects(response, reverse("tutor:request"))
