from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from tutor.models import (
    ExitTicket,
    ExitTicketEasy,
    ExitTicketMedium,
    ExitTicketDifficult,
    GradeLevel,
    Sector,
    TutorRequest,
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
)


class ExitTicketFormTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tutor = TutorFactory().user
        cls.k12_tutee = K12TuteeProfileFactory(grade_level=None).user

    def test_grade_level_form_submit_redirects(self):
        create_past_meeting(self.k12_tutee, self.tutor)
        self.client.login(username=self.k12_tutee.username, password="123")
        response = self.client.post(
            reverse("tutor:exit-ticket"),
            data={
                "username": self.k12_tutee.username,
                "password": "123",
                "grade_level": 3,
                "submit-grade": ['Submit'],
            },
            secure=True,
            follow=True,
        )
        self.assertRedirects(response, reverse("tutor:exit-ticket"), status_code=302)
        self.k12_tutee.profile.refresh_from_db()
        self.assertEqual(self.k12_tutee.profile.grade_level, GradeLevel.objects.get(display="1st"))

        redirect_url, status_code = response.redirect_chain[-1]
        redirect_response = self.client.get(redirect_url, follow=False)
        self.assertContains(redirect_response, "I like the tutor")

    def test_multiple_exit_tickets(self):
        tutee = K12TuteeProfileFactory(grade_level=GradeLevel.objects.get(display="1st")).user
        create_past_meeting(tutee, self.tutor)
        create_past_meeting(tutee, self.tutor)

        self.client.login(username=tutee.username, password="123")
        response = self.client.post(
            reverse("tutor:exit-ticket"),
            data={
                "username": tutee.username,
                "password": "123",
                "like_tutor": "True",
                "safe_mistakes": "True",
                "tutor_helps": "True",
                "understand_better": "True",
                "submit": ['Submit'],
            },
            secure=True,
            follow=True,
        )
        self.assertRedirects(response, reverse("tutor:exit-ticket"), status_code=302)
        self.assertContains(response, "I like the tutor")
        response = self.client.post(
            reverse("tutor:exit-ticket"),
            data={
                "username": tutee.username,
                "password": "123",
                "like_tutor": "True",
                "safe_mistakes": "True",
                "tutor_helps": "True",
                "understand_better": "True",
                "submit": ['Submit'],
            },
            secure=True,
            follow=True,
        )
        self.assertRedirects(response, reverse("tutor:request"), status_code=302)
        self.assertContains(response, "Manage Your Requests")

        response = self.client.get(reverse("tutor:request-new"), follow=True)
        self.assertContains(response, "What do you need help with?")


    def test_easy_exit_ticket_submission(self):
        tutee = K12TuteeProfileFactory(grade_level=GradeLevel.objects.get(display="1st")).user
        create_past_meeting(tutee, self.tutor)
        
        self.client.login(username=tutee.username, password="123")
        response = self.client.post(
            reverse("tutor:exit-ticket"),
            data={
                "username": self.k12_tutee.username,
                "password": "123",
                "like_tutor": "True",
                "safe_mistakes": "False",
                "tutor_helps": "True",
                "understand_better": "False",
                "submit": ['Submit'],
            },
            secure=True,
            follow=True,
        )
        ticket = ExitTicketEasy.objects.all().first()
        self.assertEqual(ticket.like_tutor, True)
        self.assertEqual(ticket.safe_mistakes, False)
        self.assertEqual(ticket.tutor_helps, True)
        self.assertEqual(ticket.understand_better, False)

    def test_medium_exit_ticket_submission(self):
        tutee = K12TuteeProfileFactory(grade_level=GradeLevel.objects.get(display="3rd")).user
        create_past_meeting(tutee, self.tutor)
        
        self.client.login(username=tutee.username, password="123")
        response = self.client.post(
            reverse("tutor:exit-ticket"),
            data={
                "username": self.k12_tutee.username,
                "password": "123",
                "like_tutor": "ALWAYS",
                "be_open": "SOMETIMES",
                "tutor_help": "NEVER",
                "better_understand": "ALWAYS",
                "submit": ['Submit'],
            },
            secure=True,
            follow=True,
        )
        ticket = ExitTicketMedium.objects.all().first()
        self.assertEqual(ticket.like_tutor, "ALWAYS")
        self.assertEqual(ticket.be_open, "SOMETIMES")
        self.assertEqual(ticket.tutor_help, "NEVER")
        self.assertEqual(ticket.better_understand, "ALWAYS")

    def test_difficult_exit_ticket_submission(self):
        tutee = K12TuteeProfileFactory(
            sector=Sector.objects.get(display="Middle School"),
            grade_level=GradeLevel.objects.get(display="7th")
        ).user
        create_past_meeting(tutee, self.tutor)
        
        self.client.login(username=tutee.username, password="123")
        response = self.client.post(
            reverse("tutor:exit-ticket"),
            data={
                "username": self.k12_tutee.username,
                "password": "123",
                "confidence": "7",
                "tutor_satisfaction": "3",
                "satisfaction_reason": "",
                "tutor_helpful": "3",
                "helpful_reason": "",
                "tutor_comfortable": "4",
                "comfortable_reason": "",
                "still_help": "True",
                "help_concepts": "Math",
                "recommendations": "",
                "thank_letter_yesno": "False",
                "thank_letter": "Thank you!",
                "additional_comments": "",
                "submit": ['Submit'],
            },
            secure=True,
            follow=True,
        )
        ticket = ExitTicketDifficult.objects.all().first()
        self.assertEqual(ticket.confidence, 7)
        self.assertEqual(ticket.tutor_satisfaction, 3)
        self.assertEqual(ticket.satisfaction_reason, "")
        self.assertEqual(ticket.tutor_helpful, 3)
        self.assertEqual(ticket.helpful_reason, "")
        self.assertEqual(ticket.tutor_comfortable, 4)
        self.assertEqual(ticket.comfortable_reason, "")
        self.assertEqual(ticket.still_help, True)
        self.assertEqual(ticket.help_concepts, "Math")
        self.assertEqual(ticket.recommendations, "")
        self.assertEqual(ticket.thank_letter_yesno, False)
        self.assertEqual(ticket.thank_letter, "Thank you!")
        self.assertEqual(ticket.additional_comments, "")
