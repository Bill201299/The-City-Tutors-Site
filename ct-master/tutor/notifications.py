import datetime as dt
import re
import pytz
import smtplib
import twilio.rest
from rest_framework import serializers
from twilio.base.exceptions import TwilioRestException
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail, EmailMultiAlternatives, BadHeaderError
from django.db.models import Q
from django.template.loader import render_to_string

from .models import (
    Profile,
    Meeting,
    MeetingMembership,
    TutorRequest,
)

User = get_user_model()

logger = logging.getLogger("django")

TWILIO_CLIENT = None
if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
    TWILIO_CLIENT = twilio.rest.Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


def email_test():
    email_context = ({'tutor_name': "Coco"})

    text_content = render_to_string('tutor/email_bgcheck_tutor.txt', email_context)
    html_content = render_to_string('tutor/email_bgcheck_tutor.html', email_context)

    send_emails(
        user_emails=[settings.RECIPIENT_ADDRESS],
        text_content=text_content,
        html_content=html_content,
        subject="The City Tutors Background Check",
    )


def sms_test():
    if not settings.SEND_TO_USERS:
        user = User.objects.get(pk=1)
        send_sms(user, "Test message")


def send_sms(user, body, call_source=None):
    logger.info(f"send_sms CALLED ({call_source})")
    if settings.SKIP_NOTIFY_SMS:
        return
    if not user.profile.sms_notifications:
        return
    
    if TWILIO_CLIENT:
        if settings.SEND_TO_USERS:
            number = user.profile.phone_number.as_e164
        else:
            number = settings.DEVELOPMENT_NUMBER

        try:
            TWILIO_CLIENT.messages.create(
                body=body,
                from_=settings.TWILIO_NUMBER,
                to=number,
            )
            print(f"Sent to {user} at {number}")
            logger.info(f"Notification: SMS to {user.username} at {number}")
        except TwilioRestException as e:
            print(e)
            logger.info(f"Error Notification: TwilioRestException")
            return
    else:
        print("No TWILIO_CLIENT")
        logger.info(f"Error Notification: No TWILIO CLIENT")
    logger.info(f"send_sms COMPLETE ({call_source})")


# Not in use
def send_sms_by_number(numbers, body):
    logger.info(f"send_sms_by_number CALLED")
    if settings.SKIP_NOTIFY_SMS:
        return
    
    if TWILIO_CLIENT:
        for number in numbers:
            try:
                TWILIO_CLIENT.messages.create(
                    body=body,
                    from_=settings.TWILIO_NUMBER,
                    to="1"+number,
                )
                print(f"Sent to {number}")
                logger.info(f"sent SMS to {number}")
            except TwilioRestException as e:
                print(e)
                return
    else:
        print("No TWILIO_CLIENT")
    logger.info(f"send_sms_by_number COMPLETE")


def send_emails(user_emails, subject, text_content, html_content, call_source=None):
    from .cron import print_with_timestamp
    logger.info(f"send_emails CALLED ({call_source}), user_emails={user_emails}, subject={subject}")
    if settings.SKIP_NOTIFY_EMAIL:
        logger.info(f"Error Notification: SKIP NOTIFY EMAIL is True")
        return

    if settings.SEND_TO_USERS:
        recipients = user_emails
    else:
        recipients = [settings.RECIPIENT_ADDRESS]
        logger.info("Error Notification: SEND TO USERS is False")

    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=f"The City Tutors <{settings.EMAIL_HOST_USER}>",
            to=[],
            bcc=recipients,
            reply_to=[settings.REPLYTO_ADDRESS],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        # print(f"Sent to {recipients}")
        logger.info(f"send_emails ({call_source}): email sent to {recipients}")
    except BadHeaderError:
        logger.info('Invalid header found.')
    except smtplib.SMTPException as e:
        logger.info("SMTP Exception")
        error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
        raise serializers.ValidationError(error)
    logger.info(f"send_emails COMPLETE ({call_source})")


