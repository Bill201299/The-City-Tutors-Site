import datetime as dt
import calendar
from collections import defaultdict
import pytz

from django.contrib import admin
from django.db.models import fields, Count, F, Q, ExpressionWrapper, Sum, When, Case, DecimalField
from django.db.models.functions import Lower
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model
from django.urls import path, reverse
from django.template.response import TemplateResponse
from django.conf import settings
from django.utils import timezone
from django.utils.timezone import make_aware
from django.utils.safestring import mark_safe

from .views import get_tutor_training_stage
from .models import (
    ConnectedStudent,
    Issue,
    GeneralIssue,
    TuteeIssue,
    HarassIssue,
    Profile,
    BackgroundCheckRequest,
    TutorRequest,
    TuteeAssessment,
    OrientationTraining,
    TutorTraining,
    RoleplayTraining,
    Site,
    SiteLocation,
    Meeting,
    MeetingMembership,
    Subject,
    ExitTicket,
    ExitTicketDifficult,
    ExitTicketMedium,
    ExitTicketEasy,
    TutorOfferedMonthlyHours,
    get_account_types,
    get_nonzero_monthly_hours_filter_dict,
    Orientation1,
    Orientation2,
    Orientation3,
    Orientation4,
    Orientation5,
    Orientation6,
    Orientation7,
    Orientation8,
    Orientation9,
    Orientation10,
    Orientation11,
    LiveSession,
    Dashboard,
)

from django.db import connection, reset_queries

User = get_user_model()
admin.site.unregister(User)

naive = dt.datetime(2022, 5, 3, 0, 0)
aware = make_aware(naive, timezone=pytz.timezone("America/New_York"))


@admin.action(description='Offer subject', permissions=['change'])
def offer_subject(modeladmin, request, queryset):
    for subject in queryset:
        subject.offered = True
        subject.save()


@admin.action(description='Remove subject offering', permissions=['change'])
def remove_offer_subject(modeladmin, request, queryset):
    for subject in queryset:
        subject.offered = False
        subject.save()


class SubjectAdmin(admin.ModelAdmin):
    list_filter = [
        "sector",
        "offered",
    ]
    list_display = (
        "display",
        "sector",
        "group_sessions",
        "offered",
    )
    ordering = ['sector']
    search_fields = ["display"]
    actions = [offer_subject, remove_offer_subject]

class ConnectedStudentAdmin(admin.ModelAdmin):
    model = ConnectedStudent
    fields = ["tutor", "student"]

@admin.action(description='Resolve', permissions=['change'])
def resolve_issues(modeladmin, request, queryset):
    for issue in queryset:
        issue.status = 'Resolved'
        issue.save()


@admin.action(description='Change to attention needed', permissions=['change'])
def convert_issues_attention_needed(modeladmin, request, queryset):
    for issue in queryset:
        issue.status = 'AttentionNeeded'
        issue.save()


@admin.action(description='Change to in progress', permissions=['change'])
def convert_issues_in_progress(modeladmin, request, queryset):
    for issue in queryset:
        issue.status = 'InProgress'
        issue.save()


class IssueAdmin(admin.ModelAdmin):
    model = Issue
    exclude = ['id']
    ordering = ['timestamp']
    search_fields = ['submitter', 'description', 'contact_email']
    list_filter = ["status"]
    list_display = ['submitter', 'status', 'description', 'resolved']
    readonly_fields = ["type", "timestamp", "submitter", "contact_email"]
    actions = [resolve_issues, convert_issues_in_progress, convert_issues_attention_needed]

    def has_delete_permission(self, request, obj=None):
        return False

    def resolved(self, instance):
        return instance.status == 'Resolved'
    resolved.boolean = True


