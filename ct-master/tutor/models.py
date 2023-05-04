import datetime
import pytz
import calendar
import collections
from django.utils import timezone
from calendar import day_name
from django.db import models, IntegrityError
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import UserManager, AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from phonenumber_field.modelfields import PhoneNumberField
from multiselectfield import MultiSelectField

User = get_user_model()

phone_regex = RegexValidator(regex=r'^\d{9,15}$', message="Enter digits only")

def get_name(self):
    try:
        return str(self.profile.full_name or self.profile.nickname or self.username)
    except Profile.DoesNotExist:
        return str(self.username)
User.add_to_class("__str__", get_name)


def get_time_slots():
    times = [datetime.datetime.strptime(str(h), "%H").strftime("%-I%p") for h in range(24)]
    day_times = []
    for d in day_name:
        for t in times:
            display = f"{d}, {t}"
            day_times.append((display, display))

    return day_times


def get_subjects(sector):
    if sector == "Elementary School":
        return [("Reading", "Reading"), ("Math", "Math"), ("Writing", "Writing")], []
    elif sector == "Middle School":
        return [("Math", "Math"), ("Reading", "Reading"), ("Writing", "Writing")], []
    elif sector == "High School":
        return [("Social Studies", "Social Studies"), ("English Language Arts", "English Language Arts")], [("Biology", "Biology"), ("Chemistry", "Chemistry"), ("Physics", "Physics"), ("Algebra 1", "Algebra 1"), ("Algebra 2", "Algebra 2"), ("Geometry", "Geometry"), ("Trigonometry", "Trigonometry"), ("Pre-Calculus", "Pre-Calculus"), ("Calculus", "Calculus")]
    elif sector == 'College':
        return [("Writing", "Writing")], [("Biology 1", "Biology 1"), ("Biology 2", "Biology 2"), ("Chemistry 1", "Chemistry 1"), ("Chemistry 2", "Chemistry 2"), ("Physics 1", "Physics 1"), ("Physics 2", "Physics 2"), ("Algebra and Trigonometry", "Algebra and Trigonometry"), ("Pre-Calculus", "Pre-Calculus"), ("Calculus", "Calculus"), ("Principles Microeconomics", "Principles Microeconomics"), ("Principles Macroeconomics", "Principles Macroeconomics"), ("Intermediate Microeconomics", "Intermediate Microeconomics"), ("Intermediate Macroeconomics", "Intermediate Macroeconomics")]
    elif sector == 'Adult Education':
        return [("ESL", "ESL")], [("Math", "Math"), ("Science", "Science"), ("Reading", "Reading"), ("Writing", "Writing"), ("Social Studies", "Social Studies")]
    else:
        raise ValueError(f"No such sector: {sector}")


def get_sectors():
    choices = [
        ("Elementary School", "Elementary School"),
        ("Middle School", "Middle School"),
        ("High School", "High School"),
        ("College", "College"),
        ("Adult Education", "Adult Education"),
    ]
    return choices


def get_sites():
    choices=[
        ("Henry Street Settlement", "Henry Street Settlement"),
        ("Colin Powell", "Colin Powell"),
        #("Borough of Manhattan Community College","Borough of Manhattan Community College"),
        ("Broadway Housing Community", "Broadway Housing Community"),
        ("Children's Aid", "Children's Aid"),
        ("CUNY CLIP", "CUNY CLIP"),
        ("CUNY Adult Lit", "CUNY Adult Lit"),
        ("Liberty Partnership Program", "Liberty Partnership Program"),
        ("Other", "Other")
    ]
    return choices


def get_ethnicities():
    choices=[
        ("Asian", "Asian"),
        ("American Indian or Alaska Native", "American Indian or Alaska Native"),
        ("Black", "Black"),
        ("Latino", "Latino"),
        ("Middle Eastern", "Middle Eastern"),
        ("Native Hawaiian or Pacific Islander", "Native Hawaiian or Pacific Islander"),
        ("White", "White"),
        ("Other", "Other"),
    ]
    return choices


def get_genders():
    choices=[
            ("Male", "Male"),
            ("Female", "Female"),
            ("Other", "Other"),
    ]
    return choices


def get_pronouns():
    choices=[
        ("He/his/him", "He/his/him"),
        ("She/hers/her", "She/hers/her"),
        ("They/them/their", "They/them/their"),
        ("Other", "Other"),
    ]
    return choices


def get_grade_levels():
    choices=[
        ("Pre-K", "Pre-K"),
        ("Kindergarten", "Kindergarten"),
        ("1st", "1st"),
        ("2nd", "2nd"),
        ("3rd", "3rd"),
        ("4th", "4th"),
        ("5th", "5th"),
        ("6th", "6th"),
        ("7th", "7th"),
        ("8th", "8th"),
        ("9th", "9th"),
        ("10th", "10th"),
        ("11th", "11th"),
        ("12th", "12th"),
    ]
    return choices


def get_account_types():
    choices=[
        ("K-12-Tutee", "K-12-Tutee"),
        ("College-Tutee", "College-Tutee"),
        ("Adult-Tutee", "Adult-Tutee"),
        ("Tutor", "Tutor"),
        ("Tutor-Trainer", "Tutor-Trainer"),
        ("Admin", "Admin"),
        ("Program-Coordinator", "Program-Coordinator"),
    ]
    return choices


def get_site_locations(site):
    if site == "Henry Street Settlement":
        return [("Broome Street Adult Ed", "Broome Street Adult Ed"), ("Broome Street K-12", "Broome Street K-12"), ("301 Henry Street", "301 Henry Street")]
    elif site == "Colin Powell":
        return [("CCNY", "CCNY")]
    elif site == "Broadway Housing Community":
        return [("Sugar Hill", "Sugar Hill")]
    elif site == "Children's Aid":
        return [("Hope Leadership Academy", "Hope Leadership Academy"), ("Milbank Center", "Milbank Center"), ("Next Generation Center", "Next Generation Center"), ("Frederick Douglas High School", "Frederick Douglas High School")]
    elif site == "CUNY CLIP":
        return [("Borough of Manhattan Community College","Borough of Manhattan Community College"), ("Bronx Community College","Bronx Community College"), ("College of Staten Island","College of Staten Island"), ("Hostos Community College","Hostos Community College"), ("Kingsborough Community College","Kingsborough Community College"),
                ("LaGuardia Community College","LaGuardia Community College"), ("City College of Technology","City College of Technology"), ("Queensborough Community College","Queensborough Community College"), ("York College","York College")]
    elif site == "CUNY Adult Lit":
        return [("Bronx Community College","Bronx Community College"), ("Hostos Community College","Hostos Community College"), ("Lehman College","Lehman College"), ("Brooklyn College","Brooklyn College"), ("Kingsborough Community College","Kingsborough Community College"),
                ("Medgar Evers College","Medgar Evers College"), ("City College of Technology","City College of Technology"), ("Borough of Manhattan Community College","Borough of Manhattan Community College"), ("City College of New York","City College of New York"), ("Hunter College","Hunter College"),
                ("LaGuardia Community College","LaGuardia Community College"), ("Center for Immigrant Education and Training","Center for Immigrant Education and Training"), ("Queensborough Community College","Queensborough Community College"), ("York College","York College"), ("College of Staten Island","College of Staten Island")]
    elif site == "Liberty Partnership Program":
        return [("Pace High School", "Pace High School"), ("High School for Economics and Finance", "High School for Economics and Finance"), ("Academy of Hospitality and Tourism and Science, Technology and Research Early College High School at Erasmus", "Academy of Hospitality and Tourism and Science, Technology and Research Early College High School at Erasmus")]
    elif site == "Other":
        return []
    else:
        raise ValueError(f"No such site: {site}")


