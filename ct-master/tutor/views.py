import collections
import hashlib
import os
from sre_constants import AT_END
import xlwt, csv, zipfile, tempfile
from io import StringIO, BytesIO
from calendar import day_name, month_name
import datetime as dt
from datetime import datetime, timedelta ,date
import pytz
from functools import partial
import logging
import re

from django.shortcuts import render
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import logout
from django.http import HttpResponse, HttpResponseRedirect, FileResponse, Http404
from django.db import transaction, IntegrityError
from django.db.models import Q, F, Count, Subquery, OuterRef, IntegerField, Prefetch, ExpressionWrapper, fields, Avg, Sum, DurationField, FilteredRelation, When, Case, Sum, Aggregate, CharField, Value, Exists
from django.utils import timezone
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.forms import (
    modelformset_factory,
    modelform_factory,
    ValidationError,
    ModelMultipleChoiceField,
    ValidationError,
)

from django.forms.widgets import DateInput, TimeInput, Textarea, NumberInput
from django.forms import formset_factory
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
from collections import defaultdict

from .zip_code import is_allowed_zip_code
from .notifications import (
    send_emails,
    notify_member_cancellation,
    notify_tutor_meeting,
    notify_tutee_repeat_scheduled,
    notify_tutor_repeat_scheduled,
    notify_tutee_site_update_request,
    notify_tutee_site_confirm_membership,
    notify_tutee_site_cancel_membership,
    notify_tutee_site_cancel_request,
    notify_tutee_site_create_request,
    email_test,
)
from .manual import create_phone_number_csv
from .models import (
    Site,
    Orientation1,
    Orientation2,
    Orientation3,
    Orientation4,
    LiveSession,
    BackgroundCheckRequest,
    Issue,
    TuteeIssue,
    HarassIssue,
    Profile,
    Meeting,
    MeetingMembership,
    TutorRequest,
    AccountType,
    Subject,
    Sector,
    TimeSlot,
    TuteeAssessment,
    Site,
    SiteLocation,
    ExitTicket,
    TutorOfferedMonthlyHours,
    ConnectedStudent
)
from .forms import (
    DirectoryForm,
    CreateInPersonMeetingForm,
    OrientationTrainingForm,
    ConfirmMeetingForm,
    RepeatMeetingForm,
    SpecificCancelMeetingForm,
    TutorTrainingForm,
    RoleplayTrainingForm,
    BackgroundForm,
    StartClockForm,
    StopClockForm,
    MeetingStartClockForm,
    MeetingStopClockForm,
    IssueForm,
    TutorProfileForm,
    TuteeProfileForm,
    TutorRegistrationForm,
    TutorOnboardingForm,
    K12RegistrationForm,
    K12OnboardingForm,
    CollegeRegistrationForm,
    CollegeOnboardingForm,
    AdultRegistrationForm,
    AdultOnboardingForm,
    TutorRequestForm,
    TutorRequestUpdateForm,
    TuteeAssessmentForm,
    CancelMeetingForm,
    UndoForm,
    TuteeIssueForm,
    HarassIssueForm,
    ProgramCoordinatorRegistrationForm,
    ExitTicketEasyForm,
    ExitTicketMediumForm,
    ExitTicketDifficultForm,
    GradeLevelForm,
    TutorMatchConfirmForm,
    LeaveTicketForm,
    SiteMeetingMembershipForm,
    SiteTutorRequestEditForm,
    SiteTutorRequestForm,
    TutorMonthlyHoursForm,
    TutorWeeklyHoursForm,
    TutorHoursTypeForm,
    TutorCurrentMonthlyHours,
    Orientation1Form,
    Orientation1ResultForm,
    Orientation2Form,
    Orientation2ResultForm,
    Orientation3Form,
    Orientation3ResultForm,
    Orientation4Form,
    Orientation4ResultForm,
    Orientation5Form,
    Orientation5ResultForm,
    Orientation6Form,
    Orientation6ResultForm,
    Orientation7Form,
    Orientation7ResultForm,
    Orientation8Form,
    Orientation8ResultForm,
    Orientation9Form,
    Orientation9ResultForm,
    Orientation10Form,
    Orientation10ResultForm,
    Orientation11Form,
    Orientation11ResultForm,
    OrientationLiveSession,
)
from .queries import (
    get_rerequest_tutor,
    get_site_users_annotated,
    get_site_meetings,
    get_site_requests,
    get_site_memberships,
    get_requests_requiring_exit_ticket,
    get_chained_meetings,
    get_unfulfilled_requests,
)
from .match import match_by_tutor
from django.shortcuts import render, redirect
from django.core.mail import send_mail, BadHeaderError
from django.http import HttpResponse
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.db.models.query_utils import Q
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes

User = get_user_model()

form_helper = FormHelper()
form_helper.form_tag = False
logger = logging.getLogger("django")


@login_required
def tutee_portal(request):
    logger.info(f"{request.user.username or request.user} called tutee_portal view")
    return render(
        request=request,
        template_name="tutor/tutee_portal.html",
        context={"user": request.user},
    )


@login_required
def tutor_portal(request):
    logger.info(f"{request.user.username or request.user} called tutor_portal view")
    return render(
        request=request,
        template_name="tutor/tutor_portal.html",
        context={"user": request.user},
    )


@login_required
def clock(request):
    logger.info(f"{request.user.username or request.user} called clock view")
    user = request.user

    memberships = MeetingMembership.objects.filter(Q(user=user) & ~Q(status="Cancelled"))
    meetings = user.meeting_set.filter(
        start_datetime=None,
        stop_datetime=None,
        scheduled_start__gt=timezone.now()-dt.timedelta(days=1),
        tutorrequest__active=True,
        active=True,
        meetingmembership__in=memberships,
    ).order_by("scheduled_start").distinct()

    try:
        open_meetings = user.meeting_set.exclude(start_datetime=None).filter(
            stop_datetime=None,
            meetingmembership__user_role="Tutor"
        ).order_by("scheduled_start").distinct()
        if len(open_meetings) > 1 and "stop_clock" not in request.POST:
            messages.warning(
                request, "You already have an open meeting, please complete it first."
            )
        open_meeting = open_meetings.first()
        if open_meeting is None:
            raise Meeting.DoesNotExist
        start_datetime = (
            timezone.localtime(open_meeting.start_datetime) if open_meeting else None
        )
        members = open_meeting.members.filter(
            ~Q(membership__status="Cancelled") &
            Q(membership__user_role="Tutee")
        )
        stop_clock_form = StopClockForm(
            members=members,
            requests=TutorRequest.objects.filter(meeting=open_meeting),
            initial={
                "date": timezone.localtime().date() if start_datetime else None,
                "stop_date": timezone.localtime().date(),
                "stop_time": timezone.localtime().time(),
            },
        )
        past_meetings = (user.meeting_set
        .filter(~Q(stop_datetime=None) & ~Q(meetingmembership__status="Cancelled"))
        .order_by('-start_datetime')).filter(members__in = members)[:1]
    except Meeting.DoesNotExist:
        open_meeting = None
        stop_clock_form = None
        formset = None
        members = None
        past_meetings = None

    unfinished_assessments = TuteeAssessment.objects.filter(
        meeting__meetingmembership__user_id=user.id,
        meeting__stop_datetime__isnull=False,
        assessment=None
    )
    if unfinished_assessments:
        assessment_meetings = Meeting.objects.filter(assessment__in=unfinished_assessments)
        if len(assessment_meetings) > 1 and "stop_clock" not in request.POST:
            messages.warning(
                request, "You have unfinished student assessments, please complete them first."
            )
        assessment_meeting = assessment_meetings.first()
        logger.info(f"{request.user.username or request.user} redirected to clock assessments from clock")
        return HttpResponseRedirect(reverse(
            "tutor:clock_assessment",
            kwargs={"meeting_id": assessment_meeting.id},
        ))

    #Find which meeting membership should be rated
    unrated_meetings = MeetingMembership.objects.filter(
        rate=None, meeting__stop_datetime__isnull=False,
        rated=False,
        user = request.user
    )

    if unrated_meetings:
        unrated_meeting = unrated_meetings.first()
        return HttpResponseRedirect(reverse(
            "tutor:clock_rate",
            kwargs={"unrated_meeting_id":unrated_meeting.id},
        ))

    start_clock_form = StartClockForm(request.POST or None, meetings=meetings)

    if "start_clock" in request.POST:
        logger.info(f"{request.user.username or request.user} submitted a start_clock POST request to clock")
        if start_clock_form.is_valid():
            meeting = start_clock_form.cleaned_data["meeting"]
            start_clock(meeting, request)
            logger.info(f"{request.user.username or request.user} clocked in")
        return HttpResponseRedirect(request.path_info)
    if "stop_clock" in request.POST:
        logger.info(f"{request.user.username or request.user} submitted a stop_clock POST request to clock")
        if not stop_clock_form:
            return HttpResponseRedirect(request.path_info)
        stop_clock_form = StopClockForm(request.POST, members=members,requests=TutorRequest.objects.filter(meeting=open_meeting))

        if stop_clock_form.is_valid():
            with transaction.atomic():
                date = stop_clock_form.cleaned_data["date"]
                start_time = stop_clock_form.cleaned_data["start_time"]
                stop_time = stop_clock_form.cleaned_data["stop_time"]
                local_tz = pytz.timezone('America/New_York')
                start_datetime = local_tz.localize(datetime.combine(date, start_time))
                stop_datetime = local_tz.localize(datetime.combine(date, stop_time))
                open_meeting.start_datetime = start_datetime
                open_meeting.stop_datetime = stop_datetime
                open_meeting.notes = stop_clock_form.cleaned_data["notes"]
                open_meeting.save()

                if "repeat" in stop_clock_form.cleaned_data and stop_clock_form.cleaned_data["repeat"]:
                    repeat_students = stop_clock_form.cleaned_data["repeat"]
                    create_repeat(open_meeting, repeat_students, tutor_must_confirm=False)
                    notify_tutee_repeat_scheduled(
                        repeat_students,
                        subject=open_meeting.subject,
                        tutor=open_meeting.meetingmembership_set.filter(user_role="Tutor")[0].user
                    )

                # Maybe bulk_create would be better here but it has some caveats
                open_meeting.attendance.clear()
                TuteeAssessment.objects.filter(meeting=open_meeting).delete()
                open_meeting.attendance.add(user)
                if stop_clock_form.cleaned_data["attendance"]:
                    for user in stop_clock_form.cleaned_data["attendance"]:
                        open_meeting.attendance.add(user)
                        TuteeAssessment.objects.create(
                            meeting=open_meeting,
                            tutee=user,
                        )
                    meeting_id = str(open_meeting.id)
                    logger.info(f"{request.user.username or request.user} clocked out")
                    return HttpResponseRedirect("/clock/assessment/" + meeting_id)
                else:
                    messages.success(request, "Success")
                    logger.info(f"{request.user.username or request.user} clocked out with no attendance")
                    return HttpResponseRedirect(request.path_info)
    return render(
        request=request,
        template_name="tutor/clock.html",
        context={
            "user": user,
            "start_clock_form": start_clock_form,
            "stop_clock_form": stop_clock_form,
            "open_meeting": open_meeting,
            "past_meetings":past_meetings,
            "time": timezone.localtime(),
        },
    )


def start_clock(meeting, request):
    logger.info(f"{request.user.username or request.user} called start_clock view")
    meeting.attendance.add(request.user)
    meeting.start_datetime = timezone.now()
    meeting.save()


@login_required
def clock_assessment(request, meeting_id):
    logger.info(f"{request.user.username or request.user} called clock_assessment view")
    AssessmentFormSet = modelformset_factory(
        TuteeAssessment,
        form=TuteeAssessmentForm,
        fields={"tutee", "assessment","grade"},
        extra=0,
    )
    meeting = Meeting.objects.get(id=meeting_id)
    queryset = TuteeAssessment.objects.filter(meeting=meeting)
    if "submit" in request.POST:
        formset = AssessmentFormSet(request.POST, queryset=queryset)
        if formset.is_valid():
            with transaction.atomic():
                for form in formset:
                    if form.has_changed():
                        tutee_assessment = form.save()
                messages.success(request, "Success")
                logger.info(f"{request.user.username or request.user} submitted student assessments")
                return HttpResponseRedirect("/clock/")
            return HttpResponseRedirect(request.path_info)
    else:
        formset = AssessmentFormSet(queryset=queryset)

    return render(
        request=request,
        template_name="tutor/clock_assessment.html",
        context={
            "user": request.user,
            "formset": formset,
            "meeting": meeting,
        },
    )

@login_required
def clock_rate(request, unrated_meeting_id):

    try:
        meeting = MeetingMembership.objects.get(pk=unrated_meeting_id)
        
    except MeetingMembership.DoesNotExist:
        return HttpResponseRedirect(reverse('tutor:request'))

    if meeting.user != request.user:
        return HttpResponseRedirect(reverse('tutor:request'))

    meetingmembership = MeetingMembership.objects.get(id=unrated_meeting_id)

    if "rating" in request.POST and meetingmembership.user_role == "Tutor":
        meetingmembership.rate = request.POST["rate"]
        meetingmembership.rated = True
        meetingmembership.save()
        messages.success(request, "Rated Successfullly")
        return HttpResponseRedirect("/clock/")

    if "rating" in request.POST and meetingmembership.user_role == "Tutee":
        meetingmembership.rate = request.POST["rate"]
        meetingmembership.rated = True
        meetingmembership.save()
        messages.success(request, "Rated Successfullly")
        return HttpResponseRedirect("/request/")

    if "skip" in request.POST:
        meetingmembership.rate = 0
        meetingmembership.rated = True
        meetingmembership.save()
        messages.success(request, "Skipped Successfully")
        return HttpResponseRedirect("/request/")

    return render(
        request=request,
        template_name="tutor/clock_rate.html",
        context={
            "meeting": meetingmembership.meeting,
            "role": meetingmembership.user_role,
        }
    )