class ActiveMeetingFilter(admin.SimpleListFilter):
    title = "meeting status"
    parameter_name = "meeting"

    def lookups(self, request, model_admin):
        return (
            ("Active - ALL", "Active - ALL"),
            ("Active - Future", "Active - Future"),
            ("Active - Past", "Active - Past"),
            ("Active - Past (Absent)", "Active - Past (Absent)"),
            ("Active - Past (NO CLOCK IN)", "Active - Past (NO CLOCK IN)"),
            ("Active - Past (NO CLOCK OUT)", "Active - Past (NO CLOCK OUT)"),
            ("Active - Past (Duration Over 2.5h)", "Active - Past (Duration Over 2.5h)"),
            ("Active - Past (Duration Less Than 5m)", "Active - Past (Duration Less Than 5m)"),
            ("Inactive - ALL", "Inactive - ALL"),
            ("Inactive - Future", "Inactive - Future"),
            ("Inactive - Past", "Inactive - Past"),
        )

    def queryset(self, request, queryset):
        if self.value() == "Active - ALL":
            return queryset.filter(active=True)

        elif self.value() == "Active - Future":
            return queryset.filter(active=True, scheduled_start__gt=timezone.now())

        elif self.value() == "Active - Past":
            return queryset.filter(active=True, scheduled_start__lte=timezone.now())
        elif self.value() == "Active - Past (Absent)":
            return queryset.annotate(
                num_attendees=Count('attendance')
            ).filter(
                Q(active=True,stop_datetime__isnull=False) &
                Q(attendance__profile__account_type__display="Tutor") &
                Q(num_attendees__lte=1)
            )
        elif self.value() == "Active - Past (NO CLOCK IN)":
            return queryset.filter(
                active=True, scheduled_start__lte=timezone.now(), start_datetime__isnull=True,
            )
        elif self.value() == "Active - Past (NO CLOCK OUT)":
            return queryset.filter(
                active=True, scheduled_start__lte=timezone.now(), start_datetime__isnull=False, stop_datetime__isnull=True,
            )
        elif self.value() == "Active - Past (Duration Over 2.5h)":
            duration = ExpressionWrapper(F('stop_datetime') - F('start_datetime'), output_field=fields.DurationField())
            return queryset.annotate(duration=duration).filter(
                active=True, scheduled_start__lte=timezone.now(), duration__gt=dt.timedelta(hours=2, minutes=30),
            )
        elif self.value() == "Active - Past (Duration Less Than 5m)":
            duration = ExpressionWrapper(F('stop_datetime') - F('start_datetime'), output_field=fields.DurationField())
            return queryset.annotate(duration=duration).filter(
                active=True, scheduled_start__lte=timezone.now(), duration__lt=dt.timedelta(minutes=5),
            )
        elif self.value() == "Inactive - ALL":
            return queryset.filter(active=False)
        elif self.value() == "Inactive - Future":
            return queryset.filter(active=False, scheduled_start__gt=timezone.now())
        elif self.value() == "Inactive - Past":
            return queryset.filter(active=False, scheduled_start__lte=timezone.now())


class UserAdmin(UserAdmin):
    list_display = (
        "username",
        "email",
        "account_type",
        "profile_link",
    )

    list_filter = [
        "is_staff",
    ]
    ordering = [Lower('username')]
    search_fields = ["username", "profile__full_name", "profile__nickname", "email"]

    def account_type(self, user):
        return user.profile.account_type

    def profile_link(self, user):
        url = reverse("admin:tutor_profile_change", args=[user.profile.id])
        return mark_safe(f"<a href='{url}'>{user.profile}</a>")


class MembersInline(admin.TabularInline):
    model = MeetingMembership
    fields = [
        "user",
        "user_role",
        "status",
        "cancel_reason",
        "cancel_timestamp",
        "confirmation_timestamp",
        "created_at",
        "confirmation_limit"
    ]

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = ["user", "user_role", "created_at", "confirmation_limit"]
        if not request.user.is_superuser:
            readonly_fields.append("cancel_reason")
            readonly_fields.append("cancel_timestamp")
            readonly_fields.append("confirmation_timestamp")
            readonly_fields.append("user")
        return readonly_fields

    def get_extra(self, request, obj=None, **kwargs):
        return 0 if obj else 2

    def confirmation_limit(self, obj=None):
        current_tz = timezone.get_current_timezone()
        local = obj.confirmation_limit.astimezone(current_tz)
        return local


class TutorRequestInline(admin.TabularInline):
    model = TutorRequest

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = [f.name for f in self.model._meta.fields]
        return readonly_fields

    def get_extra(self, request, obj=None, **kwargs):
        return 0 if obj else 1