def get_tiers():
    # max pooled hours, individual hours, subjects, hours per subject
    choices= [
        ("Tier 1", 30, 4, 2, 2),
        ("Tier 2", 20, 4, 2, 2),
        ("Tier 3", 6, 4, 2, 2),
        ("Free Tier", 0, 1, 1, 1),
    ]
    return choices


def get_site_tier(site):
    tier_3_sites = ("CUNY CLIP", "CUNY Adult Lit")
    tier_2_sites = ("Liberty Partnership Program",)
    tier_1_sites = (
        "Broadway Housing Community",
        "Children's Aid",
        "Henry Street Settlement",
        "Colin Powell",
        "Other"
    )
    if site in tier_1_sites:
        return "Tier 1"
    elif site in tier_2_sites:
        return "Tier 2"
    elif site in tier_3_sites:
        return "Tier 3"
    else:
        return "Free Tier"

class TimeSlot(models.Model):
    display = models.TextField(choices=get_time_slots())
    day = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(6)])
    time = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(23)])

    def __str__(self):
        return self.display

    @classmethod
    def for_current_time(cls):
        now = timezone.localtime()
        return TimeSlot.objects.get(day=now.weekday(), time=now.hour)

    def next_datetime(self):        
        # Get next time this day will occur, not counting today
        today = timezone.localtime()
        days_ahead = self.day - today.weekday()
        if days_ahead <= 0: # Target day already happened this week
            days_ahead += 7
        next_date = today + datetime.timedelta(days=days_ahead)
        next_time = datetime.time(hour=self.time)
        next_datetime = datetime.datetime.combine(next_date, next_time)
        next_datetime = timezone.make_aware(next_datetime, timezone=pytz.timezone("America/New_York"))
        # If next datetime is within 96 hours, move to following week
        if next_datetime - datetime.timedelta(hours=96) < today:
            next_datetime += datetime.timedelta(days=7)
        return next_datetime

    def next_datetime_nearest(self):
        # Get next time this day will occur with no buffer time
        today = timezone.localtime()
        days_ahead = self.day - today.weekday()
        if days_ahead <= 0: # Target day already happened this week
            days_ahead += 7
        next_date = today + datetime.timedelta(days=days_ahead)
        next_time = datetime.time(hour=self.time)
        next_datetime = datetime.datetime.combine(next_date, next_time)
        next_datetime = timezone.make_aware(next_datetime, timezone=pytz.timezone("America/New_York"))
        return next_datetime

    def reschedule_cutoff(self):
        pass


class Sector(models.Model):
    display = models.TextField()

    def __str__(self):
        return self.display


class Subject(models.Model):
    display = models.TextField()
    sector = models.ForeignKey(Sector, on_delete=models.CASCADE)
    group_sessions = models.BooleanField(default=False)
    offered = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.display} - {self.sector.display}"

class Tier(models.Model):
    display = models.TextField()
    max_pooled_hours = models.IntegerField(validators=[MinValueValidator(1)])
    max_individual_hours = models.IntegerField(validators=[MinValueValidator(1)])
    max_subjects = models.IntegerField(validators=[MinValueValidator(1)])
    max_hours_per_subj = models.IntegerField(validators=[MinValueValidator(1)])

    def __str__(self):
        return self.display+"; Pooled Hours: "+str(self.max_pooled_hours)+"; Ind Hours: "+str(self.max_individual_hours)+"; Subjects: "+str(self.max_subjects)+"; Subj Hours: "+str(self.max_hours_per_subj)


class Site(models.Model):
    display = models.TextField()
    tier = models.ForeignKey(Tier, on_delete=models.CASCADE)

    def __str__(self):
        return self.display

    @property
    def num_remaining_pooled_hours(self):
        active_requests = TutorRequest.objects.filter(
            Q(active=True, user__profile__site=self) &
            (
                Q(meeting__isnull=True) |
                Q(meeting__isnull=False, meeting__active=True, meeting__scheduled_start__gt=timezone.now())
            )
        )
        hours_used = len(active_requests)
        return self.tier.max_pooled_hours - hours_used


class SiteLocation(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE)
    display = models.TextField()
    binding = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.site.display}: {self.display}"


class Ethnicity(models.Model):
    display = models.TextField()

    def __str__(self):
        return self.display


class Gender(models.Model):
    display = models.TextField()

    def __str__(self):
        return self.display


class Pronouns(models.Model):
    display = models.TextField()

    def __str__(self):
        return self.display


class AccountType(models.Model):
    display = models.TextField()

    def __str__(self):
        return self.display


class GradeLevel(models.Model):
    display = models.TextField()

    def __str__(self):
        return self.display


def get_nonzero_monthly_hours_filter_dict():
    month_field_name = TutorOfferedMonthlyHours.get_current_month_field_name()
    filter_dict = {"user__tutorofferedmonthlyhours__" + month_field_name + "__gt": 0}
    return filter_dict