def notify_tutor_meeting(tutee_membership, call_source=None):
    logger.info(f"notify_tutor_meeting CALLED ({call_source}), #{tutee_membership.pk} {tutee_membership}")
    tutee = tutee_membership.user
    meeting = tutee_membership.meeting
    # If a student has already confirmed, tutor has already been notified
    if len(meeting.meetingmembership_set.filter(user_role="Tutee", status="Confirmed")) > 1:
        logger.info(f"notify_tutor_meeting COMPLETE: tutor already notified")
        return
    scheduled_date = meeting.scheduled_start.astimezone(pytz.timezone('America/New_York')).strftime("%B %-d at %-I:%M %p")
    status_link = f"https://app.thecitytutors.org/manage"

    tutor_memberships = meeting.meetingmembership_set.filter(user_role="Tutor")
    
    for tutor_membership in tutor_memberships:
        tutor = tutor_membership.user
    
        email_context = ({
            'tutor_name': tutor.profile.nickname or tutor.profile.full_name,
            'tutee_name': tutee.profile.nickname or tutee.profile.full_name,
            'subject': meeting.subject,
            "status_link": status_link,
            "scheduled_date": scheduled_date,
            "confirmation_deadline": tutor_membership.confirmation_limit.astimezone(pytz.timezone('America/New_York')).strftime("%B %-d at %-I:%M %p"),
        })

        if tutor_membership.status == "Confirmed":
            tutor_text_content = render_to_string('tutor/email_match_tutor_confirmed.txt', email_context)
            tutor_html_content = render_to_string('tutor/email_match_tutor_confirmed.html', email_context)

            email_subject = "Student Has Confirmed Their Attendance"
            body = (
                f"Student confirmed session scheduled for {scheduled_date}."
                f"Please check {status_link} to review meeting details"
            )

        else:
            tutor_text_content = render_to_string('tutor/email_match_tutor.txt', email_context)
            tutor_html_content = render_to_string('tutor/email_match_tutor.html', email_context)

            email_subject = "A Tutoring Session Has Been Scheduled, Confirmation Needed"
            body = (
                f"Session scheduled on {scheduled_date} with {tutee.profile.nickname or tutee.profile.full_name}. "
                f"Please check {status_link} to confirm or cancel if you cannot make it"
            )

        if tutor.profile.sms_notifications:
            send_sms(tutor, body, call_source=call_source)
    
        send_emails(
            user_emails=[tutor.email],
            text_content=tutor_text_content,
            html_content=tutor_html_content,
            subject=email_subject,
            call_source=call_source,
        )
    logger.info(f"notify_tutor_meeting COMPLETE #{tutee_membership.pk}")


def notify_match(match_result):
    logger.info(f"notify_match function called")
    tutee = match_result.tutee
    tutor = match_result.tutor
    request = match_result.request
    parent_name = tutee.profile.parent_or_guardian_name or tutee.profile.nickname or tutee.profile.full_name
    status_link = f"https://app.thecitytutors.org/request"

    if settings.DRY_RUN:
        print((
            f"Notify: \n"
            f"    Tutor: {tutor.email}, {tutor.profile.nickname}, {tutor.profile.full_name}, {tutor.profile.phone_number.as_e164} \n"
            f"    Tutee: {tutee.email}, {tutee.profile.nickname}, {tutee.profile.full_name}, {tutee.profile.phone_number.as_e164} "
        ))
        return

    body = (
        f"The City Tutors has matched you with a tutor: {tutor.profile.full_name or tutor.profile.nickname}. "
        f"Please check {status_link} to confirm"
    )
    if tutee.profile.sms_notifications:
        send_sms(tutee, body)

    # Notify tutor and tutee via email
    time_between = match_result.meeting.scheduled_start - TutorRequest.objects.get(meeting=match_result.meeting, user=tutee).timestamp

    email_context = ({
        'tutor_name': tutor.profile.nickname or tutor.profile.full_name,
        'tutee_name': tutee.profile.nickname or tutee.profile.full_name,
        'parent_name': parent_name,
        'subject': request.subject.display,
        "status_link": status_link,
    })

    tutee_text_content = render_to_string('tutor/email_match_tutee.txt', email_context)
    tutee_html_content = render_to_string('tutor/email_match_tutee.html', email_context)
    parent_text_content = render_to_string('tutor/email_match_parent.txt', email_context)
    parent_html_content = render_to_string('tutor/email_match_parent.html', email_context)

    if check_valid_email(tutee.email):
        if tutee.profile.sector.display == "Elementary School" or tutee.profile.sector.display == "Middle School" or tutee.profile.sector.display == "High School":
            send_emails(
                user_emails=[tutee.email],
                text_content=parent_text_content,
                html_content=parent_html_content,
                subject="A Tutoring Session Has Been Scheduled, Confirmation Needed",
            )
        else:
            send_emails(
                user_emails=[tutee.email],
                text_content=tutee_text_content,
                html_content=tutee_html_content,
                subject="A Tutoring Session Has Been Scheduled, Confirmation Needed",
            )