class MeetingAdmin(admin.ModelAdmin):
    list_display = [
        "tutees",
        "tutors",
        "meeting_status",
        "scheduled_start",
        "created_at",
        "active",
        "subject",
        "clocked_in",
        "follow_up_meeting_exists",
        "duration",
    ]
    list_filter = [
        ActiveMeetingFilter,
    ]
    readonly_fields = [
        "follow_up_meeting",
        "follow_up_meeting_link",
        "member_profile_links",
        "subject",
        "created_at",
        "attendance",
    ]
    search_fields = [
        "subject__display",
        "meetingmembership__user__username",
        "meetingmembership__user__profile__full_name",
        "meetingmembership__user__profile__nickname",
        "id",
    ]
    inlines = [MembersInline, TutorRequestInline]
    ordering = ["-scheduled_start"]
    filter_horizontal = ["attendance"]

    def has_add_permission(self, request, obj=None):
        return False

    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            (None, {
                'fields': (
                    'subject',
                    'created_at',
                    'scheduled_start',
                    'scheduled_time_slot',
                    'active',
                    'member_profile_links'
                )
            }),
        ]
        if obj:
            if obj.past_start() or obj.happened():
                fieldsets.append(
                    ('Clock Info', {
                        'fields': (
                            "start_datetime",
                            'stop_datetime',
                            'notes',
                            'follow_up_meeting',
                            'follow_up_meeting_link',
                            'attendance',
                        ),
                    })

                )
        return fieldsets

    def follow_up_meeting_exists(self, meeting):
        if meeting.follow_up_meeting:
            return meeting.follow_up_meeting.active
        else:
            return False
    follow_up_meeting_exists.boolean = True

    def clocked_in(self, meeting):
        return bool(meeting.start_datetime)
    clocked_in.boolean = True

    def duration(self, meeting):
        if meeting.stop_datetime:
            return meeting.stop_datetime - meeting.start_datetime

    def follow_up_meeting_link(self, meeting):
        url = reverse("admin:tutor_meeting_change", args=[meeting.follow_up_meeting.id])
        return mark_safe(f"<a href='{url}'>{meeting.follow_up_meeting}</a>")

    def member_profile_links(self, meeting):
        memberships = meeting.meetingmembership_set.all()
        member_profiles = Profile.objects.filter(user__membership__in=memberships)
        tag = ""
        for profile in member_profiles:
            url = reverse("admin:tutor_profile_change", args=[profile.id])
            tag += f"<a href='{url}'>{profile}</a><br>"
        return mark_safe(tag)

    def get_members_str(self, memberships):
        confirmed = User.objects.filter(
            Q(membership__in=memberships, membership__status="Requested Repeat") |
            Q(membership__in=memberships, membership__status="Confirmed") |
            Q(
                membership__in=memberships,
                membership__user_role="Tutor",
                membership__created_at__lt=aware,
                
                membership__status="Pending Confirmation",
            )
        )
        pending = User.objects.filter(
            Q(membership__in=memberships, membership__status="Pending Confirmation") &
            (
                Q(membership__user_role="Tutee") |
                Q(membership__created_at__gt=aware, membership__user_role="Tutor")
            )
        )
        cancelled = User.objects.filter(membership__in=memberships, membership__status="Cancelled")
        
        confirmed_str = ', '.join(str(user.profile) for user in confirmed)
        pending_str = ', '.join(str(user.profile) + "*" for user in pending)
        cancelled_str = f"({', '.join(str(user.profile) for user in cancelled)})" if cancelled else ""
        
        members = ', '.join(filter(None, [confirmed_str, pending_str, cancelled_str]))
        if members:
            return members
        else:
            return "[NONE]"

    def tutees(self, meeting):
        memberships = MeetingMembership.objects.filter(meeting=meeting, user_role="Tutee")
        return self.get_members_str(memberships)

    def tutors(self, meeting):
        memberships = MeetingMembership.objects.filter(meeting=meeting, user_role="Tutor")
        return self.get_members_str(memberships)

    def meeting_status(self, meeting):
        memberships = meeting.meetingmembership_set.all()

        if meeting.active:
            confirmed_students = memberships.filter(Q(user_role="Tutee") & (Q(status="Confirmed") | Q(status="Requested Repeat")))
            confirmed_tutors = memberships.filter(
                Q(user_role="Tutor") & 
                (Q(status="Confirmed") | Q(created_at__lt=aware, status="Pending Confirmation"))
            )

            if confirmed_tutors and confirmed_students:
                return "All confirmed"
            elif not confirmed_tutors and confirmed_students:
                return "Student confirmed"
            elif not confirmed_students and confirmed_tutors:
                return "Tutor confirmed"
            else:
                return "None confirmed"
        else:
            if meeting.tutorrequest_set.filter(cancel_reason="Unconfirmed"):
                return "Cancelled - unconfirmed student"

            cancelled_membership = memberships.filter(status="Cancelled").first()
            if not cancelled_membership:
                return "Error - Inactive Meeting"
            try:
                cancelled_membership.cancel_reason
            except AttributeError:
                return "Unknown cancel reason"
            if cancelled_membership.cancel_reason == "User":
                if cancelled_membership.user_role == "Tutee":
                    return "Cancelled by student"
                else:
                    return "Cancelled by tutor"
            elif cancelled_membership.cancel_reason == "Unconfirmed":
                if cancelled_membership.user_role == "Tutee":
                    return "Cancelled - unconfirmed student"
                else:
                    return "Cancelled - unconfirmed tutor"
            else:
                return "Student cancelled request"