class AvailableTutorProfileManager(models.Manager):
    def get_queryset(self):
        filter_dict = get_nonzero_monthly_hours_filter_dict()

        return super().get_queryset().filter(
            Q(
                account_type__display="Tutor",
                user__is_active=True,
                onboarded=True,
                user__backgroundcheckrequest__status="Approved",
                # user__livesession__isnull=False,
            ) &
            Q(
                Q(tutor_monthly_volunteer=False, offered_hours__gt=0) |
                Q(tutor_monthly_volunteer=True, **filter_dict)
            )
        ).distinct()


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(blank=True, null=True, max_length=100, default=None)
    nickname = models.CharField(
        max_length=100, blank=True, null=True, default=None,
        help_text="This is how other users will see you. If you don't have a nickname, enter your first name or leave blank"
    )
    zip_code = models.CharField(max_length=5, blank=True, null=True, default=None)
    gender = models.ForeignKey(Gender, blank=True, null=True, default=None, on_delete=models.SET_NULL)
    ethnicity = models.ForeignKey(Ethnicity, blank=True, null=True, default=None, on_delete=models.SET_NULL)
    pronouns = models.ForeignKey(Pronouns, blank=True, null=True, default=None, on_delete=models.SET_NULL)
    available = models.ManyToManyField(
        TimeSlot, blank=True,
        help_text="Hold control or command to select multiple"
    )
    can_speak_english = models.BooleanField(default=False)
    onboarded = models.BooleanField(default=False)
    account_type = models.ForeignKey(AccountType, on_delete=models.SET_NULL, null=True)
    sms_notifications = models.BooleanField(default=True)
    email_notifications = models.BooleanField(default=True)
    block = models.ManyToManyField(User, related_name="blocking", blank=True)
    # for Tutees
    sector = models.ForeignKey(Sector, related_name="tutee", blank=True, null=True, default=None, on_delete=models.SET_NULL)
    site = models.ForeignKey(Site, blank=True, null=True, default=None, on_delete=models.SET_NULL)
    site_location = models.ForeignKey(SiteLocation, blank=True, null=True, default=None, on_delete=models.SET_NULL)
    parent_or_guardian_name = models.CharField(null=True, default=None, blank=True, max_length=100)
    phone_number = PhoneNumberField(null=True)
    tutoring_reason = models.CharField(max_length=100, null=True, default=None)
    grade_level = models.ForeignKey(GradeLevel, null=True, blank=True, default=None, on_delete=models.PROTECT)
    # for Tutors
    tutor_monthly_volunteer = models.BooleanField(default=False)
    offered_hours = models.IntegerField(
        verbose_name="How many hours can you tutor weekly?",
        default=0, validators=[MinValueValidator(0), MaxValueValidator(40)],
        null=True, blank=True,
    )
    offered_subjects = models.ManyToManyField(Subject, related_name="tutor", blank=True)
    offered_sectors = models.ManyToManyField(Sector, related_name="tutor", blank=True)
    tutee_contact = models.TextField(
        null=True, default=None,
        help_text="Students will see this message from the meeting details page"
    )
    # for Trainers
    orientation_trainer = models.BooleanField(default=False)
    tutor_training_trainer = models.BooleanField(default=False)
    roleplay_trainer = models.BooleanField(default=False)
    # for Program Coordinators
    approve_coordinator = models.BooleanField(default=False)

    objects = models.Manager()
    available_tutors = AvailableTutorProfileManager()

    def __str__(self):
        return self.full_name or self.nickname or self.user.username

    @property
    def num_allowed_requests(self):
        if self.site is None:
            return Tier.objects.get(display="Free Tier").max_individual_hours
        active_requests = TutorRequest.objects.filter(active=True, user__profile__site=self.site)
        if len(active_requests) >= self.site.tier.max_pooled_hours:
            return Tier.objects.get(display="Free Tier").max_individual_hours
        return self.site.tier.max_individual_hours

    @property
    def num_allowed_subjects(self):
        if self.site is None:
            return Tier.objects.get(display="Free Tier").max_subjects
        return self.site.tier.max_subjects

    @property
    def num_allowed_hours_per_subject(self):
        if self.site is None:
            return Tier.objects.get(display="Free Tier").max_subjects
        return self.site.tier.max_hours_per_subj

    @property
    def tutor_orientation_stage(self):
        if self.account_type.display != "Tutor":
            return

        try:
            record = self.user.orientation3
            record = self.user.orientation4
            record = self.user.orientation9
            record = self.user.orientation11
            return "finished"
        except: 
            return "not-finished"

    @property
    def tutor_training_stage(self):
        if self.account_type.display != "Tutor":
            return

        try:
            record = self.user.orientation3
            record = self.user.orientation4
            record = self.user.orientation9
            record = self.user.orientation11
            record = self.user.backgroundcheckrequest
            record = self.user.livesession
            return "finished"
        except: 
            return "not-finished"

    @property
    def offered_hours_current_month(self):
        try:
            offered_hours_all = TutorOfferedMonthlyHours.objects.get(user=self.user)
            return getattr(offered_hours_all, TutorOfferedMonthlyHours.get_current_month_field_name())
        except TutorOfferedMonthlyHours.DoesNotExist:
            return 0

    @property
    def hours_done_current_month(self):
        today = timezone.now()
        month_start = (today - datetime.timedelta(days=today.day-1)).replace(hour=0, minute=0, second=0)
        month_end = (today + datetime.timedelta(days=calendar.monthrange(today.year, today.month)[1] - today.day + 1)).replace(hour=0, minute=0, second=0)

        meetings_this_month = MeetingMembership.objects.filter(
            Q(
                user=self.user,
                meeting__scheduled_start__gte=month_start,
                meeting__scheduled_start__lt=month_end
            ) & ~Q(status="Cancelled")
        )
        return meetings_this_month.distinct().count()

    @property
    def hours_left_current_month(self):
        if self.tutor_monthly_volunteer:
            current_hours = self.hours_done_current_month
            offered_hours = self.offered_hours_current_month
            remaining_hours = offered_hours - current_hours

            if remaining_hours < 0:
                return 0
            else:
                return remaining_hours
        else:
            return None

    @property
    def hours_done_current_week(self):
        today = timezone.now()
        week_start = (today - datetime.timedelta(days=today.weekday())).replace(hour=0, minute=0, second=0)
        week_end = (today + datetime.timedelta(days=8-today.weekday())).replace(hour=0, minute=0, second=0)

        meetings_this_week = MeetingMembership.objects.filter(
            Q(
                user=self.user,
                meeting__scheduled_start__gte=week_start,
                meeting__scheduled_start__lt=week_end
            ) & ~Q(status="Cancelled")
        )
        return meetings_this_week.distinct().count()

    @property
    def hours_left_current_week(self):
        if not self.tutor_monthly_volunteer:
            current_hours = self.hours_done_current_week
            remaining_hours = self.offered_hours - current_hours

            if remaining_hours < 0:
                return 0
            else:
                return remaining_hours
        else:
            return None

    @property
    def open_hours(self):
        if self.tutor_monthly_volunteer:
            return self.hours_left_current_month
        else:
            return self.hours_left_current_week

    def new_request_not_allowed(self, subject):
        requests = TutorRequest.objects.filter(
            Q(user=self.user, active=True)
        )
        num_requests = len(requests) + 1

        hours_per_subject = collections.Counter(r.subject for r in requests)
        hours_per_subject[subject] += 1

        num_allowed_requests = self.num_allowed_requests
        num_allowed_subjects = self.num_allowed_subjects

        num_allowed_hours_per_subject = self.user.profile.num_allowed_hours_per_subject

        if num_requests > num_allowed_requests:
            return f"You are only allowed up to {num_allowed_requests} active requests."
        if len(hours_per_subject) > num_allowed_subjects:
            return f"You are only allowed up to {num_allowed_subjects} different subject(s)."
        if max(hours_per_subject.values()) > num_allowed_hours_per_subject:
            return f"You are only allowed up to {num_allowed_hours_per_subject} requests per subject."


