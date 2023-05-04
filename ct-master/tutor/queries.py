import datetime as dt
import logging

from django.contrib.auth import get_user_model
from django.db.models import Q, F, Count, Subquery, OuterRef, IntegerField, Prefetch, Case, When, Value, ExpressionWrapper, fields
from django.utils import timezone

from .models import *

User = get_user_model()

logger = logging.getLogger("django")


def get_site_users_annotated(users):
    logger.info(f"get_site_users_annotated function called")
    annotated_users = users.filter(profile__account_type__display__in=[
        "K-12-Tutee",
        "College-Tutee",
        "Adult-Tutee",
    ]).annotate(
        name=Case(
            When(profile__full_name__isnull=False, then='profile__full_name'),
            When(profile__nickname__isnull=False, then='profile__nickname'),
            default=('username')
        ),
        num_scheduled_meetings=Count(
            "meeting",
            filter=Q(meeting__active=True, meeting__scheduled_start__gt=timezone.now()),
            distinct=True,
        ),
        num_past_meetings=Count(
            "meeting",
            filter=Q(meeting__active=True, meeting__scheduled_start__lt=timezone.now()),
            distinct=True,
        ),
        num_unfulfilled_requests=Count(
            "tutorrequest",
            filter=Q(tutorrequest__active=True, tutorrequest__meeting__isnull=True),
            distinct=True,
        ),
        num_fulfilled_requests=Count(
            "tutorrequest",
            filter=(
                Q(tutorrequest__active=True, tutorrequest__meeting__isnull=False) |
                Q(tutorrequest__meeting__isnull=False, tutorrequest__meeting__active=True)
            ),
            distinct=True,
        ),
        status=Case(
            When(
                Q(
                    num_past_meetings=0,
                    num_scheduled_meetings=0,
                    num_unfulfilled_requests=0,
                    num_fulfilled_requests=0,
                ),
                then=Value("No requests or meetings")),
            When(
                Q(
                    num_past_meetings=0,
                    num_scheduled_meetings=0,
                    num_unfulfilled_requests__gt=0,
                    num_fulfilled_requests=0,
                ),
                then=Value("No meetings yet. Requests unfulfilled")
            ),
            When(
                Q(
                    num_unfulfilled_requests=0,
                ),
                then=Value("All requests fulfilled")
            ),
            When(
                Q(
                    num_past_meetings__gt=0,
                    num_unfulfilled_requests__gt=0,
                ),
                then=Value("Attended meetings. Some requests unfulfilled")
            ),
            default=Value("Other")

        )
    ).distinct().order_by('status')
    return annotated_users


def get_site_meetings(users):
    logger.info(f"get_site_meetings function called")
    duration = ExpressionWrapper(F('stop_datetime') - F('start_datetime'), output_field=fields.DurationField())

    meetings = (Meeting.objects
        .filter(meetingmembership__user__in=users, active=True)
        .annotate(
            duration=duration,
            num_students=Count(
                "meetingmembership",
                filter=Q(meetingmembership__user_role="Tutee")
            )
        )
        .filter(duration__lt=dt.timedelta(hours=2.5))
        .prefetch_related(Prefetch(
            "members",
            queryset=users,
            to_attr='students'
        ))
        .prefetch_related(Prefetch(
            "members",
            queryset=User.objects.filter(profile__account_type__display="Tutor"),
            to_attr='tutors'
        ))
        .prefetch_related(Prefetch(
            "assessment",
            queryset=TuteeAssessment.objects.filter(tutee__in=users),
            to_attr='assessments'
        ))
        .distinct().order_by('-scheduled_start')
    )
    return meetings


