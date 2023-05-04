import dataclasses
import datetime
import logging

from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Q, Count, BooleanField, ExpressionWrapper
from typing import Optional

from .models import Meeting, TutorRequest, MeetingMembership, TimeSlot, TutorOfferedMonthlyHours, Profile
from .notifications import notify_match

logger = logging.getLogger("django")
User = get_user_model()

def get_user_profile(user):
    try:
        return user.profile
    except User.profile.RelatedObjectDoesNotExist:
        return None


@dataclasses.dataclass
class MatchResult:
    tutee: object
    tutor: object
    request: object
    meeting: object


def tutee_tutor_block(tutee, tutor):
    logger.info(f"tutee_tutor_block function called")
    # If tutor and tutee have at least two cancelled meetings (by either party)
    # in the past two weeks, then don't match them
    tutee_tutor_meetings = ((tutor.meeting_set.all() & tutee.meeting_set.all()).filter(
        active=False,
        scheduled_start__gte=timezone.now()-datetime.timedelta(days=14),
    ))
    tutor_cancelled_memberships = MeetingMembership.objects.filter(
        user=tutor,
        meeting__in=tutee_tutor_meetings,
        status="Cancelled"
    )
    tutee_cancelled_memberships = MeetingMembership.objects.filter(
        user=tutee,
        meeting__in=tutee_tutor_meetings,
        status="Cancelled"
    )
    implicit_block = len(tutor_cancelled_memberships) + len(tutee_cancelled_memberships) >=2
    explicit_block = tutee in tutor.profile.block.all() or tutor in tutee.profile.block.all()

    if implicit_block or explicit_block:
        print(f"Block {tutee}, {tutor}")
    return implicit_block or explicit_block


def match_tutee_by_creating_new_meeting(request) -> Optional[MatchResult]:
    logger.info(f"match_tutee_by_creating_new_meeting function called")
    tutee = request.user
    tutee_profile = get_user_profile(tutee)
    if tutee_profile is None:
        return None
    current_time_slot = TimeSlot.for_current_time()

    tutee_scheduled_meetings = tutee.meeting_set.filter(scheduled_start__gt=timezone.now(), active=True)
    tutee_availabilities = set(tutee_profile.available.all())
    tutee_scheduled_time_slots = set(meeting.scheduled_time_slot for meeting in tutee_scheduled_meetings)
    tutee_cancelled_times = list(tutee.meeting_set
        .filter(
            meetingmembership__status="Cancelled",
            scheduled_start__gt=timezone.now()-datetime.timedelta(days=14))
        .values_list("scheduled_start", flat=True)
    )

    tutor_profiles = Profile.available_tutors.all()
    tutors = User.objects.filter(profile__in=tutor_profiles)

    tutors = (tutors
        .prefetch_related("profile")
        .annotate(num_meetings=Count("meeting", filter=Q(meeting__active=True)))
        .order_by("num_meetings")
    )
    for tutor in tutors:
        # print(f"Trying to match {tutee=}, {tutor=}")
        tutor_profile = get_user_profile(tutor)
        if tutor_profile is None:
            continue

        if tutor_profile.site_location:
            if tutor_profile.site_location.binding and (tutor_profile.site_location != tutee_profile.site_location):
                continue
        
        tutor_scheduled_meetings = tutor.meeting_set.filter(scheduled_start__gt=timezone.now(), active=True)
        tutor_sectors = set(tutor_profile.offered_sectors.all())
        tutor_availabilities = list(tutor_profile.available
            .annotate(this_week=ExpressionWrapper(Q(id__gt=current_time_slot.id+96), output_field=BooleanField()))
            .order_by("-this_week"))
        tutor_scheduled_time_slots = set(meeting.scheduled_time_slot for meeting in tutor_scheduled_meetings)
        tutor_offered_subjects = set(tutor_profile.offered_subjects.all())

        if tutor_profile.tutor_monthly_volunteer:
            tutor_remaining_hours = tutor.profile.hours_left_current_month
        else:
            tutor_remaining_hours = tutor.profile.hours_left_current_week
        
        tutor_cancelled_times = list(tutor.meeting_set
            .filter(meetingmembership__status="Cancelled")
            .values_list("scheduled_start", flat=True)
        )

        if tutor.profile.tutor_training_stage == "not-finished":
            continue
        if tutor_remaining_hours <= 0:
            continue
        if tutee_profile.sector not in tutor_sectors:
            continue
        if request.subject not in tutor_offered_subjects:
            continue

        if tutee_tutor_block(tutee, tutor):
            continue

        for available_time in tutor_availabilities:
            if available_time not in tutee_availabilities:
                continue
            elif available_time not in tutor_availabilities:
                continue
            elif available_time in tutee_scheduled_time_slots:
                continue
            elif available_time in tutor_scheduled_time_slots:
                continue
            elif available_time.next_datetime() in tutee_cancelled_times:
                continue
            elif available_time.next_datetime() in tutor_cancelled_times:
                continue
            else:
                break
        else: # No break = No available time
            continue

        print((
            f"New meeting: \n"
            f"    Tutee: {tutee} \n"
            f"    Tutor: {tutor} \n"
            f"    Subject: {request.subject} \n"
            f"    Scheduled time slot: {available_time} \n"
            f"    Scheduled start: {available_time.next_datetime()} "
        ))
        if settings.DRY_RUN:
            meeting = Meeting(
                subject=request.subject,
                scheduled_time_slot=available_time,
                scheduled_start=available_time.next_datetime(),
            )
        else:
            # Create a new meeting
            meeting = Meeting.objects.create(
                subject=request.subject,
                scheduled_time_slot=available_time,
                scheduled_start=available_time.next_datetime(),
            )
            MeetingMembership(user=tutee, user_role="Tutee", meeting=meeting).save()
            MeetingMembership(user=tutor, user_role="Tutor", meeting=meeting).save()
            request.meeting = meeting
            request.save()
        return MatchResult(tutee=tutee, tutor=tutor, request=request, meeting=meeting)