class TutorOfferedMonthlyHours(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    m_8_22 = models.IntegerField(verbose_name="AUG 2022", default=0, validators=[MinValueValidator(0), MaxValueValidator(200)])
    m_9_22 = models.IntegerField(verbose_name="SEP 2022", default=0, validators=[MinValueValidator(0), MaxValueValidator(200)])
    m_10_22 = models.IntegerField(verbose_name="OCT 2022", default=0, validators=[MinValueValidator(0), MaxValueValidator(200)])
    m_11_22 = models.IntegerField(verbose_name="NOV 2022", default=0, validators=[MinValueValidator(0), MaxValueValidator(200)])
    m_12_22 = models.IntegerField(verbose_name="DEC 2022", default=0, validators=[MinValueValidator(0), MaxValueValidator(200)])
    m_1_23 = models.IntegerField(verbose_name="JAN 2023", default=0, validators=[MinValueValidator(0), MaxValueValidator(200)])
    m_2_23 = models.IntegerField(verbose_name="FEB 2023", default=0, validators=[MinValueValidator(0), MaxValueValidator(200)])
    m_3_23 = models.IntegerField(verbose_name="MAR 2023", default=0, validators=[MinValueValidator(0), MaxValueValidator(200)])
    m_4_23 = models.IntegerField(verbose_name="APR 2023", default=0, validators=[MinValueValidator(0), MaxValueValidator(200)])
    m_5_23 = models.IntegerField(verbose_name="MAY 2023", default=0, validators=[MinValueValidator(0), MaxValueValidator(200)])
    m_6_23 = models.IntegerField(verbose_name="JUN 2023", default=0, validators=[MinValueValidator(0), MaxValueValidator(200)])
    m_7_23 = models.IntegerField(verbose_name="JUL 2023", default=0, validators=[MinValueValidator(0), MaxValueValidator(200)])
    m_8_23 = models.IntegerField(verbose_name="AUG 2023", default=0, validators=[MinValueValidator(0), MaxValueValidator(200)])
    
    class Meta:
        verbose_name = 'tutor monthly hours offering'
        verbose_name_plural = 'tutor monthly hours offerings'

    def __str__(self):
        volunteer_type = "Monthly" if self.user.profile.tutor_monthly_volunteer else "Weekly"
        return f"{self.user}, {volunteer_type}"

    def get_current_month_field_name():
        today = timezone.now()
        field_name = f"m_{today.strftime('%-m')}_{today.strftime('%y')}"
        return field_name

    def get_month_field_names():
        fields = TutorOfferedMonthlyHours._meta.get_fields()[4:]

        field_months = {}

        for field in fields:
            month_number = int(field.name.split("_")[1])
            year = int(field.name.split("_")[2])
            month_str = f"{calendar.month_name[month_number]} 20{str(year)}"
            field_months[field.name] = f"{month_str}"

        return field_months


class Meeting(models.Model):
    members = models.ManyToManyField(User, through="MeetingMembership")
    attendance = models.ManyToManyField(User, related_name='attended_members', blank=True)
    scheduled_time_slot = models.ForeignKey(TimeSlot, on_delete=models.PROTECT)
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True)
    scheduled_start = models.DateTimeField(default=None, null=True)
    start_datetime = models.DateTimeField(default=None, null=True)
    stop_datetime = models.DateTimeField(default=None, null=True)
    notes = models.TextField(blank=True, default=None, null=True)
    follow_up_meeting = models.ForeignKey("Meeting", default=None, null=True, blank=True, on_delete=models.SET_NULL)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        time_ny = self.scheduled_start.astimezone(tz=pytz.timezone("America/New_York")).strftime('%A, %m/%d/%y, %-I:%M%p')
        memberships = self.meetingmembership_set.filter(~Q(status="Cancelled"))
        members = User.objects.filter(membership__in=memberships)
        return (
            f"{time_ny} | "
            f"{', '.join(str(m.profile) for m in members)}"
        )

    def can_cancel(self):
        if not self.start_datetime and self.scheduled_start > timezone.now():
            return True
        return False

    def can_repeat(self):
        if self.start_datetime and self.scheduled_start > timezone.now() - datetime.timedelta(days=3):
            return True
        return False

    def can_confirm(self):
        if not self.start_datetime and self.scheduled_start > timezone.now():
            return True
        return False

    def past_start(self):
        if self.scheduled_start < timezone.now():
            return True
        return False

    def upcoming(self):
        if not self.start_datetime:
            return True
        return False

    def happened(self):
        if self.start_datetime and self.stop_datetime:
            return True
        return False

    def happening(self):
        if self.start_datetime and not self.stop_datetime:
            return True
        return False

    def duration(self):
        return self.stop_datetime - self.start_datetime
        
    @property
    def tutors_str(self):
        if self.members:
            tutors = self.meetingmembership_set.filter(user_role="Tutor")
            return ''.join(str(item.user) for item in tutors)

    @property
    def tutor_emails(self):
        if self.members:
            tutors = self.meetingmembership_set.filter(user_role="Tutor")
            return ', '.join(str(item.user.email) for item in tutors)