class BackgroundCheckFilter(admin.SimpleListFilter):
    title = "background check status"
    parameter_name = "profile"

    def lookups(self, request, model_admin):
        return (
            ("Approved", "Approved"),
            ("Not approved", "Not approved"),
            ("Not requested", "Not requested"),
        )

    def queryset(self, request, queryset):
        if self.value() == "Approved":
            return queryset.filter(
                account_type__display="Tutor",
                user__backgroundcheckrequest__status="Approved"
            )
        elif self.value() == "Not approved":
            return queryset.filter(
                Q(account_type__display="Tutor") &
                Q(user__backgroundcheckrequest__isnull=False) &
                ~Q(user__backgroundcheckrequest__status="Approved")
            )
        elif self.value() == "Not requested":
            return queryset.filter(
                Q(account_type__display="Tutor") &
                ~Q(user__backgroundcheckrequest=None)
            )

def get_unassigned_tutor_profiles(queryset, days=None):
    if days:
        tutor_memberships = MeetingMembership.objects.filter(
            user_role="Tutor",
            meeting__created_at__gt=timezone.now()-dt.timedelta(days=days)
        )
    else:
        tutor_memberships = MeetingMembership.objects.filter(
            user_role="Tutor",
        )

    assigned_tutor_ids = list(User.objects.filter(
        membership__in=tutor_memberships
    ).values_list('profile__pk', flat=True))

    filter_dict = get_nonzero_monthly_hours_filter_dict()

    return queryset.filter(
        Q(
            account_type__display="Tutor",
            user__is_active=True,
            onboarded=True,
            offered_sectors__isnull=False,
            offered_subjects__isnull=False,
            available__isnull=False,
            user__backgroundcheckrequest__status="Approved",
            user__roleplaytraining__isnull=False,
        ) &
        (
            Q(tutor_monthly_volunteer=False, offered_hours__gt=0,)|
            Q(tutor_monthly_volunteer=True, **filter_dict)
        )
    ).exclude(pk__in=assigned_tutor_ids).distinct()


class TutorFilter(admin.SimpleListFilter):
    title = "tutor filter"
    parameter_name = "profile"

    def lookups(self, request, model_admin):
        return (
            ("Orientation", "Tutor: Orientation (not started)"),
            ("Training 1", "Tutor: Training 1"),
            ("Training 2", "Tutor: Training 2"),
            ("Background", "Tutor: Finished (no background)"),
            ("Finished", "Tutor: Finished (background)"),
            ("Approved", "Coordinator: Approved"),
            ("Not approved", "Coordinator: Not approved"),
            ("Unassigned (past week)", "Tutor: Unassigned (past week)"),
            ("Unassigned (past two weeks)", "Tutor: Unassigned (past two weeks)"),
            ("Unassigned (past 30 days)", "Tutor: Unassigned (past 30 days)"),
            ("Unassigned (all time)", "Tutor: Unassigned (all time)"),
        )

    def queryset(self, request, queryset):
        if self.value() == "Orientation":
            return queryset.filter(user__orientationtraining__isnull=True).distinct()
        elif self.value() == "Training 1":
            return queryset.filter(
                user__orientationtraining__isnull=False,
                user__tutortraining__isnull=True
            ).distinct()
        elif self.value() == "Training 2":
            return queryset.filter(
                user__orientationtraining__isnull=False,
                user__tutortraining__isnull=False,
                user__roleplaytraining__isnull=True
            ).distinct()
        elif self.value() == "Background":
            return queryset.filter(
                Q(user__orientationtraining__isnull=False,
                user__tutortraining__isnull=False,
                user__roleplaytraining__isnull=False) &
                ~Q(user__backgroundcheckrequest__status="Approved")
            ).distinct()
        elif self.value() == "Finished":
            return queryset.filter(
                user__orientationtraining__isnull=False,
                user__tutortraining__isnull=False,
                user__roleplaytraining__isnull=False
            ).distinct()
        elif self.value() == "Approved":
            return queryset.filter(
                account_type__display="Program-Coordinator",
                approve_coordinator=True,
            ).distinct()
        elif self.value() == "Not approved":
            return queryset.filter(
                account_type__display="Program-Coordinator",
                approve_coordinator=False,
            ).distinct()
        elif self.value() == "Unassigned (past week)":
            return get_unassigned_tutor_profiles(queryset, days=7)
        elif self.value() == "Unassigned (past two weeks)":
            return get_unassigned_tutor_profiles(queryset, days=14)
        elif self.value() == "Unassigned (past 30 days)":
            return get_unassigned_tutor_profiles(queryset, days=30)
        elif self.value() == "Unassigned (all time)":
            return get_unassigned_tutor_profiles(queryset)