def get_tutor_training_stage(user):
    logger.info(f"tutee_portal function called for {user}")
    
    if(user.profile.onboarded == False):
        return "onboarded"

    try:
        record = user.orientation3
        record = user.orientation4
        record = user.orientation9
        record = user.orientation11
        record = user.backgroundcheckrequest
        record = user.livesession
        return "finished"
    except: 
        return "not-finished"


@login_required
def training(request):
    logger.info(f"{request.user.username or request.user} called training view")
    training_stage = get_tutor_training_stage(request.user)

    if training_stage != "finished":
        return HttpResponseRedirect(reverse(f"tutor:orientation"))

    return HttpResponseRedirect(reverse("tutor:profile"))


@login_required
def orientation(request):
    if get_tutor_training_stage(request.user) == "onboarded":
        
        return HttpResponseRedirect(reverse("tutor:onboard"))

    if (request.user.profile.account_type.display != "Tutor"):

        return HttpResponseRedirect(reverse("tutor:home"))

    if mobile(request):
        template_name = "tutor/mobile/orientation.html"

    else:
        template_name = "tutor/orientation.html"

    orientation_count = 0
    user = request.user
    try:
        record = user.orientation3
        record = user.orientation4
        record = user.orientation9
        record = user.orientation11
        orientation_count += 1
    except:
        pass

    try:
        record = user.backgroundcheckrequest
        if(user.backgroundcheckrequest.status == "Approved"):
            orientation_count += 1
    except:
        pass

    try:
        record = user.livesession
        orientation_count += 1
    except:
        pass

    ready = False

    if(orientation_count == 3):
        ready = True

    return render(
        request=request,
        template_name=template_name,
        context={
            "orientation_count": orientation_count,
            "ready": ready,
        },

    )


def get_requests_requiring_exit_ticket(user):
    logger.info(f"get_requests_requiring_exit_ticket function called for {user}")
    period = dt.timedelta(days=8)

    tutor_requests = user.tutorrequest_set.filter(
        meeting__isnull=False, meeting__scheduled_start__lt=timezone.now()-period,
        exitticket__isnull=True, meeting__active=True,
    ).distinct()

    tutor_requests = user.tutorrequest_set.filter(
        meeting__isnull=False,
        meeting__scheduled_start__lt=timezone.now()-period,
        exitticket__isnull=True,
        meeting__active=True,
        meeting__attendance=user,
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


@login_required
def exit_ticket(request):
    logger.info(f"{request.user.username or request.user} called exit_ticket view")
    logger.info(f"{request.user.username or request.user}, exit view")
    user = request.user
    requests_requiring_exit_ticket = get_requests_requiring_exit_ticket(user)
    tutor_request = requests_requiring_exit_ticket.first()

    if not tutor_request:
        return HttpResponseRedirect(reverse("tutor:request"))

    grade_level_form = None
    form = None
    meetings = None
    tutor = None

    k12 = ["Elementary School", "Middle School", "High School"]
    if user.profile.sector.display in k12 and not user.profile.grade_level:
        grade_level_form = GradeLevelForm(request.POST or None, instance=user.profile)

        if "submit-grade" in request.POST:
            logger.info(f"{request.user.username or request.user} submitted a submit-grade POST request to exit_ticket")
            if grade_level_form.is_valid():
                grade_level_form.save()
                return HttpResponseRedirect(reverse("tutor:exit-ticket"))
    else:
        meetings = get_chained_meetings(tutor_request.meeting)
        tutor = tutor_request.meeting.meetingmembership_set.filter(user_role="Tutor").first().user

        if user.profile.sector.display == "Elementary School":
            if user.profile.grade_level.display in ["Pre-K", "Kindergarten", "1st"]:
                form = ExitTicketEasyForm(request.POST or None)
            else:
                form = ExitTicketMediumForm(request.POST or None)
        else:
            form = ExitTicketDifficultForm(request.POST or None)

        if "submit" in request.POST:
            logger.info(f"{request.user.username or request.user} submitted a submit POST request to clock")
            if form.is_valid():
                exit_ticket = form.save(commit=False)
                exit_ticket.tutor = tutor
                exit_ticket.request = tutor_request
                exit_ticket.completed = timezone.now()
                exit_ticket.save()
                logger.info(f"{request.user.username or request.user} created an exit ticket")
                return HttpResponseRedirect(reverse("tutor:exit-ticket"))

    return render(
        request=request,
        template_name="tutor/exit_ticket.html",
        context={
            "form": form,
            "tutor_request": tutor_request,
            "meetings": meetings,
            "tutor": tutor,
            "tutor_request": tutor_request,
            "grade_level_form": grade_level_form,
        },
    )


@login_required
def leave_ticket(request):
    logger.info(f"{request.user.username or request.user} called leave_ticket view")

    if (request.user.profile.account_type.display != "Tutor"):

        return HttpResponseRedirect(reverse("tutor:home"))

    user = request.user
    form = LeaveTicketForm(request.POST or None)

    if "submit" in request.POST:
        logger.info(f"{request.user.username or request.user} submitted a submit POST request to leave_ticket")
        form.fields['check'].required = True
        form.fields['leave_reason'].required = True
        form.fields['confirm_sign'].required = True
        if form.is_valid():
            leave_ticket = form.save(commit=False)
            leave_ticket.user = user
            leave_ticket.completed = timezone.now()
            leave_ticket.save() 
            user.is_active = False
            user.save()
            messages.success(request, "Your account has been deactivated")
            logout(request)
            logger.info(f"{request.user.username or request.user} created a leave ticket")
            return HttpResponseRedirect(reverse("tutor:home"))

    form.fields['check'].required = False
    form.fields['leave_reason'].required = False
    form.fields['confirm_sign'].required = False
    if 'cancel' in request.POST:
        logger.info(f"{request.user.username or request.user} submitted a cancel POST request to leave_ticket")
        return HttpResponseRedirect(reverse("tutor:profile"))
    
    return render(
        request = request,
        template_name="tutor/leave_ticket.html",
        context={
            "form": form,
            "tutor": user,
        },
    )


@login_required
def manage(request):
    logger.info(f"{request.user.username or request.user} called manage view")
    user = request.user
    account_type = user.profile.account_type.display
    if (account_type == "K-12-Tutee" or account_type == "College-Tutee" or account_type == "Adult-Tutee"):
        return HttpResponseRedirect(reverse('tutor:request'))
    if (get_tutor_training_stage(request.user) != "finished" or request.user.backgroundcheckrequest.status != "Approved"):
        return HttpResponseRedirect(reverse('tutor:orientation'))
    duration = ExpressionWrapper(F('stop_datetime') - F('start_datetime'), output_field=fields.DurationField())
    past_meetings = (user.meeting_set
        .filter(~Q(stop_datetime=None) & ~Q(meetingmembership__status="Cancelled"))
        .annotate(duration=duration)
        .order_by('-start_datetime'))

    
    #For the purpose of rating
    tutee_membership = MeetingMembership.objects.filter(meeting_id__in = past_meetings, user=request.user).order_by('-meeting__start_datetime')

    #In order to find the # of rating not done by the tutors
    rating_count = 0
    for tutee in tutee_membership:
        if tutee.rate not in [1,2,3,4,5]:
            rating_count+=1
    

    scheduled_meetings = user.meeting_set.distinct().filter(
        Q(start_datetime=None)
        # & Q(scheduled_start__gt=timezone.now())
        & ~Q(meetingmembership__status="Cancelled")
    ).filter(
        meetingmembership__user__profile__account_type__display__in=[
            "K-12-Tutee",
            "College-Tutee",
            "Adult-Tutee",
        ],
    ).annotate(
        num_confirmed=Count(
            "meetingmembership",
            filter=Q(meetingmembership__user_role="Tutee", meetingmembership__status="Confirmed"),
            distinct=True,
        ),
        status=Case(
            When(
                Exists(MeetingMembership.objects.filter(
                        user=user,
                        status="Confirmed",
                        meeting=OuterRef('pk'),
                    )
                ),
                then=Value("Confirmed")
            ),
            When(
                Exists(MeetingMembership.objects.filter(
                        user=user,
                        status="Pending Confirmation",
                        meeting=OuterRef('pk'),
                    )
                ),
                then=Value("Not confirmed")
            ),
            default=Value("–"),
        ),
        confirmation_due=ExpressionWrapper(F("created_at")+dt.timedelta(hours=48), output_field=fields.DateTimeField())
    ).filter(
        Q(num_confirmed__gte=1) | Q(meetingmembership__status="Confirmed")
    ).order_by("scheduled_start")

    open_meetings = user.meeting_set.filter(start_datetime__isnull=False, stop_datetime__isnull=True)
    unfinished_assessments = TuteeAssessment.objects.filter(
        meeting__stop_datetime__isnull=False,
        assessment=None
    )
    canceled_meetings = user.meeting_set.filter(
        scheduled_start__gt=timezone.now(),
        meetingmembership__status="Cancelled",
        meetingmembership__user=user,
    ).distinct()

    cancel_meeting_form = CancelMeetingForm(
        request.POST or None, scheduled_meetings=scheduled_meetings
    )
    unfulfilled_requests = get_unfulfilled_requests(user)
    if "cancel_meeting" in request.POST:
        logger.info(f"{request.user.username or request.user} submitted a cancel_meeting POST request to manage")
        if cancel_meeting_form.is_valid():
            meeting = cancel_meeting_form.cleaned_data["meeting"]
            membership_queryset = MeetingMembership.objects.filter(
                meeting=meeting, user=user
            )
            cancel_memberships(membership_queryset, reason="User", call_source="manage")
            logger.info(f"{request.user.username or request.user} cancelled meeting membership for {meeting}")
            return HttpResponseRedirect(reverse('tutor:manage'))

    if "rating" in request.POST:
        
        rate = request.POST["rate"]
        print(rate)
        meeting_id = request.POST["meeting"]
        print(meeting_id)
        meeting_update = MeetingMembership.objects.get(id=meeting_id)
        print(meeting_update)
        meeting_update.rate = rate
        meeting_update.save()
        return HttpResponseRedirect(reverse("tutor:request"))
    try: 
        user.backgroundcheckrequest 
        no_bg = False
    except:
        no_bg = True
    
    return render(
        request=request,
        template_name="tutor/manage.html",
        context={
            "user": user,
            "name": user.profile.nickname or user.profile.full_name,
            "cancel_meeting_form": cancel_meeting_form,
            "scheduled_meetings": scheduled_meetings,
            "past_meetings": past_meetings,
            "open_meetings": open_meetings,
            "unfinished_assessments": unfinished_assessments,
            "time": timezone.localtime(),
            "unfulfilled_requests": unfulfilled_requests,
            "no_bg": no_bg,
            "tutee_membership": tutee_membership,
            "rating_count": rating_count,
        },
    )

@login_required
def background(request):
    logger.info(f"{request.user.username or request.user} called background view")
    if(request.user.profile.account_type.display != "Tutor"):
        return HttpResponseRedirect(reverse("tutor:home"))
    applicable = True
    if "send" in request.POST:
        logger.info(f"{request.user.username or request.user} submitted a send POST request to background")
        background_form = BackgroundForm(request.POST, user=request.user)
        if background_form.is_valid():
            BackgroundCheckRequest.objects.create(user=request.user, status="Queued")

            # Send background check email to tutor
            email_context = ({
                'tutor_name': request.user.profile.nickname or request.user.profile.full_name,
            })

            text_content = render_to_string('tutor/email_bgcheck_tutor.txt', email_context)
            html_content = render_to_string('tutor/email_bgcheck_tutor.html', email_context)

            send_emails(
                user_emails=[request.user.email],
                text_content=text_content,
                html_content=html_content,
                subject="City Tutors Background Check"
            )
            logger.info(f"{request.user.username or request.user} created a background check request")
            return HttpResponseRedirect(request.path_info)
    else:
        background_form = BackgroundForm(
            user=request.user,
            initial={
                "full_name": request.user.profile.full_name,
                "phone_number": request.user.profile.phone_number,
                "email": request.user.email,
            },
        )
    return render(
        request=request,
        template_name="tutor/background.html",
        context={
            "background_form": background_form,
        },
    )


def support(request):
    logger.info(f"{request.user.username or request.user} called support view")
    if "submit" in request.POST:
        logger.info(f"{request.user.username or request.user} submitted a POST request to support")
        form = IssueForm(request.POST, user=request.user)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.timestamp = timezone.now()
            if request.user.is_authenticated:
                obj.submitter = request.user
            obj.save()
            messages.success(request, "Your issue will be reviewed")
            logger.info(f"{request.user.username or request.user} created a support issue")
    else:
        form = IssueForm(user=request.user)
    return render(
        request=request,
        template_name="tutor/support.html",
        context={
            "form": form,
        },
    )


# sumbit a harassment issue
@login_required
def harass_issue(request):
    logger.info(f"{request.user.username or request.user} called harass_issue view")
    if "submit" in request.POST:
        logger.info(f"{request.user.username or request.user} submitted a POST request to harass_issue")
        harass_issue_form = HarassIssueForm(request.POST)
        if harass_issue_form.is_valid():
            messages.success(request, "Submission succeeded")
            issue = Issue.objects.create(
                type="Harass",
                timestamp=timezone.now(),
                submitter=request.user,
            )
            harass_issue = HarassIssue.objects.create(
                issue_description=harass_issue_form.cleaned_data["issue_description"],
                issue=issue,
            )
    else:
        harass_issue_form = HarassIssueForm()
    return render(
        request=request,
        template_name="tutor/harass_issue.html",
        context={
            "harass_issue_form": harass_issue_form,
        },
    )


@login_required
def profile(request):
    logger.info(f"{request.user.username or request.user} called profile view")

    if "Tutee" in request.user.profile.account_type.display:
        ProfileForm = TuteeProfileForm
    else:
        ProfileForm = TutorProfileForm

    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=request.user)

    if "submit" in request.POST:
        logger.info(f"{request.user.username or request.user} submitted a POST request to profile")
        profile_form = ProfileForm(request.POST, instance=profile)
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, f"Your settings have been saved")
            logger.info(f"{request.user.username or request.user} saved profile settings")
        messages.error(request, str(profile_form.errors))
    else:
        profile_form = ProfileForm(instance=profile)

    return render(
        request=request,
        template_name="tutor/profile.html",
        context={
            "profile_form": profile_form,
            "page": "profile",
        },
    )