def check_valid_email(email):
    regex = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"

    return bool(re.fullmatch(regex, email))


def notify_member_cancellation(active_members, call_source=None):
    logger.info(f"notify_member_cancellation CALLED ({call_source}), {list(active_members.values_list('pk', flat=True))}")
    # Send SMS
    body=(
        f"Your meeting has been cancelled because the other members have cancelled their attendance.  "
        f"Please check to view your meetings."
    )

    for user in active_members:
        if user.profile.sms_notifications:
            send_sms(user, body, call_source=call_source)

    # Send email
    email_context = ({ })

    text_content = render_to_string('tutor/email_cancel_member.txt', email_context)
    html_content = render_to_string('tutor/email_cancel_member.html', email_context)

    send_emails(
        user_emails=list(active_members.filter(profile__email_notifications=True).values_list('email', flat=True)),
        text_content=text_content,
        html_content=html_content,
        subject="Your Meeting Has Been Cancelled",
        call_source=call_source,
    )
    logger.info(f"notify_member_cancellation ({call_source}) COMPLETE")


def notify_auto_cancellations(users, call_source=None):
    logger.info(f"notify_auto_cancellations ({call_source}) CALLED")
    body=(
        f"Your meeting attendance has been cancelled because you did not confirm your attendance.  "
        f"Please check https://app.thecitytutors.org/request to view and create requests."
    )
    for user in users:
        # Send SMS
        if user.profile.sms_notifications:
            send_sms(user, body)

    # Send emails
    email_context = ({ })
    text_content = render_to_string('tutor/email_cancel_auto.txt', email_context)
    html_content = render_to_string('tutor/email_cancel_auto.html', email_context)

    send_emails(
        user_emails=list(users.filter(profile__email_notifications=True).values_list('email', flat=True)),
        text_content=text_content,
        html_content=html_content,
        subject="Your Meeting Attendance Has Been Cancelled",
        call_source=call_source,
    )
    logger.info(f"notify_auto_cancellations ({call_source}) COMPLETE")


def notify_tutee_repeat_scheduled(users, subject, tutor):
    logger.info(f"notify_tutee_repeat_scheduled function called")
    body=(
        f"A repeat session has been scheduled for next week.  "
        f"Please check https://app.thecitytutors.org/request to view.  "
    )

    for user in users:
        # Send SMS
        if user.profile.sms_notifications:
            send_sms(user, body)

        # Send email
        email_context = ({
            'tutor_name': tutor.profile.nickname or tutor.profile.full_name,
            'tutee_name': user.profile.nickname or user.profile.full_name,
            'parent_name': user.profile.parent_or_guardian_name or user.profile.nickname or user.profile.full_name,
            'subject': subject.display,
        })
        
        if user.profile.sector.display == "Elementary School" or user.profile.sector.display == "Middle School" or user.profile.sector.display == "High School":
            text_content = render_to_string('tutor/email_repeat_parent.txt', email_context)
            html_content = render_to_string('tutor/email_repeat_parent.html', email_context)

            send_emails(
                user_emails=[user.email],
                text_content=text_content,
                html_content=html_content,
                subject="Repeat Sesssion Scheduled",
            )
        else:
            text_content = render_to_string('tutor/email_repeat_tutee.txt', email_context)
            html_content = render_to_string('tutor/email_repeat_tutee.txt', email_context)

            send_emails(
                user_emails=[user.email],
                text_content=text_content,
                html_content=html_content,
                subject="Repeat Sesssion Scheduled",
            )

