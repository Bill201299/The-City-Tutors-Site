import logging

from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives, BadHeaderError
from django.template.loader import render_to_string

logger = logging.getLogger("django")

class EmailNotification:
    def __init__(self, subject, recipients, text_file, html_file, text_str=None, context=None):
        self.subject = subject
        self.recipients = recipients

        if html_file:
            self.html_content = render_to_string(html_file, context)
        if text_file:
            self.text_content = render_to_string(text_file, context)
        else:
            self.text_content = text_str

    # def check_valid_email(self, email):
    #     regex = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    #     return bool(re.fullmatch(regex, email))

    def get_email_address_list(self, queryset):
        pass

    def send(self):
        logger.info(f"Sending emails...")

        if settings.DRY_RUN:
            print((
                f"Notify: \n"
                f"    Tutor: {tutor.email}, {tutor.profile.nickname}, {tutor.profile.full_name}, {tutor.profile.phone_number.as_e164} \n"
                f"    Tutee: {tutee.email}, {tutee.profile.nickname}, {tutee.profile.full_name}, {tutee.profile.phone_number.as_e164} "
            ))
            return
        else:
            msg = EmailMultiAlternatives(
                subject=self.subject,
                body=self.text_content,
                from_email=f"The City Tutors <{settings.EMAIL_HOST_USER}>",
                to=[],
                bcc=[self.recipients],
                reply_to=[settings.REPLYTO_ADDRESS],
            )
            if hasattr(self, 'html_content'):
                msg.attach_alternative(self.html_content, "text/html")
            msg.send()


class TestEmail(EmailNotification):
    subject = 'Testing Email'
    html_file = None
    text_file = None

    def get_text(self, recipient_name=None):
        return (
            f"Hi {recipient_name}, "
            f"This is a test email. "
        )

    def __init__(self, recipients):
        text_str = self.get_text(recipient_name='Coco')
        super().__init__(
            self.subject,
            recipients,
            self.text_file,
            self.html_file,
            text_str,
        )


# notify_tutor_meeting
class AutomatchEmailForTutor(EmailNotification):
    subject = 'A Tutoring Session Has Been Scheduled, Confirmation Needed'
    html_file = 'tutor/email_match_tutor.txt'
    text_file = None

    def __init__(self, subject, text_file, html_file, tutee_membership):
        super(EmailNotification, self).__init__(subject, text_file, html_file, tutee_membership)
        self.tutee_membership = tutee_membership

    @property
    def already_sent(self):
        if len(meeting.meetingmembership_set.filter(user_role="Tutee", status="Confirmed")) > 1:
            return

    def get_context(self):
        tutee = tutee_membership.user
        meeting = tutee_membership.meeting

        email_context = ({
            'tutor_name': tutor.profile.nickname or tutor.profile.full_name,
            'tutee_name': tutee.profile.nickname or tutee.profile.full_name,
            'subject': meeting.subject,
            "status_link": status_link,
            "scheduled_date": scheduled_date,
            "confirmation_deadline": tutor_membership.confirmation_limit.astimezone(pytz.timezone('America/New_York')).strftime("%B %-d at %-I:%M %p"),
        })

    def send(self):
        pass


class ManualMatchCompleteEmailForTutor(EmailNotification):
    subject = 'Student Has Confirmed Their Attendance'
    html_file = None
    text_file = None


class AutomatchEmailForTutee(EmailNotification):
    subject = 'A Tutoring Session Has Been Scheduled, Confirmation Needed'


class MemberCancellationEmail(EmailNotification):
    subject = 'Your Meeting Has Been Cancelled'


class UnconfirmedCancellationEmail(EmailNotification):
    subject = 'Your Meeting Attendance Has Been Cancelled'


class RepeatScheduledEmailForTutee(EmailNotification):
    subject = 'Repeat Sesssion Scheduled'


class RepeatScheduledEmailForTutor(EmailNotification):
    subject = 'Repeat Sesssion Scheduled'


class SiteUpdateRequestEmailForTutee(EmailNotification):
    subject = 'Program Coordinator Has Updated Your Request'


class SiteConfirmMembershipEmailForTutee(EmailNotification):
    subject = 'Program Coordinator Has Confirmed Your Upcoming Session'


class SiteCancelMembershipEmailForTutee(EmailNotification):
    subject = 'Program Coordinator Has Cancelled a Meeting For You'
    html_file = None
    text_file = None


class SiteCancelRequestEmailForTutee(EmailNotification):
    subject = ''
    html_file = None
    text_file = None


class ConnectionEmailForMentee(EmailNotification):
    subject = 'New Mentor Connection'
    html_file = None
    text_file = None

    def get_context(self, queryset):
        pass


class ConnectionEmailForMentor(EmailNotification):
    subject = 'New Mentee Connection'
    html_file = None
    text_file = None


class ExitTicketEmailForMentee(EmailNotification):
    subject = 'Please Complete Connection Survey'
    html_file = None
    text_file = None


class ExitTicketEmailForMentor(EmailNotification):
    subject = 'Please Complete Connection Survey'
    html_file = None
    text_file = None