@login_required
def profile_tutor_hours(request):
    logger.info(f"{request.user.username or request.user} called profile_tutor_hours view")

    if request.user.profile.account_type.display != "Tutor":
        raise PermissionDenied

    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        return HttpResponseRedirect(reverse("tutor:profile"))

    user = request.user

    current_month_offered = user.profile.offered_hours_current_month
    current_month_done = user.profile.hours_done_current_month
    current_week_month = user.profile.hours_left_current_month

    current_week_offered = user.profile.offered_hours
    current_week_done = user.profile.hours_done_current_week
    current_week_left = user.profile.hours_left_current_week

    try:
        tutor_monthly = TutorOfferedMonthlyHours.objects.get(user=request.user)
    except TutorOfferedMonthlyHours.DoesNotExist:
        tutor_monthly = TutorOfferedMonthlyHours.objects.create(user=request.user)

    if "submit_monthly" in request.POST:
        monthly_hours_form = TutorMonthlyHoursForm(request.POST, instance=tutor_monthly)
        logger.info(f"{request.user.username or request.user} submitted a submit_monthly POST request to profile_tutor_hours")
        if monthly_hours_form.is_valid():
            monthly_hours_form.save()
            messages.success(request, f"Your hours have been updated")
            logger.info(f"{request.user.username or request.user} saved monthly profile_tutor_hours settings")
        messages.error(request, str(monthly_hours_form.errors))
    else:
        monthly_hours_form = TutorMonthlyHoursForm(instance=tutor_monthly)

    if "submit_current_monthly" in request.POST:
        current_monthly_hours_form = TutorCurrentMonthlyHours(request=request.POST, instance=tutor_monthly, field_name=TutorOfferedMonthlyHours.get_current_month_field_name())
        logger.info(f"{request.user.username or request.user} submitted a submit_current_monthly POST request to profile_tutor_hours")
        if current_monthly_hours_form.is_valid():
            current_monthly_hours_form.save()
            messages.success(request, f"Your hours have been updated")
            logger.info(f"{request.user.username or request.user} saved current monthly profile_tutor_hours settings")
        messages.error(request, str(current_monthly_hours_form.errors))
    else:
        current_monthly_hours_form = TutorCurrentMonthlyHours(request=None, field_name=TutorOfferedMonthlyHours.get_current_month_field_name(), instance=tutor_monthly)

    if "submit_weekly" in request.POST:
        weekly_hours_form = TutorWeeklyHoursForm(request.POST, instance=profile)
        logger.info(f"{request.user.username or request.user} submitted a submit_weekly POST request to profile_tutor_hours")
        if weekly_hours_form.is_valid():
            weekly_hours_form.save()
            messages.success(request, f"Your hours have been updated")
            logger.info(f"{request.user.username or request.user} saved weekly profile_tutor_hours settings")
        messages.error(request, str(weekly_hours_form.errors))
    else:
        weekly_hours_form = TutorWeeklyHoursForm(instance=profile)

    if "submit_type" in request.POST:
        type_form = TutorHoursTypeForm(request.POST, instance=profile)
        logger.info(f"{request.user.username or request.user} submitted a submit_type POST request to profile_tutor_hours")
        if type_form.is_valid():
            type_form.save()
            messages.success(request, f"Your settings have been updated")
            logger.info(f"{request.user.username or request.user} saved weekly profile_tutor_hours settings")
        messages.error(request, str(type_form.errors))
    else:
        type_form = TutorHoursTypeForm(instance=profile)

    return render(
        request=request,
        template_name="tutor/profile.html",
        context={
            "page": "tutor_hours",
            "monthly_hours_form": monthly_hours_form,
            "current_monthly_hours_form": current_monthly_hours_form,
            "weekly_hours_form": weekly_hours_form,
            "type_form": type_form,
            "monthly": profile.tutor_monthly_volunteer,
            "current_month_offered": user.profile.offered_hours_current_month,
            "current_month_done": user.profile.hours_done_current_month,
            "current_month_left": user.profile.hours_left_current_month,
            "current_week_offered": user.profile.offered_hours,
            "current_week_done": user.profile.hours_done_current_week,
            "current_week_left": user.profile.hours_left_current_week,
        },
    )


@login_required
def profile_public(request, user_id):
    logger.info(f"{request.user.username or request.user} called profile_public view")
    profile_user = User.objects.get(id=user_id)

    try:
        profile_user.profile
    except Profile.DoesNotExist:
        return HttpResponseRedirect(reverse("tutor:site_log"))

    if request.user.profile.account_type.display != "Program-Coordinator":
        raise PermissionDenied
    if request.user.profile.site != profile_user.profile.site:
        raise PermissionDenied

    duration = ExpressionWrapper(F('stop_datetime') - F('start_datetime'), output_field=fields.DurationField())

    tutor_requests = TutorRequest.objects.filter(
        Q(user=profile_user) & (Q(active=True) | Q(meeting__active=True))
    ).order_by("-timestamp")
    fulfilled_tutor_requests = tutor_requests.filter(meeting__isnull=False)
    unfulfilled_tutor_requests = tutor_requests.filter(meeting__isnull=True)

    past_meetings = (profile_user.meeting_set
        .filter(active=True)
        .annotate(
            duration=duration,
            num_students=Count(
                'meetingmembership',
                filter=Q(meetingmembership__user_role='Tutee') & ~Q(meetingmembership__status='Cancelled')
            )
        )
        .prefetch_related(Prefetch(
            "members",
            queryset=User.objects.filter(profile__account_type__display="Tutor"),
            to_attr='tutors'
        ))
        .order_by("-scheduled_start")
    )

    scheduled_meetings = (profile_user.meeting_set
        .filter(active=True, scheduled_start__gt=timezone.now())
        .prefetch_related(Prefetch(
            "members",
            queryset=User.objects.filter(profile__account_type__display="Tutor"),
            to_attr='tutors'
        ))
        .order_by("-scheduled_start")
    )

    return render(
        request=request,
        template_name="tutor/profile_public.html",
        context={
            "user": request.user,
            "profile_user": profile_user,
            "past_meetings": past_meetings,
            "scheduled_meetings": scheduled_meetings,
            "tutor_requests": tutor_requests,
            "fulfilled_tutor_requests": fulfilled_tutor_requests,
            "unfulfilled_tutor_requests": unfulfilled_tutor_requests,
        },
    )


@login_required
def site_portal(request):
    logger.info(f"{request.user.username or request.user} called site_portal view")
    return render(
        request=request,
        template_name="tutor/site_portal.html",
        context={"user": request.user},
    )


