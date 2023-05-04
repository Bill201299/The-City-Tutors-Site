import datetime as dt
from datetime import datetime, timedelta ,date
import logging
import os, shutil

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import F, Q, Count, BooleanField, ExpressionWrapper, DurationField, OuterRef, Subquery
from django.template.loader import render_to_string
from django.utils import timezone
import pytz

from .notifications import send_sms, send_emails, notify_auto_cancellations, notify_member_cancellation
from .models import (
    Profile,
    Meeting,
    MeetingMembership,
    TutorRequest,
)
from .views import cancel_memberships, cancel_request, cancel_requests_by_membership
User = get_user_model()
logger = logging.getLogger("django")


def print_with_timestamp(msg):
    utc = timezone.now()
    ny = pytz.timezone(settings.TIME_ZONE)
    log = f"{utc.astimezone(ny).strftime('%Y-%m-%d %H:%M:%S')}: {msg}"
    logger.info(log)


def test_logging():
    print_with_timestamp("test cron logging")


def print_env():
    print_with_timestamp(
        f"  SEND_TO_USERS={settings.SEND_TO_USERS} \n"
        f"  DRY_RUN={settings.DRY_RUN} \n"
        f"  SKIP_NOTIFY_EMAIL={settings.SKIP_NOTIFY_EMAIL} \n"
        f"  SKIP_NOTIFY_SMS={settings.SKIP_NOTIFY_SMS} \n"
        f"  DEVELOPMENT_NUMBER={settings.DEVELOPMENT_NUMBER} \n"
        f"  RECIPIENT_ADDRESS={settings.RECIPIENT_ADDRESS} \n"
        f"  TWILIO_ACCOUNT_SID={settings.TWILIO_ACCOUNT_SID} \n"
        f"  TWILIO_AUTH_TOKEN={settings.TWILIO_AUTH_TOKEN} \n"
        f"  TWILIO_NUMBER={settings.TWILIO_NUMBER} \n"
        f"  EMAIL_HOST={settings.EMAIL_HOST} \n"
        f"  EMAIL_HOST_USER={settings.EMAIL_HOST_USER} \n"
        f"  EMAIL_HOST_PASSWORD={settings.EMAIL_HOST_PASSWORD} \n"
        f"  REPLYTO_ADDRESS={settings.REPLYTO_ADDRESS} "
    )


def notify_inactive_tutors():
    # Follow up with tutors who haven't logged in for 7 days
    available_tutors_profile = Profile.available_tutors.all()

    users = User.objects.filter(
        profile__in=available_tutors_profile,
        last_login__lte=timezone.now()-dt.timedelta(days=7),    # login < 7 days ago        8 days ago < login < 7 days ago
        last_login__gt=timezone.now()-dt.timedelta(days=8),     # login > 8 days ago
    )
    # print(
    #     f"notify_inactive_tutors \n"
    #     f"    SKIP_NOTIFY_EMAIL={settings.SKIP_NOTIFY_EMAIL} \n"
    #     f"    SKIP_NOTIFY_SMS={settings.SKIP_NOTIFY_SMS} \n"
    #     f"    SEND_TO_USERS: {settings.SEND_TO_USERS} \n"
    #     f"    {timezone.localtime()-dt.timedelta(days=8)} < Login < {timezone.localtime()-dt.timedelta(days=7)} \n"
    #     f"    {users}"
    # )

    body=(
        f"We recently sent an email following up about tutoring with us.  "
        f"Are you still able to continue?  "
        f"Please check https://app.thecitytutors.org/profile to view or change your preferences"
    )

    for user in users:
        send_sms(user, body)

        # print(f"[{timezone.now()}] Notify Inactive Tutors - SENT SMS")

        email_context = ({
            'tutor_name': user.profile.nickname or user.profile.full_name,
        })

        tutor_text_content = render_to_string('tutor/email_inactive_tutor.txt', email_context)
        tutor_html_content = render_to_string('tutor/email_inactive_tutor.html', email_context)
        
        send_emails(
            user_emails=[user.email],
            text_content=tutor_text_content,
            html_content=tutor_html_content,
            subject="Still Volunteering With Us?"
        )