class ConnectedStudent(models.Model):
    tutor = models.ForeignKey(User,related_name="tutor_associate",on_delete=models.CASCADE)
    student = models.ForeignKey(User,related_name='student_associate',on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.student or self.tutor
        

class MeetingMembership(models.Model):
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='membership', on_delete=models.CASCADE)
    status = models.TextField(
        default="Pending Confirmation",
        choices=[
            ("Pending Confirmation", "Pending Confirmation"),
            ("Confirmed", "Confirmed"),
            ("Cancelled", "Cancelled"),
            ("Requested Repeat", "Requested Repeat"),
        ]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    confirmation_timestamp = models.DateTimeField(default=None, null=True, blank=True)
    cancel_reason = models.TextField(
        default="", null=True, blank=True,
        choices=[
            ("", "----"),
            ("User", "User"),
            ("Site", "Site"),
            ("Cancelled Request", "Cancelled Request"),
            ("Unconfirmed", "Unconfirmed"),
        ]
    )
    cancel_timestamp = models.DateTimeField(default=None, null=True, blank=True)
    user_role = models.TextField(
        choices=[
            ("Tutor", "Tutor"),
            ("Tutee", "Tutee"),
        ]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    rate = models.IntegerField(
        null=True, blank=True,
        choices=[
            (1, 1),
            (2, 2),
            (3, 3),
            (4, 4),
            (5, 5),
        ]
    )
    rated = models.BooleanField(
        null=False, default=False
    )

    def __str__(self):
        return f"{self.meeting.scheduled_start.strftime('%x')} {self.user.profile.full_name or self.user.profile.nickname} - {self.status}"

    def can_cancel(self):
        if self.status == "Pending Confirmation" or self.status == "Confirmed":
            return True
        return False

    def can_repeat(self):
        if self.status != "Requested Repeat" and self.user_role == "Tutee":
            return True
        return False

    def can_confirm(self):
        if self.status == "Pending Confirmation":
            return True
        return False

    @property
    def confirmation_limit(self):
        if self.user_role == "Tutee":
            created = self.created_at if self.created_at <= self.meeting.created_at else self.meeting.created_at
            return created + datetime.timedelta(hours=48)

        elif self.user_role == "Tutor":
            return self.meeting.created_at + datetime.timedelta(hours=72)


class TutorRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    notes = models.TextField("What do you need help with?", help_text="Your tutor will be able to see this note", default=None, null=True)
    meeting = models.ForeignKey(Meeting, null=True, default=None, on_delete=models.SET_NULL)
    active = models.BooleanField(default=True)
    timestamp = models.DateTimeField()
    inactive_timestamp = models.DateTimeField(default=None, null=True, blank=True)
    cancel_reason = models.TextField(
        default="", null=True, blank=True,
        choices=[
            ("", "----"),
            ("User", "User"),
            ("Unconfirmed", "Unconfirmed"),
            ("Site", "Site"),
        ]
    )
    created_by = models.TextField(
        default="User",
        choices=[
            ("User", "User"),
            ("Site", "Site"),
        ]
    )

    def __str__(self):
        return f"{self.user} - {self.subject}"


class ExitTicket(models.Model):
    request = models.OneToOneField(TutorRequest, on_delete=models.CASCADE)
    tutor = models.ForeignKey(
        User, related_name="ticket_tutor", on_delete=models.CASCADE, default=None, blank=True, null=True,
    )
    completed = models.DateTimeField(default=None, blank=True, null=True)

    def __str__(self):
        return f"{self.request.user.profile}, {self.tutor}"

    
class ExitTicketDifficult(ExitTicket):
    confidence = models.IntegerField(
        verbose_name="How confident do you feel in the subject area you requested support with?",
        validators=[MinValueValidator(1), MaxValueValidator(7)],
        null=True,
    )
    tutor_satisfaction = models.IntegerField(
        verbose_name="What is your overall satisfaction with the tutor?",
        validators=[MinValueValidator(1), MaxValueValidator(4)],
        null=True,
    )
    satisfaction_reason = models.TextField(
        "If you rated the tutor 2 or below for the question above, please provide any additional comments here",
        default=None, blank=True, null=True,
        help_text="This information will be used to help us make changes to our program to better support you and other students in the future",
    )
    tutor_helpful = models.IntegerField(
        verbose_name="How helpful was the tutor in guiding you to understand concepts/problems?",
        validators=[MinValueValidator(1), MaxValueValidator(4)],
        null=True,
    )
    helpful_reason = models.TextField(
        "If you rated the tutor 2 or below for the question above, please provide any additional comments here",
        default=None, blank=True, null=True,
        help_text="This information will be used to help us make changes to our program to better support you and other students in the future",
    )
    tutor_comfortable = models.IntegerField(
        verbose_name="How comfortable/connected did you feel with the tutor?",
        validators=[MinValueValidator(1), MaxValueValidator(4)],
        default=None,
    )
    comfortable_reason = models.TextField(
        "If you rated the tutor 2 or below for the question above, please provide any additional comments here",
        default=None, blank=True, null=True,
        help_text="This information will be used to help us make changes to our program to better support you and other students in the future",
    )
    still_help = models.BooleanField(
        verbose_name="Do you still need help with any concepts/problems?",
        default=None, choices=[(True, "Yes"), (False, "No")],
    )
    help_concepts = models.TextField(
        "If you said yes to the above question, what concepts/problems do you need help with?",
        default=None, blank=True, null=True,
    )
    recommendations = models.TextField(
        "Do you have any recommendations on how we can improve the tutoring experience in the future?",
        default=None, blank=True, null=True,
    )
    thank_letter_yesno = models.BooleanField(
        verbose_name="Have you sent a thank you email to the tutor?",
        default=None, choices=[(True, "Yes"), (False, "No")],
    )
    thank_letter = models.TextField(
        "If you haven't sent an email yet, use the space here to write the thank you email you'll send them. We will forward it for you.",
        default=None, blank=True, null=True,
    )
    additional_comments = models.TextField(
        "Any additional comments?", default=None, blank=True, null=True,
    )

    class Meta:
        verbose_name = "exit ticket (difficult)"
        verbose_name_plural = "exit tickets (difficult)"


class ExitTicketMedium(ExitTicket):
    class Frequency(models.TextChoices):
        NEVER = "NEVER", "Never"
        SOMETIMES = "SOMETIMES", "Sometimes"
        ALWAYS = "ALWAYS", "Always"

    like_tutor = models.CharField(
        max_length=10,
        verbose_name="Did you like working with the tutor?",
        choices=Frequency.choices,
        blank=False, default=None,
    )
    be_open = models.CharField(
        max_length=10,
        verbose_name="Do you feel you can be open with the material you are having difficulty with in the tutorial session?",
        choices=Frequency.choices,
        blank=False, default=None,
    )
    tutor_help = models.CharField(
        max_length=10,
        verbose_name="When you are having difficulty with an assignment, does the tutor help you?",
        choices=Frequency.choices,
        blank=False, default=None,
    )
    better_understand = models.CharField(
        max_length=10,
        verbose_name="Do you feel you better understand the material as a result of working with the tutor?",
        choices=Frequency.choices,
        blank=False, default=None,
    )

    class Meta:
        verbose_name = "exit ticket (medium)"
        verbose_name_plural = "exit tickets (medium)"


class ExitTicketEasy(ExitTicket):
    like_tutor = models.BooleanField(
        verbose_name="I like the tutor.",
        choices=[(True, "Yes 😃"), (False, "No 🙁")],
        blank=False, default=None,
    )
    safe_mistakes = models.BooleanField(
        verbose_name="I feel safe to make mistakes in the tutorial.",
        choices=[(True, "Yes 😃"), (False, "No 🙁")],
        blank=False, default=None,
    )
    tutor_helps = models.BooleanField(
        verbose_name="When I don’t understand something, my tutor helps me.",
        choices=[(True, "Yes 😃"), (False, "No 🙁")],
        blank=False, default=None,
    )
    understand_better = models.BooleanField(
        verbose_name="I understand better when I work with the tutor.",
        choices=[(True, "Yes 😃"), (False, "No 🙁")],
        blank=False, default=None,
    )

    class Meta:
        verbose_name = "exit ticket (easy)"
        verbose_name_plural = "exit tickets (easy)"

class LeaveTicket(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    completed = models.DateTimeField(default=None, blank=True, null=True)
    leave_reason = models.TextField(max_length=200)
    leave_reason_others = models.TextField(max_length=200)
    return_date = models.DateField(default=None, null=True)

    def __str__(self):
        return f"{self.leave_reason}"
        """ return f"{self.id}, {self.user.username}, {self.leave_reason}" """


class TuteeAssessment(models.Model):
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name="assessment")
    tutee = models.ForeignKey(User, on_delete=models.CASCADE)
    assessment = models.IntegerField(null=True)
    grade = models.CharField(max_length=10, null=True, blank=True)

    def __str__(self):
        return f"{self.tutee.profile}: {self.assessment}"


class TuteeGrade(models.Model):
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE)
    tutee = models.ForeignKey(User, on_delete=models.CASCADE)
    grade = models.IntegerField()


class Issue(models.Model):
    type = models.TextField(
        default="General",
        choices=[
            ("General", "General"),
            ("Harrasment", "Harrasment"),
            ("Bug Report", "Bug Report"),
            ("My Tutor Didn't Show Up","My Tutor Didn't Show Up"),
        ]
    )
    timestamp = models.DateTimeField(default=None)
    status = models.TextField(
        default="AttentionNeeded",
        choices=[
            ("AttentionNeeded", "Attention Needed"),
            ("Resolved", "Resolved"),
            ("InProgress", "In Progress"),
        ],
    )
    submitter = models.ForeignKey(
        User,
        related_name="submitter",
        on_delete=models.SET_NULL,
        default=None,
        null=True,
    )
    assigned_staff = models.ForeignKey(
        User,
        related_name="assigned_issues",
        on_delete=models.SET_NULL,
        default=None,
        null=True,
        blank=True,
    )
    related_user = models.ForeignKey(
        User,
        related_name="issue_reports",
        on_delete=models.SET_NULL,
        default=None,
        null=True,
        blank=True,
    )
    staff_note = models.TextField(default=None, null=True, blank=True)
    description = models.TextField()
    contact_email = models.CharField(max_length=200, null=True)

    def __str__(self):
        return self.description


class GeneralIssue(models.Model):
    issue_description = models.TextField()
    issue = models.OneToOneField(
        Issue, related_name="general_issue", primary_key=True, on_delete=models.CASCADE
    )


class TuteeIssue(models.Model):
    issue_description = models.TextField()
    issue_tutee = models.ForeignKey(
        User, related_name="tutee_issue_tutee", on_delete=models.CASCADE
    )
    issue = models.OneToOneField(
        Issue, related_name="tutee_issue", primary_key=True, on_delete=models.CASCADE
    )


class HarassIssue(models.Model):
    issue_description = models.TextField()
    issue = models.OneToOneField(
        Issue, related_name="harass_issue", primary_key=True, on_delete=models.CASCADE
    )


class BackgroundCheckRequest(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    status = models.TextField(
        choices=[
            ("Queued", "Queued"),
            ("Approved", "Approved"),
            ("Denied", "Denied"),
        ]
    )
    def __str__(self):
        return f"{self.user.profile.full_name} | {self.status}"


class Comment(models.Model):
    text = models.TextField()
    submitter = models.ForeignKey(User, on_delete=models.CASCADE)
    created_timestamp = models.DateTimeField()
    last_edit_timestamp = models.DateTimeField()


class UserComment(models.Model):
    comment = models.OneToOneField(Comment, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)


class OrientationTraining(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    tutor_role = models.TextField("What do you understand your role as a tutor to be?")
    instructor_does = models.TextField("What is the role of an instructor?")
    tutor_does = models.TextField("What does a tutor do?")

    tutor_trainer = models.ForeignKey(Profile, verbose_name="Who was your tutor trainer?", related_name="orientation_training_form", on_delete=models.SET_NULL, null=True)
    tutor_trainer_rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], verbose_name="On a scale of 1-5, how knowledgeable was your trainer?", null=True)
    training_practical = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], verbose_name="On a scale of 1-5, how practical was the training?", null=True)
    overall_quality_rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], verbose_name="On a scale of 1-5, how would you rate the overall quality of the training?", null=True)
    suggestions = models.TextField("What suggestions would you have for future training?", default="")

    def __str__(self):
        if self.tutor_trainer:
            return f"{self.user.profile.full_name or self.user.username} (Trainer {self.tutor_trainer})"
        else:
            return f"{self.user.profile.full_name or self.user.username}"