@login_required
def site_log(request, location_id=None):
    logger.info(f"{request.user.username or request.user} called site_log view")
    if request.user.profile.account_type.display != "Program-Coordinator":
        raise PermissionDenied


 
    site = request.user.profile.site
    if location_id:

        site_location = SiteLocation.objects.get(id=location_id)
        if not check_site_permisssion(request.user, site_location):
            raise PermissionDenied
    else:
        site_location = request.user.profile.site_location
    
    if site_location:
        all_site_locations = None
        users = User.objects.filter(profile__site=site, profile__site_location=site_location)
    else:
        # For the purpose of Program Coordinator to see the entire program data
        all_site_locations = SiteLocation.objects.filter(site=site)
        users = User.objects.filter(profile__site=site)

    users = get_site_users_annotated(users)

    meetings = get_site_meetings(users)    
    scheduled_meetings = meetings.filter(
        scheduled_start__gt=timezone.now()
    )
    past_meetings = meetings.filter(
        scheduled_start__lte=timezone.now()
    )

    # Calculate which semester we are in currently
    year = timezone.now().year
    month = timezone.now().month
    day = 1
    if(month in (1,2,3,4,5)):
        month = 1 
        sem_time = "Jan~May"
    elif(month in (6,7,8)):
        month = 6
        sem_time = "Jun~Aug"
    else:
        month = 9
        sem_time = "Sep~Dec"

    # Calculating hour length for each semester
    semester_meetings = meetings.filter(
        scheduled_start__gt=dt.datetime(year, month, day, tzinfo=pytz.UTC)
    )
    semester_duration = semester_meetings.aggregate(Sum('duration'))["duration__sum"]
    sem_remaining_time = 0
    sem_hours = 0
    sem_minutes = 0
    if(semester_duration != None):
        sem_remaining_time = semester_duration
        sem_total_minutes = int(sem_remaining_time.total_seconds()//60)
        sem_hours,sem_minutes = sem_total_minutes // 60, sem_total_minutes % 60

    # Calculating the time frame for the current week
    today = date.today()
    """ print(today) """
    weekday = today.weekday()
    """ print(weekday) """
    start_delta = timedelta(days=weekday)
    """ print(start_delta) """
    start_of_week = today-start_delta
    """ print(start_of_week) """
    #week_calculate = timezone.now() - timedelta(days=7)
    week_meetings = meetings.filter(
        scheduled_start__gte = start_of_week
    )

    # Calculating the total hours that has been used this week
    week_duration = week_meetings.aggregate(Sum('duration'))["duration__sum"]
    if(request.user.profile.site):
        max_hours = request.user.profile.site.tier.max_pooled_hours
    else:
        max_hours = "None"
    remaining_time = 0
    hours = 0
    minutes = 0
    if(week_duration != None):
        remaining_time = week_duration
        total_minutes = int(remaining_time.total_seconds()//60)
        hours,minutes = total_minutes // 60, total_minutes % 60

    # Query needed to students with at least 1 fulfilled requests
    at_least_one_meeting = users.filter(status="All requests fulfilled" or "Attended meetings. Some requests unfulfilled")
    
    # Calculating unique number of students participated 
    number_of_students_current_week = users.filter(
        Q(meeting__scheduled_start__gte = start_of_week), Q(meeting__start_datetime__isnull = False),
        Q(meeting__active = True), Q(meeting__stop_datetime__isnull = False))

    total_duration = past_meetings.aggregate(Sum('duration'))["duration__sum"]

    if total_duration and meetings:
        average_duration = total_duration / len(past_meetings)
    else:
        total_duration = "–"
        average_duration = "–"

    tutor_requests = get_site_requests(users)
    unfulfilled_requests = tutor_requests.filter(meeting__isnull=True)
    fulfilled_requests = tutor_requests.filter(meeting__isnull=False)

    return render(
        request=request,
        template_name="tutor/site_log.html",
        context={
            "site": site,
            "site_location": site_location,
            "all_site_locations": all_site_locations,
            "request": request,
            "users": users,
            "meetings": meetings,
            "scheduled_meetings": scheduled_meetings,
            "past_meetings": past_meetings,
            "tutor_requests": tutor_requests,
            "unfulfilled_requests": unfulfilled_requests,
            "fulfilled_requests": fulfilled_requests,
            "total_duration": total_duration,
            "average_duration": average_duration,
            "semester_duration": semester_duration,
            "semester_start": month,
            "hours": hours,
            "minutes": minutes,
            "max_hours": max_hours,
            "sem_hours": sem_hours,
            "sem_minutes": sem_minutes,
            "sem_time": sem_time,
            "at_least_one_meeting": at_least_one_meeting,
            "week_meetings": week_meetings,
            "number_of_students_current_week": number_of_students_current_week,
        },
    )


def check_site_permisssion(user, site_location):
    logger.info(f"check_site_permisssion view called")
    user_in_site_location = user.profile.site_location == site_location
    user_part_of_site = site_location.site == user.profile.site and not user.profile.site_location
    return user_in_site_location or user_part_of_site


@login_required
def site_requests(request, location_id=None):
    logger.info(f"{request.user.username or request.user} called site_requests view")
    if request.user.profile.account_type.display != "Program-Coordinator":
        raise PermissionDenied

    site = request.user.profile.site

    if location_id:
        site_location = SiteLocation.objects.get(id=location_id)
        if not check_site_permisssion(request.user, site_location):
            raise PermissionDenied
    else:
        site_location = request.user.profile.site_location

    if site_location:
        users = User.objects.filter(profile__site=site, profile__site_location=site_location)
    else:
        users = User.objects.filter(profile__site=site)

    RequestFormset = modelformset_factory(
        TutorRequest,
        form=SiteTutorRequestEditForm,
        extra=0,
    )
    queryset = get_site_requests(users).filter(
        meeting__isnull=True,
        active=True,
    )
    formset = RequestFormset(request.POST or None, queryset=queryset)

    if "submit" in request.POST:
        logger.info(f"{request.user.username or request.user} submitted a POST request to site_requests")
        if formset.is_valid():
            with transaction.atomic():
                for form in formset:
                    if form.has_changed():
                        form.save()
                messages.success(request, "Success")
            logger.info(f"site coordinator {request.user.username or request.user} updated student requests")
            return HttpResponseRedirect(request.path_info)

    return render(
        request=request,
        template_name="tutor/site_manage_requests.html",
        context={
            "site": site,
            "site_location": site_location,
            "formset": formset,
        },
    )


@login_required
def site_confirmations(request, location_id=None):
    logger.info(f"{request.user.username or request.user} called site_confirmations view")
    if request.user.profile.account_type.display != "Program-Coordinator":
        raise PermissionDenied

    site = request.user.profile.site

    if location_id:
        site_location = SiteLocation.objects.get(id=location_id)
        if not check_site_permisssion(request.user, site_location):
            raise PermissionDenied
    else:
        site_location = request.user.profile.site_location

    if site_location:
        users = User.objects.filter(profile__site=site, profile__site_location=site_location)
    else:
        users = User.objects.filter(profile__site=site)

    MembershipFormset = modelformset_factory(
        MeetingMembership,
        form=SiteMeetingMembershipForm,
        extra=0,
    )
    queryset = get_site_memberships(users).filter(
        meeting__active=True,
        meeting__scheduled_start__gt=timezone.now()-dt.timedelta(days=3),
        meeting__start_datetime__isnull=True,
    )
    formset = MembershipFormset(request.POST or None, queryset=queryset)

    if "submit" in request.POST:
        logger.info(f"{request.user.username or request.user} submitted a POST request to site_confirmations")
        if formset.is_valid():
            with transaction.atomic():
                for form in formset:
                    if form.has_changed():
                        membership = form.instance
                        if form.instance.status == "Cancelled":
                            cancel_memberships(MeetingMembership.objects.filter(id=membership.id), reason="Site", call_source="site_confirmations")
                            notify_tutee_site_cancel_membership(membership.user)
                            membership.save()
                        elif form.instance.status == "Confirmed":
                            confirm_membership(membership)
                            notify_tutee_site_update_request(membership.user)
                            membership.save()
                        elif form.instance.status == "Pending Confirmation":
                            messages.warning(request, "You cannot change a meeting status to 'Pending Confirmation'")

                messages.success(request, "Success")
            logger.info(f"site coordinator {request.user.username or request.user} updated student confirmations")
            return HttpResponseRedirect(request.path_info)

    return render(
        request=request,
        template_name="tutor/site_manage_confirmations.html",
        context={
            "formset": formset,
            "site": site,
            "site_location": site_location,
        },
    )


@login_required
def site_new_request(request, location_id=None):
    logger.info(f"{request.user.username or request.user} called site_new_request view")
    if request.user.profile.account_type.display != "Program-Coordinator":
        raise PermissionDenied

    site = request.user.profile.site

    if location_id:
        site_location = SiteLocation.objects.get(id=location_id)
        if not check_site_permisssion(request.user, site_location):
            raise PermissionDenied
    else:
        site_location = request.user.profile.site_location

    if site_location:
        users = User.objects.filter(profile__site=site, profile__site_location=site_location)
    else:
        users = User.objects.filter(profile__site=site)

    students = get_site_users_annotated(users).filter(profile__onboarded=True)

    return render(
        request=request,
        template_name="tutor/site_new_request.html",
        context={
            "students": students,
        },
    )


@login_required
def site_new_request_student(request, student_id):
    logger.info(f"{request.user.username or request.user} called site_new_request_student view")
    student = User.objects.get(id=student_id)

    form = SiteTutorRequestForm(request.POST or None, user=student, site=request.user.profile.site)

    if "submit" in request.POST:
        logger.info(f"{request.user.username or request.user} submitted a POST request to site_new_request_student")
        if form.is_valid():
            with transaction.atomic():
                instance = form.save(commit=False)
                submit_new_student_request(instance, tutee=student)
                messages.success(request, "Your request has been added")
                notify_tutee_site_create_request(student)
                logger.info(f"site coordinator {request.user.username or request.user} created a new request for student {student.username or student}")
                return HttpResponseRedirect(reverse("tutor:site-requests"))

    return render(
        request=request,
        template_name="tutor/site_new_request_student.html",
        context={
            "student": student,
            "form": form,
        },
    )


@login_required
def site_cancel_request(request, request_id):
    logger.info(f"{request.user.username or request.user} called site_cancel_request view")
    tutor_request = TutorRequest.objects.get(id=request_id)

    if "submit" in request.POST:
        logger.info(f"{request.user.username or request.user} submitted a POST request to site_cancel_request")
        with transaction.atomic():
            cancel_request(tutor_request, reason="Site", call_source="site_cancel_request")
            notify_tutee_site_cancel_request(tutor_request.user)
            messages.success(request, "Successfully cancelled request")
            logger.info(f"site coordinator {request.user.username or request.user} cancelled request for student {tutor_request.user.username or tutor_request.user}")
            return HttpResponseRedirect(reverse("tutor:site-requests"))

    return render(
        request=request,
        template_name="tutor/site_cancel_request.html",
        context={
            "request": tutor_request,
        },
    )


@login_required
def site_download(request, site_location_id=None):
    logger.info(f"{request.user.username or request.user} called site_download view")
    if request.user.profile.account_type.display != "Program-Coordinator":
        raise PermissionDenied

    print(site_location_id)
    user_site = request.user.profile.site
    user_site_location = request.user.profile.site_location

    if site_location_id:
        site_location = SiteLocation.objects.get(id=site_location_id)

        if check_site_permisssion(request.user, site_location):
            users = User.objects.filter(Q(profile__site=user_site) & Q(profile__site_location=site_location) & Q(profile__account_type=AccountType.objects.get(display="K-12-Tutee")) |
            Q(profile__site=user_site) & Q(profile__site_location=site_location) & Q(profile__account_type=AccountType.objects.get(display="College-Tutee")) |
            Q(profile__site=user_site) & Q(profile__site_location=site_location) & Q(profile__account_type=AccountType.objects.get(display="Adult-Tutee"))
            )
        else:
            raise PermissionDenied
    else:
        site_location = None
        users = User.objects.filter(Q(profile__site=user_site) & Q(profile__account_type=AccountType.objects.get(display="K-12-Tutee")) |
        Q(profile__site=user_site) & Q(profile__account_type=AccountType.objects.get(display="College-Tutee")) | 
        Q(profile__site=user_site) & Q(profile__account_type=AccountType.objects.get(display="Adult-Tutee")))

    output = StringIO()
    f = zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED)
    zipio = BytesIO()

    students = get_site_users_annotated(users)
    meetings = get_site_meetings(users)
    tutor_requests = get_site_requests(users)

    student_csv_data = StringIO()
    student_writer = csv.writer(student_csv_data)
    student_writer.writerow([
        'Full Name or Nickname',
        'Sector',
        'Email',
        'Phone Number',
        'Status',
        'Fulfilled Requests',
        'Unfulfilled Requests',
        'Scheduled Meetings',
        'Past Meetings',
    ])
    for student in students:
        row = [
            student.profile.full_name or student.profile.nickname,
            student.profile.sector,
            student.email,
            student.profile.phone_number,
            student.status,
            student.num_fulfilled_requests,
            student.num_unfulfilled_requests,
            student.num_scheduled_meetings,
            student.num_past_meetings,
        ]
        student_writer.writerow(row)

    session_csv_data = StringIO()
    session_writer = csv.writer(session_csv_data)
    session_writer.writerow([
        'Student(s)',
        'Number of Students',
        'Tutor',
        'Subject',
        'Scheduled Start',
        'Actual Start',
        'Actual End',
        'Notes',
        'Assessments'
    ])
    for meeting in meetings:
        row = [
            ",".join(str(student) for student in meeting.students),
            meeting.num_students,
            ",".join(str(tutor) for tutor in meeting.tutors),
            meeting.subject,
            meeting.scheduled_start,
            meeting.start_datetime,
            meeting.stop_datetime,
            meeting.notes,
            ",".join(str(assessment) for assessment in meeting.assessments),
        ]
        session_writer.writerow(row)

    requests_csv_data = StringIO()
    request_writer = csv.writer(requests_csv_data)
    request_writer.writerow([
        'Created',
        'Student',
        'Subject',
        'Notes',
        'Meeting',
    ])
    for tutor_request in tutor_requests:
        row = [
            tutor_request.timestamp,
            tutor_request.user.profile.full_name or tutor_request.user.profile.nickname,
            tutor_request.subject,
            tutor_request.notes,
            str(tutor_request.meeting),
        ]
        request_writer.writerow(row)

    with zipfile.ZipFile(zipio, 'w') as f:
        f.writestr("students.csv", student_csv_data.getvalue())
        f.writestr("sessions.csv", session_csv_data.getvalue())
        f.writestr("requests.csv", requests_csv_data.getvalue())

    response = HttpResponse(zipio.getvalue())
    filename = f"CityTutors-{dt.date.today().strftime('%Y%m%d')}.zip"
    response['Content-Disposition'] = 'attachment; filename="%s"' % filename

    logger.info(f"{request.user.username or request.user} downloaded site data for {site_location or user_site}")
    return response

@login_required
def database_download(request):
    logger.info(f"{request.user.username or request.user} called database_download view")

    if not (request.user.is_superuser or request.user.is_staff):
        raise PermissionDenied

    ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
    BACKUP_DIR = os.path.join(ROOT_DIR, 'backups')
    all_folders = os.listdir(BACKUP_DIR)
    all_folders.sort(reverse=True)
    filename = all_folders[0]

    fullpath = os.path.join(BACKUP_DIR, filename)
    response = HttpResponse(open(fullpath, 'rb').read())
    response['Content-Type'] = 'application/zip'
    response['Content-Disposition'] = 'attachment; filename="%s"' % filename

    logger.info(f"{request.user.username or request.user} downloaded database data ")
    return response

@login_required
def session_detail(request, session_id):
    logger.info(f"{request.user.username or request.user} called session_detail view")
    session = Meeting.objects.get(pk=session_id)
    tutors = session.attendance.all().filter(membership__user_role="Tutor")
    tutees = session.attendance.all().filter(membership__user_role="Tutee")

    return render(
        request=request,
        template_name="tutor/session_detail.html",
        context={
            "user": request.user,
            "session": session,
            "tutors": tutors,
            "tutees": tutees,
        },
    )


@login_required
def session(request, session_id):
    logger.info(f"{request.user.username or request.user} called session view")
    session = Meeting.objects.get(pk=session_id)
    tutors = session.attendance.all().filter(membership__user_role='Tutor')
    tutees = session.attendance.all().filter(membership__user_role='Tutee')

    return render(
        request=request,
        template_name="tutor/session.html",
        context={
            "user": request.user,
            "session": session,
            "tutors": tutors,
            "tutees": tutees,
        },
    )


def site_registration(request):
    logger.info(f"{request.user.username or request.user} called site_registration view")
    form = ProgramCoordinatorRegistrationForm(request.POST or None)
    
    if "submit" in request.POST:
        logger.info(f"{request.user.username or request.user} submitted a POST request to site_registration")
        if form.is_valid():
            user = User.objects.create_user(
                email=form.cleaned_data["email"],
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password"],
            )
            profile = Profile.objects.create(
                user=user,
                full_name=form.cleaned_data["full_name"],
                nickname=form.cleaned_data["nickname"],
                account_type=AccountType.objects.get(display="Program-Coordinator"),
                site=form.cleaned_data["site"],
                onboarded=True,
            )
            if form.cleaned_data["site_location"]:
                profile.site_location = form.cleaned_data["site_location"]
                profile.save()

            login(request, user)
            logger.info(f"registered site coordinator {request.user.username or request.user}")
            return HttpResponseRedirect(reverse("tutor:site_portal"))

    return render(
        request=request,
        template_name="tutor/site_registration.html",
        context={
            "request": request,
            "form": form,
        },
    )


def tutor_registration(request):
    logger.info(f"{request.user.username or request.user} called tutor_registration view")
    if "submit" in request.POST:
        logger.info(f"{request.user.username or request.user} submitted a POST request to tutor_registration")
        form = TutorRegistrationForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                email=form.cleaned_data["email"],
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password"],
            )
            profile = Profile.objects.create(
                user=user,
                can_speak_english=form.cleaned_data["can_you_speak_english"],
                account_type=AccountType.objects.get(display="Tutor"),
            )
            login(request, user)
            logger.info(f"registered tutor {request.user.username or request.user}")
            return HttpResponseRedirect(reverse("tutor:onboard"))
    else:
        form = TutorRegistrationForm()
    return render(
        request=request,
        template_name="tutor/tutor_registration.html",
        context={
            "request": request,
            "form": form,
        },
    )


