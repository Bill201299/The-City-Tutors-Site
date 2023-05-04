import csv

from django.contrib.auth import get_user_model
from django.db.models import Q, When, Case, Value
from django.template.loader import render_to_string

from .notifications import send_emails, send_sms_by_number

User = get_user_model()

def send_mass_email():
    emails = []
    with open("active.csv") as f:
        reader = csv.DictReader(f)
        records = list(reader)

    for record in records:
        email = record['Email']
        emails.append(email)

    email_context = ({ })
    
    text_content = render_to_string('tutor/email_current.txt', email_context)
    html_content = render_to_string('tutor/email_current.html', email_context)
    
    # send_emails(
    #     user_emails=emails,
    #     text_content=text_content,
    #     html_content=html_content,
    #     subject="Changes to Online Matching System for Spring 2022",
    # )


def send_mass_text():
    numbers = []
    with open("active.csv") as f:
        reader = csv.DictReader(f)
        records = list(reader)

    for record in records:
        number = record['phone2']
        if len(number) == 10:
            numbers.append(number)

    body = (
        f"Hi, it's Mike from The City Tutors. "
        f"We just sent an email with a link to our new online system. "
        f"When you have 5 minutes, can you fill out the portal for registering as a volunteer? "
        f"I'll include a link here: https://app.thecitytutors.org/tutor-registration"
    )

    # send_sms_by_number(numbers, body)


def create_tutor_training_csv():
    tutors = User.objects.filter(
        profile__account_type__display="Tutor"
    ).annotate(
        training_stage=Case(
            When(orientationtraining__isnull=True, then=Value("orientation")),
            When(tutortraining__isnull=True, then=Value("training_1")),
            When(roleplaytraining__isnull=True, then=Value("training_2")),
            When(~Q(backgroundcheckrequest__status="Approved"), then=Value("background")),
            default=Value("finished")
        )
    ).filter(~Q(training_stage="finished"))

    emails = list(tutors.values_list('email', flat=True))

    header = ['tutor', 'onboarded', 'email', 'training_stage']

    with open('training_stage.csv', 'w', encoding='UTF8') as f:
        writer = csv.writer(f)

        writer.writerow(header)

        for tutor in tutors:
            row = [
                tutor.profile.full_name or tutor.profile.nickname or tutor.username,
                tutor.profile.onboarded,
                tutor.email,
                tutor.training_stage,
            ]
            writer.writerow(row)


def create_tutor_training_and_bg_csv():
    tutors = User.objects.filter(
        profile__account_type__display="Tutor"
    ).annotate(
        training_stage=Case(
            When(orientationtraining__isnull=True, then=Value("orientation")),
            When(tutortraining__isnull=True, then=Value("training_1")),
            When(roleplaytraining__isnull=True, then=Value("training_2")),
            When(~Q(backgroundcheckrequest__status="Approved"), then=Value("background")),
            default=Value("finished")
        )
    ).filter(training_stage="finished", backgroundcheckrequest__status="Approved")

    header = ['tutor', 'email']

    with open('training_bg.csv', 'w', encoding='UTF8') as f:
        writer = csv.writer(f)

        writer.writerow(header)

        for tutor in tutors:
            row = [
                tutor.profile.full_name or tutor.profile.nickname or tutor.username,
                tutor.email,
            ]
            writer.writerow(row)


def create_phone_number_csv():
    users = User.objects.filter(profile__phone_number__isnull=False)
    header = ['user', 'phone number', 'sms_notifications', 'email']

    with open('phone_number.csv', 'w', encoding='UTF8') as f:
        writer = csv.writer(f)

        writer.writerow(header)

        for user in users:
            row = [
                user.profile.full_name or user.profile.nickname or user.username,
                user.profile.phone_number,
                user.profile.sms_notifications,
                user.email,
            ]
            writer.writerow(row)