@admin.action(description='Skip training', permissions=['change'])
def skip_training(modeladmin, request, queryset):
    for profile in queryset:
        if profile.account_type.display == "Tutor":
            try:
                profile.user.orientation3
            except Orientation3.DoesNotExist:
                Orientation3.objects.create(user=profile.user)
            try:
                profile.user.orientation4
            except Orientation4.DoesNotExist:
                Orientation4.objects.create(user=profile.user)
            try:
                profile.user.orientation9
            except Orientation9.DoesNotExist:
                Orientation9.objects.create(user=profile.user)
            try:
                profile.user.orientation11
            except Orientation11.DoesNotExist:
                Orientation11.objects.create(user=profile.user)
            try:
                profile.user.livesession
            except LiveSession.DoesNotExist:
                LiveSession.objects.create(user=profile.user)


class ProfileAdmin(admin.ModelAdmin):
    list_display = [
        "__str__",
        "email",
        "onboarded",
        "account_type",
        "num_offered_subjects",
        "num_available_timeslots",
        "tutor_monthly_volunteer",
    ]
    list_filter = [
        "account_type",
        TutorFilter,
        "offered_sectors",
        "offered_subjects",
        "available",
    ]
    ordering = [Lower('user__username')]
    search_fields = [
        "user__username", 
        "full_name", 
        "nickname", 
        "user__email",
        "site__display",
        "site_location__display",
    ]
    
    actions = [skip_training]

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = [
            "email",
            "training_status",
            "background_link",
            "monthly_hours_link",
            "tutoring_reason",
            "users_blocking",
            "users_who_block_this_user",
            "hours"
        ]
        if request.user.is_superuser:
            return readonly_fields
        else:
            readonly_fields.append("account_type")
            readonly_fields.append("user")
            readonly_fields.append("onboarded")
            return readonly_fields

    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            (None, {
                'fields': (
                    'user',
                    'email',
                    'phone_number',
                    'full_name',
                    'nickname',
                    'account_type',
                    'onboarded',
                )
            }),
            ("Profile", {
                'classes': ('collapse',),
                'fields': (
                    'can_speak_english',
                    'pronouns',
                    'gender',
                    'ethnicity',
                    'zip_code',
                    'users_who_block_this_user',
                    'users_blocking',
                    'block',
                )
            })
        ]
        if obj:
            if obj.account_type.display == "Tutor" and obj.onboarded:
                fieldsets.append(
                    ('Tutor Info', {
                        'classes': ('collapse',),
                        'fields': (
                            "training_status",
                            'background_link',
                            'offered_sectors',
                            'tutor_monthly_volunteer',
                            'monthly_hours_link',
                            'hours',
                            'offered_hours',
                            'offered_subjects',
                            'site',
                            'site_location',
                            'tutee_contact',
                            'available',
                            'sms_notifications',
                            'email_notifications',
                            'tutor_training_trainer',
                        ),
                    })

                )
            if "Tutee" in obj.account_type.display and obj.onboarded:
                fieldsets.append(
                    ('Student Info', {
                        'classes': ('collapse',),
                        'fields': (
                            'tutoring_reason',
                            'parent_or_guardian_name',
                            'grade_level',
                            'sector',
                            'site',
                            'site_location',
                            'available',
                            'sms_notifications',
                            'email_notifications',
                        ),
                    })
                )
            if obj.account_type.display == "Tutor-Trainer":
                fieldsets.append(
                    ('Trainer Info', {
                        'classes': ('collapse',),
                        'fields': (
                            'orientation_trainer',
                            'tutor_training_trainer',
                            'roleplay_trainer',
                        ),
                    })

                )
            if obj.account_type.display == "Program-Coordinator":
                fieldsets.append(
                    ('Program Coordinator Info', {
                        'classes': ('collapse',),
                        'fields': (
                            'site',
                            'site_location',
                            'approve_coordinator',
                        ),
                    })

                )
        return fieldsets

    def email(self, profile):
        return profile.user.email

    def hours(self, instance):
        if not instance.account_type.display == "Tutor":
            return None
        if instance.tutor_monthly_volunteer:
            current_month_offered = instance.offered_hours_current_month
            current_month_done = instance.hours_done_current_month
            current_week_month = instance.hours_left_current_month
            return f"HI"
        else:
            current_week_offered = instance.offered_hours
            current_week_done = instance.hours_done_current_week
            current_week_left = instance.hours_left_current_week
            return f"Weekly tutor: {current_week_offered} hours offered weekly, {current_week_done} hours done this week, {current_week_left} hours left this week"

    def users_blocking(self, profile):
        return ", ".join([str(user) for user in profile.block.all()]) or "None"

    def users_who_block_this_user(self, profile):
        return ", ".join([str(user) for user in profile.user.blocking.all()]) or "None"

    def training_status(self, profile):
        status = get_tutor_training_stage(profile.user)
        if status == "background":
            return "Finished (needs background approved)"
        else:
            return status.title()

    def background_link(self, profile):
        url = reverse("admin:tutor_backgroundcheckrequest_change", args=[profile.user.backgroundcheckrequest.id])
        return mark_safe(f"<a href='{url}'>{profile.user.backgroundcheckrequest}</a>")

    def monthly_hours_link(self, profile):
        if profile.tutor_monthly_volunteer:
            url = reverse("admin:tutor_tutorofferedmonthlyhours_change", args=[profile.user.tutorofferedmonthlyhours.id])
            return mark_safe(f"<a href='{url}'>{profile.user.tutorofferedmonthlyhours}</a>")
        else:
            return "Weekly tutor"

    def num_offered_subjects(self, profile):
        if profile.account_type.display == "Tutor":
            return f"{profile.offered_subjects.all().count()} subjects"
        else:
            return None

    def num_available_timeslots(self, profile):
        return f"{profile.available.all().count()} timeslots"