def k_12_registration(request):
    logger.info(f"{request.user.username or request.user} called k_12_registration view")
    if "submit" in request.POST:
        logger.info(f"{request.user.username or request.user} submitted a POST request to k_12_registration")
        form = K12RegistrationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = User.objects.create_user(
                    email=form.cleaned_data["email"],
                    username=form.cleaned_data["username"],
                    password=form.cleaned_data["password"],
                )
                profile = Profile.objects.create(
                    user=user,
                    zip_code=form.cleaned_data["student_zip_code"],
                    can_speak_english=form.cleaned_data["student_speaks_english"],
                    site=form.cleaned_data["student_is_in_partner_program"],
                    site_location=form.cleaned_data["student_is_in_partner_program_location"],
                    account_type=AccountType.objects.get(display="K-12-Tutee"),
                )
            login(request, user)
            logger.info(f"registered {request.user.username or request.user} for K12")
            return HttpResponseRedirect(reverse("tutor:onboard"))
    else:
        form = K12RegistrationForm()
    return render(
        request=request,
        template_name="tutor/sector_registration.html",
        context={
            "request": request,
            "form": form,
            "sector": "K-12",
        },
    )


def college_registration(request):
    logger.info(f"{request.user.username or request.user} called college_registration view")
    if "submit" in request.POST:
        logger.info(f"{request.user.username or request.user} submitted a POST request to college_registration")
        form = CollegeRegistrationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = User.objects.create_user(
                    email=form.cleaned_data["email"],
                    username=form.cleaned_data["username"],
                    password=form.cleaned_data["password"],
                )
                profile = Profile.objects.create(
                    user=user,
                    zip_code=form.cleaned_data["student_zip_code"],
                    can_speak_english=form.cleaned_data["student_speaks_english"],
                    site=form.cleaned_data["student_is_in_partner_program"],
                    site_location=form.cleaned_data["student_is_in_partner_program_location"],
                    account_type=AccountType.objects.get(display="College-Tutee"),
                )
            login(request, user)
            logger.info(f"registered {request.user.username or request.user} for college")
            return HttpResponseRedirect(reverse("tutor:onboard"))
    else:
        form = CollegeRegistrationForm()
    return render(
        request=request,
        template_name="tutor/sector_registration.html",
        context={
            "request": request,
            "form": form,
            "sector": "College",
        },
    )


def adult_education_registration(request):
    logger.info(f"{request.user.username or request.user} called adult_education_registration view")
    if "submit" in request.POST:
        logger.info(f"{request.user.username or request.user} submitted a POST request to adult_education_registration")
        form = AdultRegistrationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = User.objects.create_user(
                    email=form.cleaned_data["email"],
                    username=form.cleaned_data["username"],
                    password=form.cleaned_data["password"],
                )
                profile = Profile.objects.create(
                    user=user,
                    zip_code=form.cleaned_data["student_zip_code"],
                    can_speak_english=form.cleaned_data["student_speaks_english"],
                    site=form.cleaned_data["student_is_in_partner_program"],
                    site_location=form.cleaned_data["student_is_in_partner_program_location"],
                    account_type=AccountType.objects.get(display="Adult-Tutee")
                )
            login(request, user)
            logger.info(f"registered {request.user.username or request.user} for adult")
            return HttpResponseRedirect(reverse("tutor:onboard"))
    else:
        form = AdultRegistrationForm()
    return render(
        request=request,
        template_name="tutor/sector_registration.html",
        context={
            "request": request,
            "form": form,
            "sector": "Adult Education",
        },
    )


@login_required
def not_qualified(request):
    logger.info(f"{request.user.username or request.user} called not_qualified view")
    return render(
        request=request,
        template_name="tutor/not_qualified.html",
        context={
            "request": request,
        },
    )


@login_required
def onboard(request):
    logger.info(f"{request.user.username or request.user} called onboard view")
    account_type = request.user.profile.account_type.display
    if "Tutee" in account_type:
        if request.user.profile.site is None and not is_allowed_zip_code(
            request.user.profile.zip_code
        ):
            return HttpResponseRedirect(reverse("tutor:not-qualified"))
    if account_type == "K-12-Tutee":
        return k_12_onboard(request)
    if account_type == "College-Tutee":
        return college_onboard(request)
    if account_type == "Adult-Tutee":
        return adult_onboard(request)
    if account_type == "Tutor":
        return tutor_onboard(request)
    return HttpResponse(
        f"Site does not yet support onboarding account type: {account_type}"
    )


@login_required
def request(request):
    logger.info(f"{request.user.username or request.user} called request view")
    account_type = request.user.profile.account_type.display
    if (account_type == "K-12-Tutee" or account_type == "College-Tutee" or account_type == "Adult-Tutee"):
        return student_request_manage(request)
    if account_type == "Tutor":
        return manage(request)
    if account_type == "Program-Coordinator":
        return HttpResponseRedirect(reverse("tutor:site_log"))
    return HttpResponse(
        f"Site does not yet support requests for account type: {account_type}"
    )


@login_required
def tutor_onboard(request):
    logger.info(f"{request.user.username or request.user} called tutor_onboard view")

    if "submit" in request.POST:
        logger.info(f"{request.user.username or request.user} submitted a POST request to tutor_onboard")
        form = TutorOnboardingForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                profile = request.user.profile
                profile.full_name = form.cleaned_data["full_name"]
                profile.nickname = form.cleaned_data["nickname"]
                profile.phone_number = form.cleaned_data["phone_number"]
                profile.available.add(*form.cleaned_data["availability"])
                profile.gender = form.cleaned_data["gender"]
                profile.pronouns = form.cleaned_data["pronouns"]
                profile.ethnicity = form.cleaned_data["ethnicity"]
                profile.offered_sectors.add(*form.cleaned_data["offered_sectors"])
                profile.offered_subjects.add(*form.cleaned_data["offered_subjects"])
                profile.tutee_contact = form.cleaned_data["tutee_contact"]
                profile.sms_notifications = form.cleaned_data["sms_notifications"]
                profile.onboarded = True
                profile.site = form.cleaned_data["site"]
                profile.site_location = form.cleaned_data["site_location"]
                profile.tutor_monthly_volunteer = form.cleaned_data["monthly"]
                profile.save()
            if form.cleaned_data["training_code"] == settings.TRAINING_CODE:
                Orientation1.objects.create(user=request.user)
                Orientation2.objects.create(user=request.user)
                Orientation3.objects.create(user=request.user)
                Orientation4.objects.create(user=request.user)
                LiveSession.objects.create(user=request.user)
            logger.info(f"onboarded tutor {request.user.username or request.user}")
            if form.cleaned_data["monthly"]:
                return HttpResponseRedirect(reverse("tutor:tutor-onboard-monthly"))
            else:
                return HttpResponseRedirect(reverse("tutor:tutor-onboard-weekly"))
    else:
        form = TutorOnboardingForm()
    return render(
        request=request,
        template_name="tutor/tutor_onboard.html",
        context={
            "request": request,
            "form": form,
        },
    )


@login_required
def tutor_onboard_monthly(request):
    logger.info(f"{request.user.username or request.user} called tutor_onboard_monthly view")

    tutor_monthly, _ = TutorOfferedMonthlyHours.objects.get_or_create(user=request.user)
    monthly_form = TutorMonthlyHoursForm(request.POST or None, instance=tutor_monthly)
    current_month_form = TutorCurrentMonthlyHours(request=request.POST or None, instance=tutor_monthly, field_name=TutorOfferedMonthlyHours.get_current_month_field_name())

    if "submit" in request.POST:
        logger.info(f"{request.user.username or request.user} submitted a POST request to tutor_onboard_monthly")
        
        if monthly_form.is_valid():
            monthly_form.save()
            logger.info(f"{request.user.username or request.user} saved tutor_onboard_monthly monthly_form settings")

        if current_month_form.is_valid():
            current_month_form.save()
            logger.info(f"{request.user.username or request.user} saved tutor_onboard_monthly current_month_form settings")

        if monthly_form.is_valid() and current_month_form.is_valid():
            return HttpResponseRedirect(reverse("tutor:training"))
        messages.error(request, str(monthly_form.errors) + str(current_month_form.errors))

    return render(
        request=request,
        template_name="tutor/tutor_onboard_monthly.html",
        context={
            "request": request,
            "form": monthly_form,
            "form_current": current_month_form,
        },
    )


@login_required
def tutor_onboard_weekly(request):
    logger.info(f"{request.user.username or request.user} called tutor_onboard_weekly view")

    profile = request.user.profile
    form = TutorWeeklyHoursForm(request.POST or None, instance=profile)

    if "submit_weekly" in request.POST:
        logger.info(f"{request.user.username or request.user} submitted a POST request to tutor_onboard_weekly")
        if form.is_valid():
            form.save()
            logger.info(f"{request.user.username or request.user} saved tutor_onboard_weekly settings")
            return HttpResponseRedirect(reverse("tutor:training"))
        messages.error(request, str(form.errors))

    return render(
        request=request,
        template_name="tutor/tutor_onboard_weekly.html",
        context={
            "request": request,
            "form": form,
        },
    )


@login_required
def k_12_onboard(request):
    logger.info(f"{request.user.username or request.user} called k_12_onboard view")
    if "submit" in request.POST:
        logger.info(f"{request.user.username or request.user} submitted a POST request to k_12_onboard")
        form = K12OnboardingForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                profile = request.user.profile
                profile.full_name = form.cleaned_data["student_full_name"]
                profile.nickname = form.cleaned_data["student_nickname"]
                profile.phone_number = form.cleaned_data["parent_phone_number"]
                profile.available.add(*form.cleaned_data["availability"])
                profile.gender = form.cleaned_data["gender"]
                profile.pronouns = form.cleaned_data["pronouns"]
                profile.ethnicity = form.cleaned_data["ethnicity"]
                profile.sector = form.cleaned_data["sector"]
                profile.used_tutoring_before = form.cleaned_data["used_tutoring_before"]
                profile.tutoring_reason = form.cleaned_data["tutoring_reason"]
                profile.onboarded = True
                profile.save()
                first_request = TutorRequest.objects.create(
                    user=request.user,
                    timestamp=timezone.now(),
                    subject=form.cleaned_data["subject"],
                    notes=form.cleaned_data["notes"],
                )
            logger.info(f"onboarded {request.user.username or request.user} for K12")
            return HttpResponseRedirect(reverse("tutor:request"))
    else:
        form = K12OnboardingForm()
    return render(
        request=request,
        template_name="tutor/sector_onboard.html",
        context={
            "request": request,
            "form": form,
            "sector": "K-12",
        },
    )


@login_required
def college_onboard(request):
    logger.info(f"{request.user.username or request.user} called college_onboard view")
    if "submit" in request.POST:
        logger.info(f"{request.user.username or request.user} submitted a POST request to college_onboard")
        form = CollegeOnboardingForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                profile = request.user.profile
                profile.full_name = form.cleaned_data["full_name"]
                profile.nickname = form.cleaned_data["nickname"]
                profile.phone_number = form.cleaned_data["phone_number"]
                profile.available.add(*form.cleaned_data["availability"])
                profile.gender = form.cleaned_data["gender"]
                profile.pronouns = form.cleaned_data["pronouns"]
                profile.ethnicity = form.cleaned_data["ethnicity"]
                profile.sector = Sector.objects.get(display="College")
                profile.used_tutoring_before = form.cleaned_data["used_tutoring_before"]
                profile.tutoring_reason = form.cleaned_data["tutoring_reason"]
                profile.onboarded = True
                profile.save()
                first_request = TutorRequest.objects.create(
                    user=request.user,
                    timestamp=timezone.now(),
                    subject=form.cleaned_data["subject"],
                    notes=form.cleaned_data["notes"],
                )
            logger.info(f"onboarded {request.user.username or request.user} for college")
            return HttpResponseRedirect(reverse("tutor:request"))
    else:
        form = CollegeOnboardingForm()
    return render(
        request=request,
        template_name="tutor/sector_onboard.html",
        context={
            "request": request,
            "form": form,
            "sector": "College",
        },
    )

@login_required
def adult_onboard(request):
    logger.info(f"{request.user.username or request.user} called adult_onboard view")
    if "submit" in request.POST:
        logger.info(f"{request.user.username or request.user} submitted a POST request to adult_onboard")
        form = AdultOnboardingForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                profile = request.user.profile
                profile.full_name = form.cleaned_data["full_name"]
                profile.nickname = form.cleaned_data["nickname"]
                profile.phone_number = form.cleaned_data["phone_number"]
                profile.available.add(*form.cleaned_data['availability'])
                profile.gender = form.cleaned_data["gender"]
                profile.pronouns = form.cleaned_data["pronouns"]
                profile.ethnicity = form.cleaned_data["ethnicity"]
                profile.sector = Sector.objects.get(display="Adult Education")
                profile.used_tutoring_before = form.cleaned_data["used_tutoring_before"]
                profile.tutoring_reason = form.cleaned_data["tutoring_reason"]
                profile.onboarded = True
                profile.save()
                first_request = TutorRequest.objects.create(
                    user=request.user,
                    timestamp=timezone.now(),
                    subject=form.cleaned_data["subject"],
                    notes=form.cleaned_data["notes"],
                )
            logger.info(f"onboarded {request.user.username or request.user} for adult")
            return HttpResponseRedirect(reverse("tutor:request"))
    else:
        form = AdultOnboardingForm()
    return render(
        request=request,
        template_name="tutor/sector_onboard.html",
        context={
            "request": request,
            "form": form,
            "sector": "Adult Education",
        },
    )


@login_required
def tutor_request(request):
    logger.info(f"{request.user.username or request.user} called tutor_request view")
    return HttpResponseRedirect(reverse("tutor:manage"))