class TutorTraining(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    what_is_minimalism = models.TextField()
    resources_for_control = models.TextField()
    video_conference_applications = models.TextField()
    facial_and_body_language = models.TextField()
    speaking_and_language = models.TextField()

    tutor_trainer = models.ForeignKey(Profile, verbose_name="Who was your tutor trainer?", related_name="tutor_training_form", on_delete=models.SET_NULL, null=True)
    tutor_trainer_rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], verbose_name="On a scale of 1-5, how knowledgeable was your trainer?", null=True)
    training_practical = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], verbose_name="On a scale of 1-5, how practical was the training?", null=True)
    overall_quality_rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], verbose_name="On a scale of 1-5, how would you rate the overall quality of the training?", null=True)
    suggestions = models.TextField("What suggestions would you have for future training?", default="")

    def __str__(self):
        if self.tutor_trainer:
            return f"{self.user.profile.full_name or self.user.username} (Trainer {self.tutor_trainer})"
        else:
            return f"{self.user.profile.full_name or self.user.username}"


class RoleplayTraining(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    what_difficulties = models.TextField()
    what_strategies = models.TextField()
    what_could_you_have_done_better = models.TextField()
    how_did_tutor_help = models.TextField()
    what_did_you_learn = models.TextField()
    how_can_tutor_improve = models.TextField()

    tutor_trainer = models.ForeignKey(Profile, verbose_name="Who was your tutor trainer?", related_name="roleplay_training_form", on_delete=models.SET_NULL, null=True)
    tutor_trainer_rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], verbose_name="On a scale of 1-5, how knowledgeable was your trainer?", null=True)
    training_practical = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], verbose_name="On a scale of 1-5, how practical was the training?", null=True)
    overall_quality_rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], verbose_name="On a scale of 1-5, how would you rate the overall quality of the training?", null=True)
    suggestions = models.TextField("What suggestions would you have for future training?", default="")

    def __str__(self):
        if self.tutor_trainer:
            return f"{self.user.profile.full_name or self.user.username} (Trainer {self.tutor_trainer})"
        else:
            return f"{self.user.profile.full_name or self.user.username}"