class DashboardAdmin(admin.ModelAdmin):
    change_list_template = 'tutor/dashboard.html'

    list_filter = (
        'onboarded',
    )

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(
            request,
            extra_context=extra_context,
        )

        try:
            qs = response.context_data['cl'].queryset
        except (AttributeError, KeyError):
            return response

        metrics = {
            'ready_tutors': Count(
                Case(When(onboarded=True, then=F('offered_hours')), output_field=DecimalField(), default=0)),
            'total_tutors': Count('id'),
            'total_hours': Sum(
                Case(When(onboarded=True, then=F('offered_hours')), output_field=DecimalField(), default=0)),
            'total_possible_hours': Sum('offered_hours'),
        }

        response.context_data['tutors'] = list(
            qs
            .filter(account_type__display='Tutor')
            .values('full_name', 'user__email', 'phone_number')
            .annotate(**metrics)
            .order_by('user__last_name')
        )

        response.context_data['tutor_total'] = qs.filter(account_type__display='Tutor').count()

        response.context_data['students'] = list(
            qs
            .filter(Q(account_type__display='K-12-Tutee') |
                    Q(account_type__display='College-Tutee') |
                    Q(account_type__display='Adult-Tutee'))
            .values('full_name', 'user__email', 'phone_number')
            .annotate(**metrics)
            .order_by('full_name')
        )

        response.context_data['student_total'] = qs.filter(~Q(account_type__display='Tutor')).count()

        return response

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class BackgroundCheckRequestAdmin(admin.ModelAdmin):
    list_display = [
        "__str__",
        "profile_link",
    ]
    readonly_fields = ["user", "profile_link"]
    list_filter = ["status"]
    search_fields = ["user__username", "user__profile__full_name", "user__profile__nickname"]

    def profile_link(self, obj):
        url = reverse("admin:tutor_profile_change", args=[obj.user.profile.id])
        return mark_safe(f"<a href='{url}'>Profile: {obj.user.profile}</a>")


class MeetingFilter(admin.SimpleListFilter):
    title = "meeting"
    parameter_name = "request"

    def lookups(self, request, model_admin):
        return (
            ("Active meeting", "Active meeting"),
            ("No active meeting", "No active meeting"),
        )

    def queryset(self, request, queryset):
        if self.value() == "Active meeting":
            return queryset.filter(meeting__active=True)
        elif self.value() == "No active meeting":
            return queryset.filter(Q(meeting__isnull=True) | Q(meeting__active=False))