def get_site_requests(users):
    logger.info(f"get_site_requests function called")
    students = users.filter(profile__account_type__display__in=[
        "K-12-Tutee",
        "College-Tutee",
        "Adult-Tutee",
    ])
    
    tutor_requests = TutorRequest.objects.filter(
        Q(user__in=students) &
        (
            Q(active=True) | 
            Q(meeting__isnull=False, meeting__active=True)
        )
    ).order_by('meeting__scheduled_start') 


    # Could potentially do it this way, just couldn't figure out how to get the 'meeting.scheduled_start'
    # upcoming = tutor_requests.filter(meeting.scheduled_start > timezone.now)    
    # no_mtg = tutor_requests.filter(meeting__isnull=True)
    # past = tutor_requests.filter(meeting.scheduled_start < timezone.now)
    # tutor_requests = upcoming | no_mtg | past
    
    pastMeetings = []
    upcomingMeetings = []
    nullMeetings = []
    for entry in tutor_requests:
        if (entry.meeting != None):
            if (entry.meeting.scheduled_start > timezone.now()):
                upcomingMeetings.append(entry)
            else:
                pastMeetings.append(entry)
        else:
            nullMeetings.append(entry)
    
    nullMeetings.extend(pastMeetings)
    upcomingMeetings.extend(nullMeetings)
    
    meetings = []
    for entry in upcomingMeetings:
        meetings.append(entry.id)

    preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(meetings)])
    query = TutorRequest.objects.filter(pk__in=meetings).order_by(preserved)

    return query


def get_site_memberships(users):
    logger.info(f"get_site_memberships function called")
    students = users.filter(profile__account_type__display__in=[
        "K-12-Tutee",
        "College-Tutee",
        "Adult-Tutee",
    ])
    memberships = MeetingMembership.objects.filter(
        user__in=students, meeting__isnull=False, meeting__active=True
    ).order_by("-created_at")
    return memberships


def get_requests_requiring_exit_ticket(user):
    logger.info(f"get_requests_requiring_exit_ticket function called for {user.username}")
    period = dt.timedelta(days=8)

    tutor_requests = user.tutorrequest_set.filter(
        meeting__isnull=False, meeting__scheduled_start__lt=timezone.now()-period,
        exitticket__isnull=True, meeting__active=True,
    ).distinct()

    return tutor_requests


def get_chained_meetings(meeting):
    logger.info(f"get_chained_meetings function called for {meeting}")
    meeting_ids = [meeting.id]

    try:
        previous_meeting = Meeting.objects.get(follow_up_meeting=meeting)
    except Meeting.DoesNotExist:
        previous_meeting = None
    
    while previous_meeting:
        meeting_ids.append(previous_meeting.id)
        try:
            previous_meeting = Meeting.objects.get(follow_up_meeting=previous_meeting)
        except Meeting.DoesNotExist:
            previous_meeting = None

    meetings = Meeting.objects.filter(pk__in=meeting_ids).order_by("scheduled_start").distinct()
    return meetings


def get_unfulfilled_requests(user):
    logger.info(f"get_unfulfilled_requests function called for {user.username}")
    unfulfilled_requests = TutorRequest.objects.filter(
        Q(
            active=True,
            meeting__isnull=True,
            # user__profile__sector__display__in=list(user.profile.offered_sectors.all()),
        ) & ~Q(user__pk__in=user.blocking.distinct().values_list('pk', flat=True))
    ).annotate(
        time_since=ExpressionWrapper(timezone.now()-F("timestamp"), output_field=fields.DurationField()),
        sector_match=Case(
            When(user__profile__sector__display__in=list(user.profile.offered_sectors.all()), then=Value(1)),
            default=Value(0)
        ),
        subject_match=Case(
            When(subject__in=list(user.profile.offered_subjects.all()), then=Value(1)),
            default=Value(0)
        )
    ).order_by("-sector_match", "-subject_match")

    if user.profile.site_location:
        if user.profile.site_location.binding:
            unfulfilled_requests = unfulfilled_requests.filter(
                user__profile__site_location=user.profile.site_location
            )

    return unfulfilled_requests


#Query used to find previous tutors who had meetings
def get_rerequest_tutor(user):


    #Query for Meetings table that has request_user 
    meetings = Meeting.objects.filter(meetingmembership__user_id = user.id, stop_datetime__isnull=False)
    
    #Query for MeetingMembership table to find out all the tutors that were in each Meeting table 
    meetingmemberships = MeetingMembership.objects.filter(meeting__in = meetings, user = user)

    return meetingmemberships
    #Get user_id of tutors in distinct()