def notify_session_start():
    print_with_timestamp("notify_session_start CALLED")
    # Notify meeting members 15 minutes before session start
    meetings = Meeting.objects.filter(
        active=True,
        scheduled_start__gte=timezone.now()+dt.timedelta(minutes=15),   # start >= now + 15      now + 15 <= start < now + 30
        scheduled_start__lt=timezone.now()+dt.timedelta(minutes=30),    # start < now + 30
        start_datetime__isnull=True,
    )

    # {timezone.localtime()+dt.timedelta(minutes=15)} < Scheduled Start < {timezone.localtime()+dt.timedelta(minutes=30)}"

    tutors = User.objects.filter(
        Q(membership__meeting__in=meetings, membership__user_role="Tutor") &
        ~Q(membership__status="Cancelled")
    )
    tutees = User.objects.filter(
        membership__meeting__in=meetings,
        membership__user_role="Tutee",
        membership__status="Confirmed"
    )
    print_with_timestamp(f"notify_session_start: {len(tutors)} tutors, {len(tutees)} tutees queried to notify")

    # Notify tutor and tutee via sms
    if tutees:
        body=(
            f"Your tutoring session begins soon.  "
            f"Please check https://app.thecitytutors.org/request to view details"
        )
        for tutee in tutees:
            send_sms(tutee, body)

    if tutors:
        body=(
            f"Your tutoring session begins soon.  "
            f"Please clock in at https://app.thecitytutors.org/clock when you begin the session"
        )
        for tutor in tutors:
            send_sms(tutor, body)

    # Notify tutor and tutee via email
    email_context = {}

    tutor_text_content = render_to_string('tutor/email_sessionstart_tutor.txt', email_context)
    tutor_html_content = render_to_string('tutor/email_sessionstart_tutor.html', email_context)
    tutee_text_content = render_to_string('tutor/email_sessionstart_tutee.txt', email_context)
    tutee_html_content = render_to_string('tutor/email_sessionstart_tutee.html', email_context)
    parent_text_content = render_to_string('tutor/email_sessionstart_parent.txt', email_context)
    parent_html_content = render_to_string('tutor/email_sessionstart_parent.html', email_context)

    if tutors:
        send_emails(
            user_emails=list(tutors.filter(profile__email_notifications=True).values_list('email', flat=True)),
            text_content=tutor_text_content,
            html_content=tutor_html_content,
            subject="Tutoring Session Begins Soon"
        )

    tutees_parent = tutees.filter(Q(profile__sector__display="Elementary School") | Q(profile__sector__display="Middle School"))
    tutees_self = tutees.filter(~Q(profile__sector__display="Elementary School") & ~Q(profile__sector__display="Middle School"))

    if tutees_self:
        send_emails(
            user_emails=list(tutees_self.filter(profile__email_notifications=True).values_list('email', flat=True)),
            subject="Tutoring Session Begins Soon",
            text_content=tutee_text_content,
            html_content=tutee_html_content,
        )

    if tutees_parent:
        send_emails(
            user_emails=list(tutees_parent.filter(profile__email_notifications=True).values_list('email', flat=True)),
            subject="Tutoring Session Begins Soon",
            text_content=parent_text_content,
            html_content=parent_html_content,
        )
    print_with_timestamp("notify_session_start COMPLETE")


def notify_late_session():
    print_with_timestamp("notify_late_session CALLED")

    # Notify tutor if they have not clocked in 15 minutes after session was supposed to start
    meetings = Meeting.objects.filter(
        scheduled_start__lte=timezone.now()-dt.timedelta(minutes=15),   # start <= now - 15      now - 30 < start < now - 15
        scheduled_start__gt=timezone.now()-dt.timedelta(minutes=30),    # start > now - 30
        start_datetime__isnull=True,
        active=True
    )

    tutors = User.objects.filter(
        Q(membership__meeting__in=meetings, membership__user_role="Tutor") &
        ~Q(membership__status="Cancelled")
    )

    print_with_timestamp(f"Notify late session: {len(tutors)} tutors queried to notify")

    if tutors:
        body=(
            f"Did you forget to clock in to your tutoring session?  "
            f"Please clock in at https://app.thecitytutors.org/clock."
        )
        for tutor in tutors:
            send_sms(tutor, body)

        # print(f"[{timezone.now()}] Notify Late Session - SENT SMS")

        email_context = ({
            'tutor_name': 'tutor',
        })

        tutor_text_content = render_to_string('tutor/email_sessionlate_tutor.txt', email_context)
        tutor_html_content = render_to_string('tutor/email_sessionlate_tutor.html', email_context)

        send_emails(
            user_emails=list(tutors.filter(profile__email_notifications=True).values_list('email', flat=True)),
            text_content=tutor_text_content,
            html_content=tutor_html_content,
            subject="Please Clock In",
        )
    print_with_timestamp("notify_late_session COMPLETE")