class TutorRequestAdmin(admin.ModelAdmin):
    list_display = (
        "profile",
        "active",
        "subject",
        # "active_meeting",
        "meeting_link",
        "timestamp",
        "profile_link",
    )
    list_filter = [
        "active",
        MeetingFilter,
        "subject",
    ]
    ordering = ['-timestamp']
    search_fields = [
        "user__username",
        "user__profile__full_name",
        "user__profile__nickname",
        "user__profile__site__display",
        "user__profile__site_location__display",
        "subject__display",
        "meeting__meetingmembership__user__username",
        "meeting__meetingmembership__user__profile__nickname",
        "meeting__meetingmembership__user__profile__full_name",
    ]

    def has_add_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return ["meeting_link", "profile_link", "timestamp", "created_by"]
        else:
            return ["meeting_link", "profile_link", "timestamp", "subject", "user", "notes", "cancel_reason"]

    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            (None, {
                'fields': (
                    "timestamp",
                    'user',
                    'profile_link',
                    'created_by',
                    'active',
                    'inactive_timestamp',
                    'cancel_reason',
                    'notes',
                )
            }),
        ]
        if obj:
            if obj.meeting:
                if obj.meeting.active:
                    fieldsets.append(
                        ('Meeting Info', {
                            'fields': (
                                'meeting_link',
                            ),
                        })

                    )
        return fieldsets

    def profile(self, tutor_request):
        tutee = tutor_request.user
        memberships = tutee.membership.filter(
            ~Q(status="Cancelled") & Q(meeting__active=True)
        )
        return f"{tutee.profile} ({memberships.distinct().count()})"

    def active_meeting(self, tutor_request):
        if tutor_request.meeting:
            return bool(tutor_request.meeting.active)
        else:
            return False
    active_meeting.boolean = True

    def meeting_link(self, tutor_request):
        if tutor_request.meeting:
            url = reverse("admin:tutor_meeting_change", args=[tutor_request.meeting.id])
            return mark_safe(f"<a href='{url}'>Meeting: {tutor_request.meeting}</a>")

    def profile_link(self, tutor_request):
        url = reverse("admin:tutor_profile_change", args=[tutor_request.user.profile.id])
        return mark_safe(f"<a href='{url}'>Profile: {tutor_request.user.profile}</a>")


class TuteeAssessmentAdmin(admin.ModelAdmin):
    list_display = (
        "meeting",
        "profile_link",
        "assessment",
    )
    list_filter = [
        "assessment",
    ]
    search_fields = ["tutee__username", "tutee__profile__full_name", "tutee__profile__nickname"]
    readonly_fields = ["profile_link", "meeting", "tutee"]

    def get_fields(self, request, obj=None):
        fields = super(TuteeAssessmentAdmin, self).get_fields(request, obj)
        if not obj:
            fields.remove("profile_link")
        return fields

    def profile_link(self, assessment):
        url = reverse("admin:tutor_profile_change", args=[assessment.tutee.profile.id])
        return mark_safe(f"<a href='{url}'>Profile: {assessment.tutee.profile}</a>")


class SiteAdmin(admin.ModelAdmin):
    list_display = [
        "__str__",
        "tier",
    ]
    search_fields = ["display"]


@admin.action(description='Set binding to TRUE', permissions=['change'])
def set_binding_true(modeladmin, request, queryset):
    for item in queryset:
        item.binding = True
        item.save()


@admin.action(description='Set binding to FALSE', permissions=['change'])
def set_binding_false(modeladmin, request, queryset):
    for item in queryset:
        item.binding = False
        item.save()


class SiteLocationAdmin(admin.ModelAdmin):
    list_display = [
        "display",
        "site",
        "binding",
    ]
    list_filter = [
        "site",
        "binding",
    ]
    search_fields = ["display", "site__display"]
    actions = [set_binding_true, set_binding_false]