def submit_new_student_request(instance, tutee):
    logger.info(f"submit_new_student_request function called for {tutee}")
    instance.timestamp = timezone.now()
    instance.active = True
    instance.user = tutee
    instance.save()
    logger.info(f"created a new tutor request for {tutee}")


@login_required
def student_request_new(request):
    logger.info(f"{request.user.username or request.user} called student_request_new view")
    tickets_due = len(get_requests_requiring_exit_ticket(request.user))

    form = TutorRequestForm(user=request.user)
    if "submit" in request.POST:
        logger.info(f"{request.user.username or request.user} submitted a POST request to student_request_new")
        form = TutorRequestForm(request.POST, user=request.user)
        if form.is_valid():
            instance = form.save(commit=False)
            submit_new_student_request(instance, tutee=request.user)
            messages.success(request, "Your request has been added")
            logger.info(f"{request.user.username or request.user} created a new tutor request")
            return HttpResponseRedirect(reverse("tutor:request-manage"))

    requests = TutorRequest.objects.filter(user=request.user, active=True)
    num_active_requests = len(requests)

    template = "tutor/tutor_request.html"

    return render(
        request=request,
        template_name=template,
        context={
            "request": request,
            "name": request.user.profile.nickname or request.user.profile.full_name,
            "form": form,
            "page": "request",
            "memberships": MeetingMembership.objects.filter(user=request.user),
            "num_active_requests": num_active_requests,
            "tickets_due": tickets_due,
        },
    )


@login_required
def student_request_manage(request):
    logger.info(f"{request.user.username or request.user} called student_request_manage view")
    account_type = request.user.profile.account_type.display
    if account_type == "Tutor":
        return HttpResponseRedirect(reverse("tutor:request"))

    #Find which meeting membership should be rated
    unrated_meetings = MeetingMembership.objects.filter(
        rate=None, meeting__stop_datetime__isnull=False,
        meeting__stop_datetime__gt = dt.datetime(2022, 12, 14, tzinfo=pytz.UTC),
        user = request.user
    )

    if unrated_meetings:
        unrated_meeting = unrated_meetings.first()
        return HttpResponseRedirect(reverse(
            "tutor:clock_rate",
            kwargs={"unrated_meeting_id":unrated_meeting.id},
        ))


    if "delete" in request.POST:
        logger.info(f"{request.user.username or request.user} submitted a delete POST request to student_request_manage")
        form = TutorRequestUpdateForm(request.POST, user=request.user)
        if form.is_valid():
            # This seems hacky but not sure of a better way at the moment
            # Also not that secure, someone could technically send someone else's
            _, pk = request.POST["delete"].split("-")
            instance = TutorRequest.objects.get(pk=pk, user=request.user)
            cancel_request(instance, reason="User")
            messages.error(request, "Your request has been cancelled")
        return HttpResponseRedirect(reverse("tutor:request-manage"))

    if "update" in request.POST:
        logger.info(f"{request.user.username or request.user} submitted an update POST request to student_request_manage")
        form = TutorRequestUpdateForm(request.POST, user=request.user)
        if form.is_valid():
            _, pk = request.POST["update"].split("-")
            instance = TutorRequest.objects.get(pk=pk, user=request.user)
            instance.notes = form.cleaned_data["notes"]
            instance.save()
            messages.success(request, "Your request has been updated")
        return HttpResponseRedirect(reverse("tutor:request-manage"))

    requests = TutorRequest.objects.filter(
        Q(user=request.user, active=True) &
        (Q(meeting__isnull=True) | Q(meeting__scheduled_start__gt=timezone.now()-dt.timedelta(days=3)))
    )
    request_forms = [
        TutorRequestUpdateForm(
            instance=request,
            user=request.user
        )
        for request in requests
    ]
    num_active_requests = len(requests)

    return render(
        request=request,
        template_name="tutor/tutor_request.html",
        context={
            "request": request,
            "name": request.user.profile.nickname or request.user.profile.full_name,
            "request_forms": request_forms,
            "page": "manage",
            "num_active_requests": num_active_requests,
            "time": timezone.localtime(),
        },
    )


def cancel_memberships(memberships, reason, keep_meeting=False, call_source=None):
    # Cancels memberships, updates meetings, and notifies relevant members
    logger.info(f"cancel_memberships CALLED ({call_source}) {list(memberships.values_list('pk', flat=True))}, reason={reason}, keep_meeting={keep_meeting}")

    meeting_ids = []
    confirmed_meeting_ids = [] # Meetings that had at least one confirmed student
    for membership in memberships:
        logger.info(f"cancel_memberships ({call_source}): cancelling membership #{membership.pk} {membership}")
        meeting = membership.meeting

        if meeting.start_datetime: # Meeting has already happened
            logger.info(f"cancel_memberships ({call_source}): #{membership.pk} meeting already happened")
            continue

        meeting_ids.append(meeting.id)

        # If user is a tutee, remove meeting from the request
        # Keep meeting attached to request if tutee is cancelling the request
        if membership.user_role == "Tutee" and not keep_meeting:
            try:
                related_request = TutorRequest.objects.get(user=membership.user, meeting=meeting)
                related_request.meeting = None
                related_request.save()
            except TutorRequest.DoesNotExist:
                pass
        if ((membership.user_role == "Tutee" and membership.status == "Confirmed") or
        (meeting.meetingmembership_set.filter(user_role="Tutor", status="Confirmed"))):
            confirmed_meeting_ids.append(meeting.id)

        membership.status = "Cancelled"
        membership.cancel_reason = reason
        membership.cancel_timestamp = timezone.now()
        membership.save()
        logger.info(f"cancel_memberships ({call_source}): MeetingMembership #{membership.pk} set status=Cancelled, cancel_reason={reason}")

        active_tutor_memberships = meeting.meetingmembership_set.filter(
            Q(user_role="Tutor") & ~Q(status="Cancelled"))
        active_tutee_memberships = meeting.meetingmembership_set.filter(
            Q(user_role="Tutee") & ~Q(status="Cancelled"))

        # If either tutor count or tutee count becomes 0, meeting becomes inactive
        if not active_tutor_memberships or not active_tutee_memberships:
            meeting.active = False
            meeting.save()
            logger.info(f"cancel_memberships ({call_source}): Meeting #{meeting.pk} set active=False")

            # If there are active tutees in the meeting, remove the meeting from their requests
            if active_tutee_memberships:
                tutor_requests = TutorRequest.objects.filter(meeting=meeting)
                for tutor_request in tutor_requests:
                    tutor_request.meeting = None
                    tutor_request.save()
                    logger.info(f"cancel_memberships ({call_source}): TutorRequest #{tutor_request.pk} meeting=None")

    # After cancelling all memberships that have been passed,
    # notify the remaining active members if their meeting has been cancelled
    meetings = Meeting.objects.filter(id__in=meeting_ids).distinct()
    confirmed_meetings = Meeting.objects.filter(id__in=confirmed_meeting_ids).distinct()
    for meeting in meetings:
        if meeting.active or meeting.scheduled_start < timezone.now():
            continue

        active_memberships = meeting.meetingmembership_set.filter(~Q(status="Cancelled"))
        active_tutors = User.objects.filter(
            membership__in=active_memberships,
            membership__user_role="Tutor"
        ).distinct()
        active_tutees = User.objects.filter(
            membership__in=active_memberships,
            membership__user_role="Tutee"
        ).distinct()

        if active_tutees:
            logger.info(f"cancel_memberships ({call_source}): Meeting #{meeting.pk}, active tutees {list(active_tutees.values_list('pk', flat=True))}")
            notify_member_cancellation(active_tutees, call_source=call_source)
        # Only notify tutors if they received match notification when student confirmed
        if active_tutors and meeting in confirmed_meetings:
            logger.info(f"cancel_memberships ({call_source}): Meeting #{meeting.pk}, active tutors {list(active_tutors.values_list('pk', flat=True))}")
            notify_member_cancellation(active_tutors, call_source=call_source)

    logger.info(f"cancel_memberships ({call_source}) COMPLETE: cancelled MeetingMembership instances {list(memberships.values_list('pk', flat=True))}")


def cancel_requests_by_membership(memberships, reason, call_source=None):
    logger.info(f"cancel_requests_by_membership CALLED ({call_source}), {list(memberships.values_list('pk', flat=True))}, reason={reason}")
    for membership in memberships:
        related_request = TutorRequest.objects.get(user=membership.user, meeting=membership.meeting)
        cancel_request(related_request, reason, call_source=call_source)
        logger.info(f"cancel_requests_by_membership ({call_source}): cancelled request for membership #{membership.pk}, request #{related_request.pk}")
    logger.info(f"cancel_requests_by_membership ({call_source}) COMPLETE")


def cancel_request(tutor_request, reason, call_source=None):
    logger.info(f"cancel_request CALLED ({call_source}) #{tutor_request.pk} {tutor_request}, reason={reason}")
    tutor_request.active = False
    tutor_request.inactive_timestamp = timezone.now()
    tutor_request.cancel_reason = reason
    tutor_request.save()
    logger.info(f"cancel_request ({call_source}): saved TutorRequest active=False, cancel_reason={reason}")

    # If request has been fulfilled by a meeting, cancel membership but keep meeting attached to request
    meeting = tutor_request.meeting
    if meeting:
        # If meeting has not happened and before scheduled start (if after start, don't cancel membership)
        if not meeting.start_datetime and not meeting.past_start():
            logger.info(f"cancel_request ({call_source}): cancelling membership for meeting #{meeting.pk} {meeting}")
            membership_queryset = (MeetingMembership.objects
                .filter(meeting=meeting, user=tutor_request.user))
            cancel_memberships(membership_queryset, reason="Cancelled Request", keep_meeting=True, call_source=call_source)
    logger.info(f"cancel_request ({call_source}) COMPLETE #{tutor_request.pk}")


def confirm_membership(membership, call_source=None):
    logger.info(f"confirm_membership CALLED ({call_source}), {membership.pk} {membership}")
    membership.status = "Confirmed"
    membership.confirmation_timestamp = timezone.now()
    membership.save()
    logger.info(f"confirm_membership ({call_source}): saved MeetingMembership status")
    if membership.user_role == "Tutee":
        notify_tutor_meeting(membership, call_source)
    logger.info(f"confirm_membership COMPLETE #{membership.pk}: {membership}")


@login_required
def meeting(request):
    logger.info(f"{request.user.username or request.user} called meeting view")
    user = request.user

    meeting_id = request.GET.get("id")
    try:
        meeting = Meeting.objects.get(pk=meeting_id)
    except Meeting.DoesNotExist:
        return HttpResponseRedirect(reverse('tutor:manage'))

    try:
        membership = meeting.meetingmembership_set.get(user=user)
    except MeetingMembership.DoesNotExist:
        return HttpResponseRedirect(reverse('tutor:manage'))

    time_limit = timezone.localtime(membership.confirmation_limit)

    confirm_form = ConfirmMeetingForm()
    repeat_form = RepeatMeetingForm()
    cancel_form = SpecificCancelMeetingForm()
    if user not in meeting.members.all():
        raise PermissionDenied
    if "confirm" in request.POST:
        logger.info(f"{request.user.username or request.user} submitted a confirm POST request to meeting")
        form = ConfirmMeetingForm(request.POST)
        if form.is_valid():
            confirm_membership(membership)
    if "cancel" in request.POST:
        logger.info(f"{request.user.username or request.user} submitted a cancel POST request to meeting")
        form = SpecificCancelMeetingForm(request.POST)
        if form.is_valid():
            membership_queryset = MeetingMembership.objects.filter(id=membership.id)
            cancel_memberships(membership_queryset, reason="User", call_source="meeting")
            return HttpResponseRedirect(reverse('tutor:manage'))
        
    if "repeat" in request.POST:
        logger.info(f"{request.user.username or request.user} submitted a repeat POST request to meeting")
        form = RepeatMeetingForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                follow_up_meeting = create_repeat(meeting, User.objects.filter(id=user.id))
                notify_tutor_repeat_scheduled(follow_up_meeting.meetingmembership_set.filter(user_role="Tutor").first().user)
                messages.success(request, f"Repeat meeting has been scheduled for {follow_up_meeting.scheduled_start.strftime('%x')}")
                return HttpResponseRedirect(reverse("tutor:request"))
    current_time = timezone.now()
    if membership.can_confirm() and membership.meeting.can_confirm():
        messages.warning(request, "You must confirm you will attend this meeting")
    if membership.status == "Confirmed" and meeting.upcoming():
        messages.success(request, "You have confirmed you will attend this meeting")
    if membership.status == "Cancelled":
        messages.error(request, "You have cancelled your attendance of this meeting")
    if membership.status == "Requested Repeat":
        messages.success(request, "You have requested a repeat meeting")
    if meeting.can_repeat() and membership.can_repeat():
        messages.warning(
            request, "This meeting will expire if you do not reschedule it"
        )
    return render(
        request=request,
        template_name="tutor/meeting.html",
        context={
            "request": request,
            "membership": membership,
            "meeting": meeting,
            "current_time": timezone.now(),
            "confirm_form": confirm_form,
            "repeat_form": repeat_form,
            "cancel_form": cancel_form,
            "time_limit": time_limit,
        },
    )


def tutor_redirect(request):
    logger.info(f"{request.user.username or request.user} called tutor_redirect view")
    return HttpResponseRedirect("/register/")


def login_redirect(request):
    logger.info(f"{request.user.username or request.user} called login_redirect view")
    return HttpResponseRedirect("/login/")