def match_tutee_by_joining_study_group(request) -> Optional[MatchResult]:
    logger.info(f"match_tutee_by_joining_study_group function called")
    tutee = request.user
    tutee_profile = get_user_profile(tutee)
    if tutee_profile is None:
        return None

    tutee_scheduled_meetings = tutee.meeting_set.filter(
        scheduled_start__gt=timezone.now(),
        active=True,
    )
    tutee_availabilities = set(tutee_profile.available.all())
    tutee_scheduled_time_slots = set(meeting.scheduled_time_slot for meeting in tutee_scheduled_meetings)
    
    meetings = Meeting.objects.annotate(
        num_students=Count(
            'meetingmembership',
            filter=Q(meetingmembership__user_role='Tutee') & ~Q(meetingmembership__status='Cancelled')
        )
    ).filter(
        scheduled_start__gt=timezone.now(),
        subject=request.subject,
        num_students__lt=4,
        scheduled_time_slot__in=tutee_availabilities,
        created_at__gte=timezone.now()-datetime.timedelta(hours=48)
    ).exclude(
        meetingmembership__user=tutee
    ).exclude(
        scheduled_time_slot__in=tutee_scheduled_time_slots
    ).exclude(
        meetingmembership__user__profile__site_location__binding=True
    ).order_by("num_students")
    
    meeting = None
    for potential_meeting in meetings:
        tutor = potential_meeting.meetingmembership_set.get(user_role="Tutor").user
        if tutee_tutor_block(tutee, tutor):
            continue
        else:
            meeting = potential_meeting
            break
    if meeting is None:
        # No group found
        return None

    tutor = MeetingMembership.objects.filter(meeting=meeting, user_role="Tutor").first().user

    print((
        f"Add to meeting: \n"
        f"    Tutee: {tutee} \n"
        f"    Tutor: {tutor} \n"
        f"    Subject: {meeting.subject} \n"
        f"    Scheduled time slot: {meeting.scheduled_time_slot} \n"
        f"    Scheduled start: {meeting.scheduled_start} "
    ))

    if not settings.DRY_RUN:
        request.meeting = meeting
        MeetingMembership(user=tutee, user_role="Tutee", meeting=meeting).save()
        request.save()

    return MatchResult(tutee=tutee, tutor=tutor, request=request, meeting=meeting)