def notify_tutor_repeat_scheduled(tutor):
    logger.info(f"notify_tutor_repeat_scheduled function called")
    body=(
        f"A student has requested a repeat session.  "
        f"Please confirm at https://app.thecitytutors.org/manage.  "
    )

    email_context = ({
        'tutor_name': tutor.profile.nickname or tutor.profile.full_name,
    })

    text_content = render_to_string('tutor/email_repeat_tutor.txt', email_context)
    html_content = render_to_string('tutor/email_repeat_tutor.html', email_context)


    send_emails(
        user_emails=[tutor.email],
        text_content=text_content,
        html_content=html_content,
        subject="Repeat Sesssion Scheduled",
    )


def notify_tutee_site_update_request(tutee):
    logger.info(f"notify_tutee_site_update_request function called")
    body=(
        f"A site program coordinator has updated your request for tutoring.  "
        f"View at https://app.thecitytutors.org/manage.  "
    )

    email_context = ({
        
    })

    text_content = render_to_string('tutor/email_site_update_request.txt', email_context)
    html_content = render_to_string('tutor/email_site_update_request.html', email_context)


    send_emails(
        user_emails=[tutee.email],
        text_content=text_content,
        html_content=html_content,
        subject="Program Coordinator Has Updated Your Request",
    )


def notify_tutee_site_confirm_membership(tutee):
    logger.info(f"notify_tutee_site_confirm_membership function called")
    body=(
        f"A site program coordinator has confirmed an upcoming tutoring session for you.  "
        f"View at https://app.thecitytutors.org/manage.  "
    )

    email_context = ({
    })

    text_content = render_to_string('tutor/email_site_confirm_meeting.txt', email_context)
    html_content = render_to_string('tutor/email_site_confirm_meeting.html', email_context)


    send_emails(
        user_emails=[tutee.email],
        text_content=text_content,
        html_content=html_content,
        subject="Program Coordinator Has Confirmed Your Upcoming Session",
    )


def notify_tutee_site_cancel_membership(tutee):
    logger.info(f"notify_tutee_site_cancel_membership function called")
    body=(
        f"A site program coordinator has cancelled a meeting for you.  "
        f"View at https://app.thecitytutors.org/manage.  "
    )

    email_context = ({
    })

    text_content = render_to_string('tutor/email_site_cancel_meeting.txt', email_context)
    html_content = render_to_string('tutor/email_site_cancel_meeting.html', email_context)

    send_emails(
        user_emails=[tutee.email],
        text_content=text_content,
        html_content=html_content,
        subject="Program Coordinator Has Cancelled a Meeting",
    )


def notify_tutee_site_cancel_request(tutee):
    logger.info(f"notify_tutee_site_cancel_request function called")
    body=(
        f"A site program coordinator has cancelled a request for you.  "
        f"Submit a new request at https://app.thecitytutors.org/manage.  "
    )

    email_context = ({  
    })

    text_content = render_to_string('tutor/email_site_cancel_request.txt', email_context)
    html_content = render_to_string('tutor/email_site_cancel_request.html', email_context)


    send_emails(
        user_emails=[tutee.email],
        text_content=text_content,
        html_content=html_content,
        subject="Program Coordinator Has Cancelled Your Request",
    )


def notify_tutee_site_create_request(tutee):
    logger.info(f"notify_tutee_site_create_request function called")
    body=(
        f"A site program coordinator has created a request for you.  "
        f"View at https://app.thecitytutors.org/manage.  "
    )

    email_context = ({
    })

    text_content = render_to_string('tutor/email_site_new_request.txt', email_context)
    html_content = render_to_string('tutor/email_site_new_request.html', email_context)


    send_emails(
        user_emails=[tutee.email],
        text_content=text_content,
        html_content=html_content,
        subject="Program Coordinator Has Created A Tutor Request",
    )