def notify_exit_ticket():
    # Notify student if they have not completed an exit ticket that was due x days ago
    pass


def query_unconfirmed_students(notify=False):
    tutee_memberships = MeetingMembership.objects.filter(
        status="Pending Confirmation",
        meeting__active=True,
        user_role="Tutee",
        created_at__lte=timezone.now()-dt.timedelta(hours=48)
    ).distinct()

    if notify:
        tutee_memberships = tutee_memberships.filter(meeting__scheduled_start__gte=timezone.now())
    
    return tutee_memberships


def cancel_unconfirmed_students():
    try:
        print_with_timestamp("cancel_unconfirmed_students CALLED")
        memberships = query_unconfirmed_students()

        if memberships:
            print_with_timestamp(f"cancel_unconfirmed_students: {len(memberships)} memberships queried to cancel {list(memberships.values_list('pk', flat=True))}")
            cancel_requests_by_membership(memberships, reason="Unconfirmed", call_source='cancel_unconfirmed_students')

            users_to_notify = User.objects.filter(membership__in=list(query_unconfirmed_students(notify=True)))

            if users_to_notify:
                print_with_timestamp(f"cancel_unconfirmed_students: {len(users_to_notify)} users will be notified")
                notify_auto_cancellations(users_to_notify, call_source="cancel_unconfirmed_students")
                print_with_timestamp(f"cancel_unconfirmed_students: notified students of auto cancellation")
        else:
            print_with_timestamp(f"cancel_unconfirmed_students: no student MeetingMemberships to cancel")

        print_with_timestamp("cancel_unconfirmed_students COMPLETE")
    except Exception as e:
        print_with_timestamp(e)


def query_unconfirmed_tutors(notify=False):
    tutor_memberships = MeetingMembership.objects.filter(
        status="Pending Confirmation",
        meeting__active=True,
        user_role="Tutor",
        created_at__lte=timezone.now()-dt.timedelta(hours=72),
    ).distinct()

    if notify:
        tutor_memberships = tutor_memberships.filter(meeting__scheduled_start__gte=timezone.now())
    
    return tutor_memberships


def cancel_unconfirmed_tutors():
    try:
        print_with_timestamp("cancel_unconfirmed_tutors CALLED")

        tutor_memberships = query_unconfirmed_tutors()
        
        if tutor_memberships:
            copy_database()
            print_with_timestamp(f"cancel_unconfirmed_tutors: {len(tutor_memberships)} tutor_memberships queried to cancel {list(tutor_memberships.values_list('pk', flat=True))}")
            cancel_memberships(tutor_memberships, reason="Unconfirmed", call_source="cancel_unconfirmed_tutors")
        
            users_to_notify = User.objects.filter(membership__in=list(query_unconfirmed_tutors(notify=True)))

            if users_to_notify:
                print_with_timestamp(f"cancel_unconfirmed_tutors: {len(users_to_notify)} users will be notified")
                notify_auto_cancellations(users_to_notify, call_source=" cancel_unconfirmed_tutors")
                print_with_timestamp(f"cancel_unconfirmed_tutors: notified tutors of auto cancellation")

        else:
            print_with_timestamp(f"cancel_unconfirmed_tutors: no tutor MeetingMemberships to cancel")

        print_with_timestamp("cancel_unconfirmed_tutors COMPLETE")
    except Exception as e:
        print_with_timestamp(e)


def notify_unconfirmed():
    '''
    Make sure the notification doesn't go twice
    Send final reminder 1 hour before cancellation????
    '''
    pass

""" def automatic_clockout():
    
    tutor_meetings = Meeting.objects.filter(
        stop_datetime__isnull = True,
        start_datetime__lt = timezone.now() - timedelta(hours = 2)
    )

    print("testing...")
    print("total number of meetings: ")
    print(tutor_meetings.count())
    print("current time: ")
    print(timezone.now())
    print(" ")

    for meetings in tutor_meetings:
        meetings.stop_datetime = meetings.start_datetime + timedelta(hours = 1)
        meetings.save()
        print("saved stop_datetime")
        print(meetings.stop_datetime)
        print(" ") """


def copy_database():
    if settings.COPY_DB:
        BASE_DIR = settings.BASE_DIR
        src = os.path.join(BASE_DIR, "db.sqlite3")
        dst = os.path.join(BASE_DIR, 'databases')
        shutil.copyfile(src, dst + '/' + timezone.now().astimezone(pytz.timezone('America/New_York')).strftime("%Y-%m-%d %H%M"))
        print_with_timestamp('Copied database')
