import datetime as dt
import factory
from django.utils import timezone
from .models import (
    User,
    Profile,
    ExitTicket,
    TutorRequest,
    Meeting,
    Sector,
    AccountType,
    Subject,
    TimeSlot,
    MeetingMembership,
)


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Faker("email")
    password = factory.PostGenerationMethodCall("set_password", "123")


class K12TuteeProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Profile

    user = factory.SubFactory(UserFactory)
    nickname = "Tutee"
    account_type = AccountType.objects.get(display="K-12-Tutee")
    sector = Sector.objects.get(display="Elementary School")
    zip_code = 10001
    onboarded = True
    can_speak_english = True


class CollegeTuteeProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Profile

    user = factory.SubFactory(UserFactory)
    nickname = "Tutee"
    account_type = AccountType.objects.get(display="College-Tutee")
    sector = Sector.objects.get(display="College")


class TutorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Profile

    user = factory.SubFactory(UserFactory)
    nickname = "Tutor"
    account_type = AccountType.objects.get(display="Tutor")
    offered_sectors = factory.Iterator(Sector.objects.all())
    offered_hours = 5

    @factory.post_generation
    def offered_sectors(self, create, extracted, **kwargs):
        if not create:
            for sector in Sector.objects.all():
                self.offered_sectors.add(sector)
            return

        if extracted:
            for sector in extracted:
                self.offered_sectors.add(sector)


class TutorRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TutorRequest

    subject = Subject.objects.get(
        sector=Sector.objects.get(display="Elementary School"),
        display="Reading",
    )
    notes = "I need help on my homework"
    active = True
    timestamp = timezone.now()


class MeetingMembershipFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MeetingMembership

    status = "Confirmed"


class ScheduledMeetingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Meeting

    active=True
    scheduled_time_slot = TimeSlot.objects.get(pk=10)
    scheduled_start = timezone.now() + dt.timedelta(days=3)


class PastMeetingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Meeting

    active=True
    scheduled_time_slot = TimeSlot.objects.get(pk=10)
    scheduled_start = timezone.now() - dt.timedelta(days=8)
    start_datetime = timezone.now() - dt.timedelta(days=8)
    stop_datetime = start_datetime + dt.timedelta(hours=1)
    notes = "We worked on reviewing last week's homework"

    @factory.post_generation
    def attendance(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for user in extracted:
                self.attendance.add(user)

    @factory.post_generation
    def members(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for user in extracted:
                self.members.add(user)


def create_past_meeting(tutee, tutor, start_datetime=None):
    if start_datetime:
        meeting = PastMeetingFactory(
            attendance=(tutee, tutor),
            start_datetime=start_datetime,
            scheduled_start=start_datetime,
        )
    else:
        meeting = PastMeetingFactory(
            attendance=(tutee, tutor),
        )
    MeetingMembershipFactory(user=tutee, meeting=meeting, user_role="Tutee")
    MeetingMembershipFactory(user=tutor, meeting=meeting, user_role="Tutor")
    TutorRequestFactory(user=tutee, meeting=meeting)

    return meeting


def create_previous_linked_meeting(tutee, tutor, meeting):
    previous_meeting = PastMeetingFactory(
        attendance=(tutee, tutor),
    )
    MeetingMembershipFactory(user=tutee, meeting=previous_meeting, user_role="Tutee")
    MeetingMembershipFactory(user=tutor, meeting=previous_meeting, user_role="Tutor")
    previous_meeting.follow_up_meeting = meeting
    previous_meeting.save()
    return previous_meeting


def create_next_linked_meeting(tutee, tutor, meeting, future=False):
    tutor_request = meeting.tutorrequest_set.all().first()

    if future:
        follow_up_meeting = ScheduledMeetingFactory(
            scheduled_start=timezone.now()+dt.timedelta(days=3),
        )
    else:
        follow_up_meeting = PastMeetingFactory(attendance=(tutee, tutor),)

    MeetingMembershipFactory(user=tutee, meeting=follow_up_meeting, user_role="Tutee")
    MeetingMembershipFactory(user=tutor, meeting=follow_up_meeting, user_role="Tutor")
    meeting.follow_up_meeting = follow_up_meeting
    meeting.save()

    tutor_request.meeting = follow_up_meeting
    tutor_request.save()
    return follow_up_meeting