def create_repeat(meeting, students, tutor_must_confirm=True):
    logger.info(f"create_repeat function called for {meeting}")
    student_memberships = MeetingMembership.objects.filter(user__in=students, meeting=meeting)
    for membership in student_memberships:
        membership.status = "Requested Repeat"
        membership.save()
    follow_up_meeting = meeting.follow_up_meeting

    if follow_up_meeting is None:
        # Create a new follow up meeting
        follow_up_meeting = Meeting.objects.create(
            subject=meeting.subject,
            scheduled_time_slot=meeting.scheduled_time_slot,
            scheduled_start=meeting.scheduled_time_slot.next_datetime_nearest(),
        )
        tutor = meeting.meetingmembership_set.get(
            user__profile__account_type=AccountType.objects.get(
                display="Tutor"
            )
        ).user
        # Copy over memberships
        if tutor_must_confirm:
            follow_up_meeting.members.add(tutor, through_defaults={'user_role': 'Tutor'})
        else:
            follow_up_meeting.members.add(tutor, through_defaults={
                'user_role': 'Tutor',
                'status': 'Confirmed',
                'confirmation_timestamp': timezone.now(),
            })
        
        for student in students:
            follow_up_meeting.members.add(student, through_defaults={
                'user_role': 'Tutee',
                'status': 'Confirmed',
                'confirmation_timestamp': timezone.now(),
            })
        
            # Modify request
            try:
                tutor_request = TutorRequest.objects.get(user=student, meeting=meeting)
                tutor_request.meeting = follow_up_meeting
                tutor_request.save()
            except TutorRequest.DoesNotExist:
                pass

        # Modify original meeting to point to new one
        meeting.follow_up_meeting = follow_up_meeting
        meeting.save()

    else:
        # Add to existing follow up meeting
        for student in students:
            follow_up_meeting.members.add(student, through_defaults={
                'user_role': 'Tutee',
                'status': 'Confirmed',
                'confirmation_timestamp': timezone.now(),
            })
            
            try:
                tutor_request = TutorRequest.objects.get(user=student, meeting=meeting)
                tutor_request.meeting = follow_up_meeting
                tutor_request.save()
            except TutorRequest.DoesNotExist:
                pass
    return follow_up_meeting


def register(request):
    if mobile(request):
        is_mobile = True
    else:
        is_mobile = False
    
    print(is_mobile)
    logger.info(f"{request.user.username or request.user} called register view")
    return render(
        request=request,
        template_name="tutor/register.html",
        context={
            "user": request.user,
        },
    )


def home(request):
    logger.info(f"{request.user.username or request.user} called home view")
    if request.user.is_anonymous:
        return HttpResponseRedirect("/register")
    if not request.user.profile.onboarded:
        return HttpResponseRedirect(reverse("tutor:onboard"))
    if request.user.profile.account_type.display == "Tutor":
        # slightly wasteful since training page will do the same queries
        if get_tutor_training_stage(request.user) != "finished":
            return HttpResponseRedirect(reverse("tutor:orientation"))
        open_meetings = request.user.meeting_set.exclude(start_datetime=None).filter(
            stop_datetime=None
        )
        if open_meetings:
            return HttpResponseRedirect(reverse("tutor:clock"))

        unrated_meetings = MeetingMembership.objects.filter(
            rate=None, meeting__stop_datetime__isnull=False,
            meeting__stop_datetime__gt = dt.datetime(2022, 11, 1, tzinfo=pytz.UTC),
            user = request.user
        )

        if unrated_meetings:
            return HttpResponseRedirect(reverse("tutor:clock"))

    return HttpResponseRedirect(reverse("tutor:request"))


@login_required
def add_student(request):
    if request.method == 'GET':
        id = request.GET.get('id')
        student = User.objects.get(id = id)
        #print(User.objects.filter(student_associate__student = student),11)
        if (not ConnectedStudent.objects.filter(student=student, tutor=request.user)):
            o = ConnectedStudent.objects.create(student=student,tutor=request.user)
            o.save()
        #response_data = 'successful!'
        return HttpResponse(
        )


def directory(request):
    logger.info(f"{request.user.username or request.user} called directory view")
    site_id = request.GET.get("site_id")
    form = DirectoryForm(site_id=site_id,user = request.user)
    search_string = request.GET.get('search')
    result = ''
    updated_result = []
    tutee_types = ["K-12-Tutee", "College-Tutee", "Adult-Tutee"]
    if search_string:
        tutee_types = ["K-12-Tutee", "College-Tutee", "Adult-Tutee"]
        result = User.objects.filter(profile__account_type__display__in=tutee_types) \
            .filter(Q(email = search_string) | Q(profile__phone_number = search_string) |
                Q(profile__full_name__icontains = search_string)).select_related("profile")\
            .select_related("profile__site_location", "profile__site").all()\
            .values('id','profile__full_name','email','profile__phone_number',
                "profile__site_location__display", "profile__site__display")

        for r in result:
            curr = r.copy()
            if curr["profile__phone_number"]:
                curr["profile__phone_number"] = "*******" + curr["profile__phone_number"][-4:]
            updated_result.append(curr)   
    try:
        if request.user.backgroundcheckrequest.status != "Approved":
            raise PermissionDenied
    except BackgroundCheckRequest.DoesNotExist:
        raise PermissionDenied
    if "submit" in request.POST:
        logger.info(f"{request.user.username or request.user} submitted a POST request to directory")
        form = DirectoryForm(request.POST, site_id=site_id, user = request.user)
        if form.is_valid():
            users = form.cleaned_data["selected_users"] 
            subject = form.cleaned_data["subject"]
            now = timezone.now()
            meeting = Meeting.objects.create(
                subject=subject,
                scheduled_time_slot=TimeSlot.for_current_time(),
                scheduled_start=now,
                start_datetime=now,
            )
            meeting.members.add(request.user, through_defaults={'user_role': 'Tutor', 'status': 'Confirmed'})
            meeting.members.add(*users, through_defaults={'user_role': 'Tutee', 'status': 'Confirmed'})
            ConnectedStudent.objects.filter(tutor=request.user).delete()
            return HttpResponseRedirect(reverse("tutor:clock"))
    return render(
        request=request,
        template_name="tutor/directory.html",
        context={
            "form": form,
            "search_result": updated_result,
            "sites": Site.objects.all(),
            "site_id": int(site_id) if site_id is not None else None,
        },
    )



@login_required
def unfulfilled_requests(request):
    logger.info(f"{request.user.username or request.user} called unfulfilled_requests view")
    if request.user.profile.account_type.display != "Tutor":
        raise PermissionDenied
    if get_tutor_training_stage(request.user) != "finished":
        raise PermissionDenied

    unfulfilled_requests = get_unfulfilled_requests(request.user)
    
    return render(
        request=request,
        template_name="tutor/unfulfilled_requests.html",
        context={
            "unfulfilled_requests": unfulfilled_requests,
            "now": timezone.now(),
        },
    )


@login_required
def tutor_match(request):
    logger.info(f"{request.user.username or request.user} called tutor_match view")
    if request.user.profile.account_type.display != "Tutor":
        raise PermissionDenied
    if get_tutor_training_stage(request.user) != "finished":
        raise PermissionDenied

    unfulfilled_requests = get_unfulfilled_requests(request.user)
    tutor_timeslots = request.user.profile.available.all()

    if "submit" in request.POST:
        logger.info(f"{request.user.username or request.user} submitted a POST request to tutor_match")
        return HttpResponseRedirect(reverse(
            "tutor:tutor-match-confirm",
            kwargs={
                "request_id": request.POST["request_id"],
                "timeslot_id": request.POST["timeslot_id"],
            },
        ))

    return render(
        request=request,
        template_name="tutor/tutor_match_timeslot.html",
        context={
            "unfulfilled_requests": unfulfilled_requests,
            "now": timezone.now(),
            "tutor_timeslots": tutor_timeslots,
        },
    )


@login_required
def tutor_match_confirm(request, request_id, timeslot_id):
    logger.info(f"{request.user.username or request.user} called tutor_match_confirm view")
    if request.user.profile.account_type.display != "Tutor":
        raise PermissionDenied
    if get_tutor_training_stage(request.user) != "finished":
        raise PermissionDenied

    student_request = TutorRequest.objects.get(id=request_id)
    timeslot = TimeSlot.objects.get(id=timeslot_id)

    # Request has already been fulfilled
    if student_request.meeting:
        request_already_fulfilled = True
    else:
        request_already_fulfilled = False

    # Student is no longer available for timeslot
    if timeslot not in student_request.user.profile.available.all():
        student_time_change = True
    else:
        student_time_change = False

    tutor_matches_timeslot = timeslot in request.user.profile.available.all()
    tutor_matches_subject = student_request.subject in request.user.profile.offered_subjects.all()
    tutor_matches_sector = student_request.user.profile.sector in request.user.profile.offered_sectors.all()

    form = TutorMatchConfirmForm(
        request.POST or None,
        tutor_matches_timeslot=tutor_matches_timeslot,
        tutor_matches_subject=tutor_matches_subject,
        tutor_matches_sector=tutor_matches_sector,
    )

    if "submit" in request.POST:
        logger.info(f"{request.user.username or request.user} submitted a POST request to tutor_match_confirm")
        match_by_tutor(request.user, student_request, timeslot)
        return HttpResponseRedirect(reverse("tutor:tutor-match-done"))

    return render(
        request=request,
        template_name="tutor/tutor_match_confirm.html",
        context={
            "student_request": student_request,
            "time": timeslot.next_datetime(),
            "form": form,
            "student_time_change": student_time_change,
            "request_already_fulfilled": request_already_fulfilled,
        },
    )


@login_required
def tutor_match_done(request):
    logger.info(f"{request.user.username or request.user} called tutor_match_done view")
    return render(
        request=request,
        template_name="tutor/tutor_match_done.html"
    )


def monthly_weekly_info(request):
    logger.info(f"{request.user.username or request.user} called monthly_weekly_info view")
    return render(
        request=request,
        template_name="tutor/monthly_weekly_info.html"
    )


@login_required
def admin_hours_forecast(request):
    logger.info(f"{request.user.username or request.user} called admin_hours_forecast view")

    if not request.user.is_superuser:
        raise PermissionDenied

    field_name = TutorOfferedMonthlyHours.get_current_month_field_name()
    offered_monthly = {}

    fields = TutorOfferedMonthlyHours._meta.get_fields()[4:]

    for field in fields:
        month_number = int(field.name.split("_")[1])
        year = int(field.name.split("_")[2])

        month_str = f"{month_name[month_number]} 20{str(year)}"

        offered_monthly[month_str] =  sum(list(TutorOfferedMonthlyHours.objects
            .filter(user__profile__account_type__display="Tutor", user__profile__tutor_monthly_volunteer=True)
            .values_list(field.name, flat=True)
        ))

    this_month = TutorOfferedMonthlyHours.objects.filter(**{f"{field_name}__gt": 0})

    return render(
        request=request,
        template_name="tutor/admin_hours_forecast.html",
        context={
            "offered_monthly": offered_monthly,
            "this_month": this_month,
        }
    )


@login_required
def orientation_1c(request):
    if (request.user.profile.account_type.display != "Tutor"):
        return HttpResponseRedirect(reverse("tutor:home"))

    user = request.user
    try:
        user.orientation1
        form = Orientation1ResultForm()
    except:
        form = Orientation1Form(request.POST or None)
        
    if "submit" in request.POST:
        if form.is_valid():
            form = form.save(commit=False)
            form.user = user
            form.completed = timezone.now()
            form.occupation = 0
            form.save() 
            return HttpResponseRedirect(reverse("tutor:orientation-1c"))
    return render(
        request = request,
        template_name="tutor/orientation_1c.html",
        context={
            "form": form,
            "tutor": user,
            "answer1": 1,
            "answer2": 1,
        },
    )

@login_required
def orientation_content(request):
    if (request.user.profile.account_type.display != "Tutor"):

        return HttpResponseRedirect(reverse("tutor:home"))
    return render(
        request = request,
        template_name="tutor/orientation_content.html",
    )

@login_required
def orientation_1h(request):
    if (request.user.profile.account_type.display != "Tutor"):

        return HttpResponseRedirect(reverse("tutor:home"))
    user = request.user
    try:
        user.orientation1
        form = Orientation1ResultForm()
    except:
        form = Orientation1Form(request.POST or None)

    if "submit" in request.POST:
        if form.is_valid():
            form = form.save(commit=False)
            form.user = user
            form.completed = timezone.now()
            form.occupation = 1
            form.save() 
            return HttpResponseRedirect(reverse("tutor:orientation-1h"))
    return render(
        request = request,
        template_name="tutor/orientation_1h.html",
        context={
            "form": form,
            "tutor": user,
            "answer1": 1,
            "answer2": 0,
        },
    )

@login_required
def orientation_1r(request):
    if (request.user.profile.account_type.display != "Tutor"):

        return HttpResponseRedirect(reverse("tutor:home"))
    user = request.user
    try:
        user.orientation1
        form = Orientation1ResultForm()
    except:
        form = Orientation1Form(request.POST or None)
    if "submit" in request.POST:
        if form.is_valid():
            form = form.save(commit=False)
            form.user = user
            form.completed = timezone.now()
            form.occupation = 2
            form.save() 
            return HttpResponseRedirect(reverse("tutor:orientation-1r"))
    return render(
        request = request,
        template_name="tutor/orientation_1r.html",
        context={
            "form": form,
            "tutor": user,
            "answer1": 1,
            "answer2": 3,
        },
    )