class Orientation1(models.Model):
    CHOICES1 = (
        (0,'After completing this training module'),
        (1,'After completing all training modules'),
        (2,'After completing background check'),
        (3,'After completing first tutoring session')
    )
    CHOICES2 = (
        (0,'Student Transcript + Letter of Reference + Parental Consent'),
        (1,'Student Transcript + Background check'),
        (2,'Letter of Employment Verification + Background Check'),
        (3,'Professional Letter of Reference + Background Check')
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    question1 = models.IntegerField(choices=CHOICES1, null=True, blank=True)
    question2 = models.IntegerField(choices=CHOICES2, null=True, blank=True)
    occupation = models.IntegerField(default=5, null=True, blank=True)
    completed = models.DateTimeField(default=None, blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.profile.full_name or self.user.username}"

class Orientation2(models.Model):
    CHOICES1 = (
        (0,'Socio-economic roadblocks and a lack of public investment'),
        (1,'Socio-economic roadblocks and lack of private investment'),
        (2,'Socio-emotional roadblocks and lack of public investment'),
        (3,'Socio-emotional roadblocks and lack of private investment')
    )
    CHOICES2 = (
        (0,'Flexibility and availability for drop-in sessions'),
        (1,'Provides both remediation and enrichment support'),
        (2,'Potential for working with other programs that serve students'),
        (3,"Data tracking and sharing information with stakeholders in a student's learning development (instructors, program managers, advisors, etc)."),
        (4,'Tutor training in alignment with minimalism best practices (the student is the driver; enhances learning autonomy and learning confidence).')
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    question1 = models.IntegerField(choices=CHOICES1, null=True, blank=True)
    question2 = MultiSelectField(choices=CHOICES2, null=True, blank=True)
    completed = models.DateTimeField(default=None, blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.profile.full_name or self.user.username}"

class Orientation3(models.Model):
    CHOICES1 = (
        (0,"Change your available hours to 0 in the 'Settings' tab"),
        (1,"Cancel confirmation for the scheduled session in the 'Meetings' tab"),
        (2,"Use the student's contact information to inform them that you can't make the session"),
        (3,'None of the above')
    )
    CHOICES2 = (
        (0,'Learn biology concepts in order to help the student'),
        (1,'Direct the student to the student portal and have them place a request for a biology tutor'),
        (2,'Tell the student to talk with their biology instructor and have them ask for school related resources to help the student'),
        (3, "Tell the student you can’t help with anything outside of the subject you have signed up to support.")
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    question1 = MultiSelectField(choices=CHOICES1, blank=True, null=True)
    question2 = MultiSelectField(choices=CHOICES2, blank=True, null=True)
    completed = models.DateTimeField(default=None, blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.profile.full_name or self.user.username}"

class Orientation4(models.Model):
    CHOICES1 = (
        (0,"Notify your tutee via email in advance"),
        (1,"Provide a detailed explanation of the reason for your absence"),
        (2,"Ask your tutee for alternate days/times to reschedule the missed session"),
        (3,'Inform your tutee after you missed the scheduled session')
    )
    CHOICES2 = (
        (0,'Announce in the group session that the tutee failed the school math test'),
        (1,'Send the tutee an email expressing your disappointment and frustration'),
        (2,'Respond privately and set up a time to meet the tutee individually to better understand why he/she failed the test'),
        (3,"Respond to the tutee’s email by asking the tutee to do better next time")
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    question1 = MultiSelectField(choices=CHOICES1, blank=True, null=True)
    question2 = models.IntegerField(choices=CHOICES2, blank=True, null=True)
    completed = models.DateTimeField(default=None, blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.profile.full_name or self.user.username}"

class Orientation5(models.Model):
    CHOICES1 = (
        (0,"Help build the tutees’ confidence and help them achieve learning autonomy"),
        (1,"Provide the support necessary to help the tutees get from where they are to where they want to be"),
        (2,"Teach new concepts to the tutees in the subjects that you are tutoring in"),
        (3,"Build the tutees’ critical thinking abilities by engaging in active dialogue"),
        (4, "Ensure grade improvment for the student by the end of the semester")
    )
    CHOICES2 = (
        (0,'You complete the assignment and send it to the tutee'),
        (1,'You respond by saying that you can help the tutee in your next tutoring session to review the assignment and provide guidance on how to complete it'),
        (2,'You ask the tutee to ask someone else to complete it for them'),
        (3,"Ignore the tutee")
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    question1 = MultiSelectField(choices=CHOICES1, blank=True, null=True)
    question2 = models.IntegerField(choices=CHOICES2, blank=True, null=True)
    completed = models.DateTimeField(default=None, blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.profile.full_name or self.user.username}"

class Orientation6(models.Model):
    CHOICES1 = (
        (0,"Show the tutee a video you found that explains the concept"),
        (1,"Clear the entire session's schedule to focus on the concept. Do not move on until the student has achieved mastery"),
        (2,"Enhance their understanding by asking relevant probing questions to promote reflection and guide their thinking towards an understanding of the concepts"),
        (3,"Direct the tutee to an online article you found that can help him/her understand the concepts")
    )
    CHOICES2 = (
        (0,'Help the tutee make a study schedule where he/she reviews the concept at regular intervals'),
        (1,'Revisit the concept in your tutoring sessions from time to time'),
        (2,'Move on to new material, and ignore past concepts'),
        (3,"Go over their performance on the test in your session and reiterate the tutee’s understanding of the concept")
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    question1 = MultiSelectField(choices=CHOICES1, blank=True, null=True)
    question2 = MultiSelectField(choices=CHOICES2, blank=True, null=True)
    completed = models.DateTimeField(default=None, blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.profile.full_name or self.user.username}"

class Orientation7(models.Model):
    CHOICES1 = (
        (0,"Solid internet connection"),
        (1,"Ipad/tablet to screenshare on"),
        (2,"Quiet Space"),
        (3,"Working Video camera")
    )
    CHOICES2 = (
        (0,'Create a collaborative whiteboard that we can write problems on or upload the pictures that the student shared to'),
        (1,'Inform the tutee that a successful tutorial session requires a device that they can participate in the session with, and to reschedule once they have procured that'),
        (2,'Use probing questions to have the tutee clarify their understanding of concepts, and guide them when needed'),
        (3,"Annotate what the tutee says on any collaborative work for their review outside of the session")
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    question1 = MultiSelectField(choices=CHOICES1, blank=True, null=True)
    question2 = MultiSelectField(choices=CHOICES2, blank=True, null=True)
    completed = models.DateTimeField(default=None, blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.profile.full_name or self.user.username}"

class Orientation8(models.Model):
    CHOICES1 = (
        (0,"Confirm that the time scheduled works for you. If it doesn't, decline the meeting"),
        (1,"Send the student an email introducing yourself"),
        (2,"Send the student information to join the session"),
        (3,"Ask the student for information regarding what they would like to work on before the session"),
        (4,"Ask student for their address, and visit them in-person to facilitate the first session")
    )
    CHOICES2 = (
        (0,'Start the clock in on the tutor portal'),
        (1,'Introduce yourself and give them a little of your academic background'),
        (2,"Ask the student if they have participated in The City Tutors' cost-sharing to provide services to the entire city in order for the session to continue"),
        (3,"Ask the student to introduce themselves, and what they want to improve on"),
        (4,"Exchange preferred contact information")
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    question1 = MultiSelectField(choices=CHOICES1, blank=True, null=True)
    question2 = MultiSelectField(choices=CHOICES2, blank=True, null=True)
    completed = models.DateTimeField(default=None, blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.profile.full_name or self.user.username}"

class Orientation9(models.Model):
    CHOICES1 = (
        (0,"On a remote call with the student, the tutor is dressed business casual. They have their camera on. Their background is blurred out. There is no more than a fist of space above the head in camera view. They look at the student as they are speaking, and their hands are at their side."),
        (1,"On a remote call with the student, the tutor is wearing a plain T-shirt. There is no more than a fist of space above the head in camera view. You can see their apartment. They sometimes turn off the camera, but typically have it on and are looking at the student when they are speaking, and their hands are at their side."),
        (2,"On a remote call with the student, the tutor is wearing a business suit. The tutor is sitting further away from the camera. Their arms are folded as they speak, and they often look to the side when the student is speaking."),
        (3,"In an in-person session with the student, the tutor is wearing a tank top. The tutor is sitting across the table from a student, and is switching between checking their phone and then asking the student questions on their assignment."),
        (4,"In an in-person session with the student, the tutor is dressed business casual. The tutor is sitting on the same side as the student. The tutor respects the students space, and also doesn't control the students material. They are looking at the student when they speak, and are looking at the material as the student works on the problem.")
    )
    CHOICES2 = (
        (0,"The student brings in an assignment where the teacher gave them an F. The tutor spends the session highlighting pieces of their work where they went wrong, and said that the student must change how they do assignments in the future. The student attemps to explain their reasoning, but the tutor cuts them off as the session is only an hour long and there is a lot of material in the student's work that needs to be corrected"),
        (1,"The student brings in an assignment where the teacher said the work needs revision. The tutor starts off by asking the student what they understand the assignment to require. The student answers, but its clear that they don't fully understand what is required, so the tutor asks questions focusing on the concepts involved"),
        (2,"The student comes to the session crying, because the teacher gave them an F on their test and they had the student make their parents sign the test and then give it back to the instructor. The student starts off the session saying how they were also bad with the concept, and the test reinforces that perception. The tutor allows the student to talk, and then goes on to explain that this in not a reflection of the student's future potential with the material. The tutor goes on to say that no one has mastery in the beginning, and it requires time and practice to see permenant improvement. The tutor encourages the student to not give up, and to use the test as an opportunity to identify what can be worked on to improve"),
        (3,"A college student or adult learner comes in to the session, and says that the instructor gave them no homework. The tutor asks the student if there are any tests or quizzes coming up, and if they want to prepare for that. The student shows disinterest in the material. The tutor asks them what their long term goals are, and talks about how this class fits into that long term goal."),
        (4,"A K - 12 student comes into the session. They say that their parent/program made them sign up for tutoring and they don't feel that they need support. The tutor then asks the student how they performed on their last grade. The student says they don't remember, so the tutor asks them if there is anything from the subject matter that is confusing them. The students says no, and the tutor responds with that's okay. Tutoring isn't about just dealing with issues in understanding material. It is also about enriching their understanding of the topic. If it's a STEM subject, the tutor has the student select an intermediate or hard question that the student needs to walk the tutor through. If its a writing tutorial, the student can do some freewriting for the tutor to review."),
        (5,"The student comes in to the session, and says that the instructor gave them no homework. The tutor asks what the student would like to work on, and the student says that they don't have anything. The tutor decides that, because there is no material to work on, they will end the session early and meet the student again next week")
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    question1 = MultiSelectField(choices=CHOICES1, blank=True, null=True)
    question2 = MultiSelectField(choices=CHOICES2, blank=True, null=True)
    completed = models.DateTimeField(default=None, blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.profile.full_name or self.user.username}"

class Orientation10(models.Model):
    CHOICES1 = (
        (0,"Ask the student(s) to recap what they took away from the session"),
        (1,"Remind student or student's parent to go to the City Tutors' website, and use the 'donate' button in order to continue receiving services in the future"),
        (2,"You recap what was discussed in the session"),
        (3,"Ask the student(s) if they want to have another session."),
        (4,"Clock Out on the tutor Portal")
    )
    CHOICES2 = (
        (0,'Remind them that they can request support in the future through their student portal'),
        (1,'Remind them to fill out an exit ticket that will be sent over the student portal'),
        (2,"Have the student tell 2-5 friends about the tutoring service, and have them create accounts and register to receive tutoring support"),
        (3,"If your preferences for tutoring have changed as a result of the student no longer having sessions with you, update the 'settings' tab in your tutor portal")
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    question1 = MultiSelectField(choices=CHOICES1, blank=True, null=True)
    question2 = MultiSelectField(choices=CHOICES2, blank=True, null=True)
    completed = models.DateTimeField(default=None, blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.profile.full_name or self.user.username}"

class Orientation11(models.Model):
    CHOICES1 = (
        (0,"Minimalism requires the tutor to always be hands-off. If the student is stuck, it is always valuable to keep asking questions. Students will eventually be able to solve the problem on their own."),
        (1,"It requires tutors to start by asking the student questions about what they know"),
        (2,"When students say they don't know what to do next, minimalism has the tutor ask questions to see if the student can get to the next stage of the problem"),
        (3,"If student cannot continue with the problem after the tutor asked them questions, minimalism requires the tutor to provide a model for them a problem solving strategy that the student can apply to their own problem"),
    )
    CHOICES2 = (
        (0,'Help the student to develop strategies for annotating texts, and taking notes in class'),
        (1,'Help the student to develop a time management strategy for studying the material'),
        (2,"Help the student to reflect on commonly recurring issues within their knowledge of concepts, or application of problem solving stratgies"),
        (3,"Help the student to develop a discrete means of contacting the tutor for answers should they need help during tests or exams (Available only to students who have subscribed to The City Tutors Plus service)")
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    question1 = MultiSelectField(choices=CHOICES1, blank=True, null=True)
    question2 = MultiSelectField(choices=CHOICES2, blank=True, null=True)
    completed = models.DateTimeField(default=None, blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.profile.full_name or self.user.username}"

class LiveSession(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    trainer = models.ForeignKey(Profile, on_delete=models.CASCADE, blank=True, null=True)
    q1 = models.TextField("What do you see as the role of the tutor? How do you see yourself as a tutor?", blank=True, null=True)
    q2 = models.TextField('Recall the module: Ethics and Professionalism. Identify 3-4 characteristics, elements, or key points you took from that module', blank=True, null=True)
    q3 = models.TextField("Explain how this topic impacts your practice as a tutor.", blank=True, null=True)
    q4 = models.TextField("What did you work on? What difficulties were you experiencing in the session, and how would you rate the student’s ability to complete the assignment on their own?", blank=True, null=True)
    q5 = models.TextField("What strategies did you use to keep the session on track?", blank=True, null=True)
    q6 = models.TextField("What could you have done better?", blank=True, null=True)
    q7 = models.TextField("What was easy? What went well?", blank=True, null=True)
    q8 = models.TextField("What was difficult? What could be improved?", blank=True, null=True)
    q9 = models.TextField("Where would you like more support? What kind of support would you like to receive?", blank=True, null=True)
    completed = models.DateTimeField(default=None, blank=True, null=True)

    def __str__(self):
        return f"{self.user.profile.full_name or self.user.username}"

class Dashboard(Profile):
    class Meta:
        proxy = True
        verbose_name = 'Dashboard'
        verbose_name_plural = 'Dashboard'