def fulfill_requests():
    from .cron import print_with_timestamp
    print_with_timestamp("Cronjob called: fulfill_requests")
    # print((
    #     f"Settings and vars: \n"
    #     f"    SEND_TO_USERS: {settings.SEND_TO_USERS} \n"
    #     f"    DRY_RUN: {settings.DRY_RUN} \n"
    #     f"    SKIP_NOTIFY_EMAIL={settings.SKIP_NOTIFY_EMAIL} \n"
    #     f"    SKIP_NOTIFY_SMS={settings.SKIP_NOTIFY_SMS} \n"
    #     f"    EMAIL_HOST_USER: {settings.EMAIL_HOST_USER} \n"
    #     f"    TWILIO_ACCOUNT_SID: {settings.TWILIO_ACCOUNT_SID} \n"
    #     f"    TWILIO_AUTH_TOKEN: {settings.TWILIO_AUTH_TOKEN} \n"
    #     f"    TWILIO_NUMBER: {settings.TWILIO_NUMBER} \n"
    #     f"    REPLYTO_ADDRESS: {settings.REPLYTO_ADDRESS} "
    # ))

    requests = TutorRequest.objects.filter(active=True, meeting=None).order_by("timestamp")
    print(f"{len(requests)} request(s)")
    for request in requests:
        tutee = request.user
        print(f"\nSTUDENT: {tutee}")

        tutee_cancelled_times = list(tutee.meeting_set
            .filter(
                meetingmembership__status="Cancelled",
                scheduled_start__gt=timezone.now()-datetime.timedelta(days=14))
            .values_list("scheduled_start", flat=True)
        )
        # If tutee has cancelled (intentionally or automatically) at least 5 times in the past 2 weeks
        # don't match them (temporary block)
        if len(tutee_cancelled_times) >= 5:
            print(f"Temporary block for {tutee}")
            continue

        # First attempt a 1:1 match
        if True:
            match_result = match_tutee_by_creating_new_meeting(request=request)
            if match_result is not None:
                print((
                    f"Individual match found: \n"
                    f"    Tutee: {tutee} \n"
                    f"    Subject: {request.subject} "
                ))
                notify_match(match_result)
                continue
        # Next, if allowed, attempt to add to a study group
        if request.subject.group_sessions:
            match_result = match_tutee_by_joining_study_group(request=request)
            if match_result is not None:
                print((
                    f"Group match found: \n"
                    f"    Tutee: {tutee} \n"
                    f"    Subject: {request.subject} "
                ))
                notify_match(match_result)
                continue
            else:
                print((
                    f"No individual or group match found: \n"
                    f"    Tutee: {tutee} \n"
                    f"    Subject: {request.subject} "
                ))
        else:
            print((
                f"No individual match found: \n"
                f"    Tutee: {tutee} \n"
                f"    Subject: {request.subject} "
            ))
    print_with_timestamp("Cronjob complete: fulfill_requests")


def match_by_tutor(tutor, tutor_request, timeslot):
    logger.info(f"match_by_tutor function called")
    tutee = tutor_request.user

    meeting = Meeting.objects.create(
        subject=tutor_request.subject,
        scheduled_time_slot=timeslot,
        scheduled_start=timeslot.next_datetime(),
    )
    logger.info(f"match_by_tutor: created meeting instance (pk:{meeting.pk})")
    MeetingMembership(user=tutee, user_role="Tutee", meeting=meeting).save()
    MeetingMembership(user=tutor, user_role="Tutor", meeting=meeting, status="Confirmed", confirmation_timestamp=timezone.now()).save()
    logger.info("match_by_tutor: created meeting membership instances")
    tutor_request.meeting = meeting
    tutor_request.save()
    logger.info(f"match_by_tutor: attached meeting to tutor request")

    match_result = MatchResult(tutee=tutee, tutor=tutor, request=tutor_request, meeting=meeting)

    notify_match(match_result)