class OrientationTrainingAdmin(admin.ModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            readonly_fields = []
        else:
            readonly_fields = [f.name for f in self.model._meta.fields]
        return readonly_fields

    def has_add_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return False


class TutorTrainingAdmin(admin.ModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            readonly_fields = []
        else:
            readonly_fields = [f.name for f in self.model._meta.fields]
        return readonly_fields

    def has_add_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return False


class RoleplayTrainingAdmin(admin.ModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            readonly_fields = []
        else:
            readonly_fields = [f.name for f in self.model._meta.fields]
        return readonly_fields

    def has_add_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return False


class ExitTicketDifficultInline(admin.StackedInline):
    model = ExitTicketDifficult
    exclude = ["tutor", "completed", "request"]

    def has_delete_permission(self, request, obj=None):
        return False


class ExitTicketMediumInline(admin.StackedInline):
    model = ExitTicketMedium
    exclude = ["tutor", "completed", "request"]

    def has_delete_permission(self, request, obj=None):
        return False


class ExitTicketEasyInline(admin.StackedInline):
    model = ExitTicketEasy
    exclude = ["tutor", "completed", "request"]

    def has_delete_permission(self, request, obj=None):
        return False


class ExitTicketAdmin(admin.ModelAdmin):
    list_display = [
        "__str__",
        "completed",
        "request",
    ]

    def has_add_permission(self, request, obj=None):
        return False

    def get_inline_instances(self, request, obj=None):
        inlines = []

        try:
            obj.exitticketeasy
            inlines.append(ExitTicketEasyInline)
        except ExitTicketEasy.DoesNotExist:
            pass

        try:
            obj.exitticketmedium
            inlines.append(ExitTicketMediumInline)
        except ExitTicketMedium.DoesNotExist:
            pass

        try:
            obj.exitticketdifficult
            inlines.append(ExitTicketDifficultInline)
        except ExitTicketDifficult.DoesNotExist:
            pass

        return [inline(self.model, self.admin_site) for inline in inlines]


class MonthlyVolunteerFilter(admin.SimpleListFilter):
    title = "monthly tutor"
    parameter_name = "monthly"

    def lookups(self, request, model_admin):
        return (
            ("Monthly volunteer", "Monthly volunteer"),
            ("Weekly volunteer", "Weekly volunteer"),
        )

    def queryset(self, request, queryset):
        if self.value() == "Monthly volunteer":
            return queryset.filter(
                user__profile__account_type__display="Tutor",
                user__profile__tutor_monthly_volunteer=True,
            )
        elif self.value() == "NOT monthly volunteer":
            return queryset.filter(
                user__profile__account_type__display="Tutor",
                user__profile__tutor_monthly_volunteer=False,
            )


class MonthlyAvailabilityFilter(admin.SimpleListFilter):
    title = "monthly tutor"
    parameter_name = "available"

    def lookups(self, request, model_admin):
        fields = TutorOfferedMonthlyHours._meta.get_fields()[4:]

        offered_monthly = []

        for field in fields:
            month_number = int(field.name.split("_")[1])
            year = int(field.name.split("_")[2])

            month_str = f"{calendar.month_name[month_number]} 20{str(year)}"

            hours = TutorOfferedMonthlyHours.objects.filter(
                user__profile__account_type__display="Tutor",
                user__profile__tutor_monthly_volunteer=True,
            ).values_list(field.name, flat=True)

            offered_monthly.append([f"{month_str}", f"{month_str} -------- {sum(hours)} hr"])
        return offered_monthly

    def queryset(self, request, queryset):
        field_months = TutorOfferedMonthlyHours.get_month_field_names()

        for field_name, month in field_months.items():
            if self.value() == month:
                return queryset.filter(
                    user__profile__account_type__display="Tutor",
                    user__profile__tutor_monthly_volunteer=True,
                    **{f"{field_name}__gt": 0}
                )


class TutorOfferedMonthlyHoursAdmin(admin.ModelAdmin):
    list_filter = [
        MonthlyVolunteerFilter,
        MonthlyAvailabilityFilter,
    ]

    def get_list_display(self, request):
        today = timezone.now()
        fields = list(TutorOfferedMonthlyHours._meta.get_fields()[4:])

        def get_field_name(field):
            return field.name

        field_names = list(map(get_field_name, fields))

        return ["user", "monthly", *field_names]

    def monthly(self, instance):
        if instance.user.profile.tutor_monthly_volunteer:
            return True
        else:
            return False
    monthly.boolean = True


admin.site.register(User, UserAdmin)
admin.site.register(Meeting, MeetingAdmin)
admin.site.register(Subject, SubjectAdmin)
admin.site.register(Issue, IssueAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(BackgroundCheckRequest, BackgroundCheckRequestAdmin)
admin.site.register(TutorRequest, TutorRequestAdmin)
admin.site.register(TuteeAssessment, TuteeAssessmentAdmin)
admin.site.register(Site, SiteAdmin)
admin.site.register(SiteLocation, SiteLocationAdmin)
admin.site.register(OrientationTraining, OrientationTrainingAdmin)
admin.site.register(TutorTraining, TutorTrainingAdmin)
admin.site.register(RoleplayTraining, RoleplayTrainingAdmin)
admin.site.register(ExitTicket, ExitTicketAdmin)
admin.site.register(TutorOfferedMonthlyHours, TutorOfferedMonthlyHoursAdmin)
admin.site.register(Dashboard, DashboardAdmin)
admin.site.register(ConnectedStudent, ConnectedStudentAdmin)