@login_required
def orientation_1w(request):
    if (request.user.profile.account_type.display != "Tutor"):

        return HttpResponseRedirect(reverse("tutor:home"))
    user = request.user
    try:
        user.orientation1
        form = Orientation1ResultForm()
    except:
        form = Orientation1Form(request.POST or None)
    if "submit" in request.POST:
        if form.is_valid():
            form = form.save(commit=False)
            form.user = user
            form.completed = timezone.now()
            form.occupation = 3
            form.save() 
            return HttpResponseRedirect(reverse("tutor:orientation-1w"))
    return render(
        request = request,
        template_name="tutor/orientation_1w.html",
        context={
            "form": form,
            "tutor": user,
            "answer1": 1,
            "answer2": 2,
        },
    )

@login_required
def orientation_2(request):
    if (request.user.profile.account_type.display != "Tutor"):

        return HttpResponseRedirect(reverse("tutor:home"))
    user = request.user

    try:
        user.orientation2
        form = Orientation2ResultForm()
    except:
        form = Orientation2Form(request.POST or None)
    if "submit" in request.POST:
        if form.is_valid():
            form = form.save(commit=False)
            form.user = user
            form.completed = timezone.now()
            form.save() 
            return HttpResponseRedirect(reverse("tutor:orientation-2"))
    return render(
        request = request,
        template_name="tutor/orientation_2.html",
        context={
            "form": form,
            "tutor": user,
            "answer1": 0,
            "answer2": [0,1,2,3,4],
        },
    )

@login_required
def orientation_3(request):
    if (request.user.profile.account_type.display != "Tutor"):

        return HttpResponseRedirect(reverse("tutor:home"))
    user = request.user
    try:
        user.orientation3
        form = Orientation3ResultForm()
    except:
        form = Orientation3Form(request.POST or None)
    if "submit" in request.POST:
        if form.is_valid():
            form = form.save(commit=False)
            form.user = user
            form.completed = timezone.now()
            form.save() 
            return HttpResponseRedirect(reverse("tutor:orientation-3"))
    return render(
        request = request,
        template_name="tutor/orientation_3.html",
        context={
            "form": form,
            "tutor": user,
            "answer1": [0,1,2],
            "answer2": [0,1,2,3],
        },
    )

@login_required
def orientation_4(request):
    if (request.user.profile.account_type.display != "Tutor"):

        return HttpResponseRedirect(reverse("tutor:home"))
    user = request.user
    try:
        user.orientation4
        form = Orientation4ResultForm()
    except:
        form = Orientation4Form(request.POST or None)
    if "submit" in request.POST:
        if form.is_valid():
            form = form.save(commit=False)
            form.user = user
            form.completed = timezone.now()
            form.save() 
            return HttpResponseRedirect(reverse("tutor:orientation-4"))
    return render(
        request = request,
        template_name="tutor/orientation_4.html",
        context={
            "form": form,
            "tutor": user,
            "answer1": [0,2],
            "answer2": 2,
        },
    )

@login_required
def orientation_5(request):
    if (request.user.profile.account_type.display != "Tutor"):

        return HttpResponseRedirect(reverse("tutor:home"))
    user = request.user
    try:
        user.orientation5
        form = Orientation5ResultForm()
    except:
        form = Orientation5Form(request.POST or None)
    if "submit" in request.POST:
        if form.is_valid():
            form = form.save(commit=False)
            form.user = user
            form.completed = timezone.now()
            form.save() 
            return HttpResponseRedirect(reverse("tutor:orientation-5"))
    return render(
        request = request,
        template_name="tutor/orientation_5.html",
        context={
            "form": form,
            "tutor": user,
            "answer1": [0,1,3],
            "answer2": 1,
        },
    )

@login_required
def orientation_6(request):
    if (request.user.profile.account_type.display != "Tutor"):

        return HttpResponseRedirect(reverse("tutor:home"))
    user = request.user
    try:
        user.orientation6
        form = Orientation6ResultForm()
    except:
        form = Orientation6Form(request.POST or None)
    if "submit" in request.POST:
        if form.is_valid():
            form = form.save(commit=False)
            form.user = user
            form.completed = timezone.now()
            form.save() 
            return HttpResponseRedirect(reverse("tutor:orientation-6"))
    return render(
        request = request,
        template_name="tutor/orientation_6.html",
        context={
            "form": form,
            "tutor": user,
            "answer1": [0,2,3],
            "answer2": [0,1,3],
        },
    )

@login_required
def orientation_7(request):
    if (request.user.profile.account_type.display != "Tutor"):

        return HttpResponseRedirect(reverse("tutor:home"))
    user = request.user
    try:
        user.orientation7
        form = Orientation7ResultForm()
    except:
        form = Orientation7Form(request.POST or None)
    if "submit" in request.POST:
        if form.is_valid():
            form = form.save(commit=False)
            form.user = user
            form.completed = timezone.now()
            form.save() 
            return HttpResponseRedirect(reverse("tutor:orientation-7"))
    return render(
        request = request,
        template_name="tutor/orientation_7.html",
        context={
            "form": form,
            "tutor": user,
            "answer1": [0,2,3],
            "answer2": [0,2,3],
        },
    )

@login_required
def orientation_8(request):
    if (request.user.profile.account_type.display != "Tutor"):

        return HttpResponseRedirect(reverse("tutor:home"))
    user = request.user
    try:
        user.orientation8
        form = Orientation8ResultForm()
    except:
        form = Orientation8Form(request.POST or None)
    if "submit" in request.POST:
        if form.is_valid():
            form = form.save(commit=False)
            form.user = user
            form.completed = timezone.now()
            form.save() 
            return HttpResponseRedirect(reverse("tutor:orientation-8"))
    return render(
        request = request,
        template_name="tutor/orientation_8.html",
        context={
            "form": form,
            "tutor": user,
            "answer1": [0,1,2,3],
            "answer2": [0,1,3,4],
        },
    )

@login_required
def orientation_9(request):
    if (request.user.profile.account_type.display != "Tutor"):

        return HttpResponseRedirect(reverse("tutor:home"))
    user = request.user
    try:
        user.orientation9
        form = Orientation9ResultForm()
    except:
        form = Orientation9Form(request.POST or None)
    if "submit" in request.POST:
        if form.is_valid():
            form = form.save(commit=False)
            form.user = user
            form.completed = timezone.now()
            form.save() 
            return HttpResponseRedirect(reverse("tutor:orientation-9"))
    return render(
        request = request,
        template_name="tutor/orientation_9.html",
        context={
            "form": form,
            "tutor": user,
            "answer1": [0,1,4],
            "answer2": [1,2,3,4],
        },
    )

@login_required
def orientation_10(request):
    if (request.user.profile.account_type.display != "Tutor"):

        return HttpResponseRedirect(reverse("tutor:home"))
    user = request.user
    try:
        user.orientation10
        form = Orientation10ResultForm()
    except:
        form = Orientation10Form(request.POST or None)
    if "submit" in request.POST:
        if form.is_valid():
            form = form.save(commit=False)
            form.user = user
            form.completed = timezone.now()
            form.save() 
            return HttpResponseRedirect(reverse("tutor:orientation-10"))
    return render(
        request = request,
        template_name="tutor/orientation_10.html",
        context={
            "form": form,
            "tutor": user,
            "answer1": [0,2,3,4],
            "answer2": [0,1,3],
        },
    )

@login_required
def orientation_11(request):
    if (request.user.profile.account_type.display != "Tutor"):

        return HttpResponseRedirect(reverse("tutor:home"))
    user = request.user
    try:
        user.orientation11
        form = Orientation11ResultForm()
    except:
        form = Orientation11Form(request.POST or None)
    if "submit" in request.POST:
        if form.is_valid():
            form = form.save(commit=False)
            form.user = user
            form.completed = timezone.now()
            form.save() 
            return HttpResponseRedirect(reverse("tutor:orientation-11"))
    return render(
        request = request,
        template_name="tutor/orientation_11.html",
        context={
            "form": form,
            "tutor": user,
            "answer1": [1,2,3],
            "answer2": [0,1,2],
        },
    )

@login_required
def orientation_live_session(request):
    if (request.user.profile.account_type.display != "Tutor"):

        return HttpResponseRedirect(reverse("tutor:home"))
    form = OrientationLiveSession(request.POST or None)
    if "Submit" in request.POST:
        if form.is_valid():
            form = form.save(commit=False)
            form.user = request.user
            form.completed = timezone.now()
            form.save()
        return HttpResponseRedirect(reverse("tutor:live-training"))
    return render(
        request=request,
        template_name="tutor/live_training.html",
        context={
            "request": request,
            "form": form,
        },
    )

def mobile(request):
    """ returns true if the request comes from a mobile device """
    MOBILE_AGENT_RE = re.compile(r".*(iphone|mobile|androidtouch)", re.IGNORECASE)
    if MOBILE_AGENT_RE.match(request.META['HTTP_USER_AGENT']):
        return True
    else:
        return False


@login_required
def student_request_rerequest(request):

    past_meetings = get_rerequest_tutor(request.user)
    user = past_meetings.select_related('user').all()
    user = user.select_related('meeting').all().order_by("-meeting__start_datetime")
    requests = TutorRequest.objects.filter(user=request.user, active=True)
    num_active_requests = len(requests)

    template = "tutor/tutor_request.html"

    if "submit" in request.POST:
        
        rate = request.POST["rate"]
        meeting_id = request.POST["meeting"]
        meeting_update = MeetingMembership.objects.get(id=meeting_id)
        meeting_update.rate = rate
        meeting_update.save()
        return HttpResponseRedirect(reverse("tutor:request-rerequest"))
        
    
    if "request" in request.POST:
        requests = TutorRequest.objects.filter(
            Q(user=request.user, active=True)
        )
        num_requests = len(requests) + 1
        hours_per_subject = collections.Counter(r.subject for r in requests)
        hours_per_subject[Subject.objects.get(id=request.POST["subject"])] += 1
        num_allowed_requests = request.user.profile.num_allowed_requests
        num_allowed_subjects = request.user.profile.num_allowed_subjects
        num_allowed_hours_per_subject = request.user.profile.num_allowed_hours_per_subject

        if num_requests > num_allowed_requests:
            messages.error(request, f"You are only allowed up to {num_allowed_requests} active requests.")
            print(f"You are only allowed up to {num_allowed_requests} active requests.")
            return HttpResponseRedirect(reverse("tutor:request-rerequest"))
        if len(hours_per_subject) > num_allowed_subjects:
            messages.error(request, f"You are only allowed up to {num_allowed_subjects} different subject(s).")
            print(f"You are only allowed up to {num_allowed_subjects} different subject(s).")
            return HttpResponseRedirect(reverse("tutor:request-rerequest"))
        if max(hours_per_subject.values()) > num_allowed_hours_per_subject:
            messages.error(request, f"You are only allowed up to {num_allowed_hours_per_subject} requests per subject.")
            print(f"You are only allowed up to {num_allowed_hours_per_subject} requests per subject.")
            return HttpResponseRedirect(reverse("tutor:request-rerequest"))

        meeting = Meeting.objects.get(id=request.POST["meeting"])
        tutor = meeting.meetingmembership_set.get(
            user__profile__account_type=AccountType.objects.get(
                display="Tutor"
            )
        ).user

        tutee = meeting.meetingmembership_set.get(
            user__profile__account_type=AccountType.objects.get(
                Q(display="K-12-Tutee")
            )
        ).user

        follow_up_meeting = Meeting.objects.create(
            subject=Subject.objects.get(id=request.POST["subject"]),
            scheduled_time_slot=meeting.scheduled_time_slot,
            scheduled_start=meeting.scheduled_time_slot.next_datetime_nearest(),
        )

        follow_up_meeting.members.add(tutor, through_defaults={'user_role': 'Tutor'})
        follow_up_meeting.members.add(tutee, through_defaults={
            'user_role': 'Tutee', 
        })

        TutorRequest.objects.create(
            meeting = follow_up_meeting, 
            user = request.user, 
            notes = (f"Requested repeat from the meeting { meeting }"),
            timestamp = timezone.now(),
            subject = Subject.objects.get(id=request.POST["subject"]),
        )

        
        #print(request.POST['subject'])
        #notify_tutor_repeat_scheduled(follow_up_meeting.meetingmembership_set.filter(user_role="Tutor").first().user)
        #messages.success(request, f"Repeat meeting has been scheduled for {follow_up_meeting.scheduled_start.strftime('%x')}")
        return HttpResponseRedirect(reverse(
            "tutor:request", 
        ))

    return render(
        request=request,
        template_name=template,
        context={
            "request": request,
            "name": request.user.profile.nickname or request.user.profile.full_name,
            "page": "rerequest",
            "num_active_requests": num_active_requests,
            "past_meetings": user,
        },
    )

def past_meetings(request):
    past_meetings = get_rerequest_tutor(request.user)
    user = past_meetings.select_related('user').all()
    user = user.select_related('meeting').all().order_by("-meeting__start_datetime")
    
    return render(
        request=request,
        template_name="tutor/past_meetings.html",
        context={
            "request": request,
            "name": request.user.profile.nickname or request.user.profile.full_name,
            "past_meetings": user,
        },
    )
"""     meetings = Meeting.objects.filter(meetingmembership__user = request.user)
    calculated_meetings = meetings.annotate(
        count=Count('members'),

        ).filter(
            count__gte=1)

    print(calculated_meetings[0].members.all())  """
