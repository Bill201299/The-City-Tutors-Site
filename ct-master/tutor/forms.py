import re
import uuid
import hashlib
import datetime
import collections
import math
from calendar import day_name, month_name

import pytz
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, ButtonHolder, Submit, Field, HTML
from crispy_forms.bootstrap import Div, StrictButton, FieldWithButtons
from crispy_forms import layout, bootstrap
from django.template import loader
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.forms import (
    modelformset_factory,
    Widget,
    Form,
    HiddenInput,
    ModelForm,
    ModelChoiceField,
    RadioSelect,
    Select,
    CheckboxSelectMultiple,
    SelectMultiple,
    ModelMultipleChoiceField,
    MultipleChoiceField,
    CharField,
    IntegerField,
    ValidationError,
    DateField,
    TimeField,
    MultiValueField,
    BooleanField,
    ChoiceField,
    PasswordInput,
    BaseModelFormSet,
)
import django.forms
from django.forms import formset_factory
from django.forms.widgets import DateInput, TimeInput, Textarea, NumberInput
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm, UsernameField
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models import Q
from phonenumber_field.formfields import PhoneNumberField
from django import forms
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.forms import SetPasswordForm
from django.utils.translation import ugettext_lazy  as _

from .models import (
    Orientation3,
    OrientationTraining,
    TutorTraining,
    RoleplayTraining,
    TutorRequest,
    Profile,
    Meeting,
    Site,
    SiteLocation,
    Sector,
    Ethnicity,
    Gender,
    Pronouns,
    TimeSlot,
    Subject,
    BackgroundCheckRequest,
    TuteeAssessment,
    Issue,
    MeetingMembership,
    ExitTicket,
    ExitTicketDifficult,
    ExitTicketMedium,
    ExitTicketEasy,
    LeaveTicket,
    TutorOfferedMonthlyHours,
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
)

form_helper = FormHelper()
form_helper.form_tag = False



class ChosenSelectMultiple(SelectMultiple):
    """
    Chosen elements are not compatible with the required attribute
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs['class'] = "chosen-select"
        self.attrs['data-placeholder'] = "Click to select"
    def use_required_attribute(self, initial):
        return False


class ChosenSelect(Select):
    """
    Chosen elements are not compatible with the required attribute
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs['class'] = "chosen-select"
        self.attrs['data-placeholder'] = "Click to select"
    def use_required_attribute(self, initial):
        return False


class TuteeChoiceField(ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.tutee}"


class TuteesChoiceField(ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.tutee}"


class UserChoiceField(ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.profile.full_name or obj.profile.nickname or obj.username}"


class UserMultipleChoiceField(ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        try:
            return f"{obj.profile.full_name or obj.profile.nickname or obj.username}"
        except Profile.DoesNotExist:
            return obj.username


class RankPicker(Field):
    template = "tutor/forms/widgets/rank_widget.html"

    def render(self, *args, **kwargs):
        form, *others = args
        rank_field = form.fields[self.fields[0]]
        rank_objects = [x for x in rank_field.queryset]
        kwargs["extra_context"] = {
            "rank_numbers": [n + 1 for n in range(len(rank_objects))],
            "rank_objects": rank_objects,
        }
        return super().render(*args, **kwargs)


class RankField(django.forms.Field):
    def __init__(self, *args, queryset, **kwargs):
        self.queryset = queryset
        self.num_ranks = len(self.queryset)
        self.string_to_objects = {c.value_text: c for c in self.queryset}
        super().__init__(*args, **kwargs)

    def clean(self, value):
        if len(set(value)) != self.num_ranks:
            raise ValidationError("No duplicates allowed in ranking")
        return [self.string_to_objects[v] for v in value]


class CancelMeetingForm(Form):
    meeting = ModelChoiceField(queryset=None)

    def __init__(self, *args, scheduled_meetings, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.fields["meeting"].queryset = scheduled_meetings
        self.helper.layout = Layout(
            "meeting",
            layout.Submit(
                "cancel_meeting", "Cancel Meeting", css_class="btn btn-danger my-2"
            ),
        )


class UndoForm(Form):
    meeting = ModelChoiceField(queryset=None)

    def __init__(self, *args, canceled_meetings, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.fields["meeting"].queryset = canceled_meetings
        self.helper.layout = Layout(
            "meeting",
            layout.Submit(
                "undo_cancel_meeting",
                "Undo Cancel Meeting",
                css_class="btn btn-primary my-2",
            ),
        )


class StartClockForm(Form):
    meeting = ModelChoiceField(queryset=None)

    def __init__(self, *args, meetings, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["meeting"].queryset = meetings
        self.helper = FormHelper()
        self.helper.layout = Layout(
            "meeting",
            layout.Submit(
                "start_clock", "Start Clock", css_class="btn btn-primary my-2"
            ),
        )


class StopClockForm(Form):
    date = DateField(widget=DateInput(attrs={"type": "date"}))
    start_time = TimeField(widget=TimeInput(format='%H:%M', attrs={"type": "time", "step": "any"}))
    stop_time = TimeField(widget=TimeInput(format='%H:%M', attrs={"type": "time", "step": "any"}))
    attendance = ModelMultipleChoiceField(
        queryset=None,
        widget=ChosenSelectMultiple(),
        required=False
    )
    notes = CharField(required=True, widget=Textarea(attrs={"rows": 4}))
    repeat = ModelMultipleChoiceField(
        queryset=None,
        widget=ChosenSelectMultiple(),
        required=False
    )

    def __init__(self, *args, members=None, requests=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.fields["attendance"].queryset = members
        self.fields['attendance'].initial = members
        self.fields["attendance"].help_text = mark_safe(
            "<br> Check out this <a href=https://youtu.be/tbc6zGo00oc> video </a>on how to mark absent students."
            )
        self.fields["repeat"].label = "Select students who will attend a repeat session next week (leave blank if unneeded)"
        self.fields["repeat"].help_text = "A meeting will be scheduled at the same time next week for the same subject including all students you select here. Please check your meetings page after submitting"
        self.fields["repeat"].queryset = members
        self.helper.layout = Layout(
            "date",
            "start_time",
            "stop_time",
            "attendance",
            "notes",
            "repeat",
            layout.Submit("stop_clock", "Stop Clock", css_class="btn btn-primary my-2"),
        )

        if not requests:
            self.fields["repeat"].widget = HiddenInput()

    def clean(self):
        if len(self.cleaned_data["notes"]) < 60:
            raise ValidationError(
                "Please write more than 60 characters for meeting notes"
            )

        local_tz = pytz.timezone('America/New_York')
        start_datetime = local_tz.localize(datetime.datetime.combine(self.cleaned_data["date"], self.cleaned_data["start_time"]))
        stop_datetime = local_tz.localize(datetime.datetime.combine(self.cleaned_data["date"], self.cleaned_data["stop_time"]))

        if start_datetime > stop_datetime:
            raise ValidationError("Clock out time cannot be earlier than clock in time")
        if stop_datetime > timezone.localtime():
            raise ValidationError("Clock out time cannot be in the future")
        if (stop_datetime - start_datetime).total_seconds() / 60 < 5:
            raise ValidationError("Your session must be at least 5 minutes")
        if (stop_datetime - start_datetime).total_seconds() / 60 / 60 > 6:
            raise ValidationError("Your session duration has exceeded the maximum allowed duration of 6 hours.")



        if "repeat" in self.cleaned_data:
            repeats = list(self.cleaned_data["repeat"])
            attended = list(self.cleaned_data["attendance"])
            if not all(elem in attended for elem in repeats):
                raise ValidationError("You cannot schedule a student for a repeat meeting if they haven't attended this meeting")


class MeetingStartClockForm(Form):
    def __init__(self, *args, members=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            layout.Submit("start_clock", "Clock Into Meeting", css_class="btn btn-primary my-2"),
        )


class MeetingStopClockForm(Form):
    def __init__(self, *args, members=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            layout.Submit("start_clock", "Clock Out of Meeting", css_class="btn btn-primary my-2"),
        )


class TuteeAssessmentForm(ModelForm):
    class Meta:
        model = TuteeAssessment
        exclude = ["meeting"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.fields["tutee"].disabled = True
        self.fields["assessment"].widget.attrs["min"] = 0
        self.fields["assessment"].widget.attrs["max"] = 20
        self.fields["assessment"].label = "Student Autonomy (0-20)"
        self.fields["grade"].label = "Grade received in the past week (if any):"
        self.fields["tutee"].widget.attrs.update({
            'class': 'form-control'
        })
        self.fields["assessment"].widget.attrs.update({
            'class': 'form-control'
        })
        self.fields["grade"].widget.attrs.update({ 
            'class': 'form-control'
        })
        self.helper.layout = Layout(
            "tutee",
            "assessment",
            "grade",
        )


class IssueForm(ModelForm):
    class Meta:
        model = Issue
        fields = ["type", "description", "contact_email", "related_user"]

    def __init__(self, *args, user=None, **kwargs):
        if user is not None and user.is_authenticated:
            kwargs["initial"] = {}
            kwargs["initial"]["contact_email"] = user.email
        super().__init__(*args, **kwargs)
        self.fields["related_user"] = UserChoiceField(queryset=None, required=False)

        if user is not None and user.is_authenticated:
            self.fields["contact_email"].widget.attrs["readonly"] = True
            self.fields["contact_email"].required = False
            self.fields["related_user"].queryset = (
                User.objects.filter(meeting__in=user.meeting_set.all())
                .distinct()
                .exclude(pk=user.pk)
            )
        else:
            self.fields["related_user"].queryset = User.objects.none()
            self.fields["related_user"].disabled = True
        self.helper = FormHelper()
        self.helper.layout = Layout(
            "type",
            Field("description", rows=2),
            "contact_email",
            "related_user",
            layout.Submit("submit", "Submit", css_class="btn btn-primary my-2"),
        )


class TuteeIssueForm(Form):
    issue_description = CharField()
    issue_tutee = TuteeChoiceField(queryset=None)

    def __init__(self, *args, approved_connections, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["issue_tutee"] = TuteeChoiceField(queryset=approved_connections)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            "issue_tutee", "issue_description", ButtonHolder(Submit("submit", "Submit"))
        )


class HarassIssueForm(Form):
    issue_description = CharField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            "issue_description", ButtonHolder(Submit("submit", "Submit"))
        )


class TuteeProfileForm(ModelForm):
    class Meta:
        model = Profile
        fields = [
            "full_name", "nickname", "gender", "phone_number", "available",
            "sector", "site", "site_location", "sms_notifications"
        ]
        widgets = {
            "available": ChosenSelectMultiple()
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.fields["available"].widget.attrs["size"] = 10
        self.fields['sector'].disabled = True
        self.fields["sms_notifications"].label = "I would like to be notified about my sessions (such as new and cancelled sessions) via text (SMS)"
        self.fields["full_name"].required = True
        tutee_settings_fieldset = Fieldset(
            "Student Settings",
            "sector",
            "requested_hours",
            "requested_subjects",
            "site",
            "site_location",
            "notes",
        )
        general_settings_fieldset = Fieldset(
            "General Settings",
            "full_name",
            "nickname",
            "can_speak_english",
            "available",
            "race",
            "gender",
            "phone_number",
            "sms_notifications",
        )
        self.helper.layout = Layout(
            general_settings_fieldset,
            tutee_settings_fieldset,
        )

    def clean(self):
        errors = {}
        if len(self.cleaned_data["available"]) < 2:
            errors["available"] = "Please select at least 3 time slots"
        if errors:
            raise ValidationError(errors)


class TutorProfileForm(ModelForm):
    class Meta:
        model = Profile
        fields = [
            "full_name",
            "nickname",
            "gender",
            "phone_number",
            "available",
            "offered_sectors",
            "offered_subjects",
            "tutee_contact",
            "sms_notifications"
        ]
        widgets = {
            "available": ChosenSelectMultiple(),
            "offered_sectors": ChosenSelectMultiple(),
            "offered_subjects": ChosenSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.fields["available"].widget.attrs["size"] = 10
        self.fields["available"].label += " - Eastern Time"
        self.fields["tutee_contact"].label = (
            "Describe to the student how they should contact you at your scheduled time"
        )
        self.fields['tutee_contact'].widget.attrs['placeholder'] = 'Join meeting room at: https://...'
        self.fields["sms_notifications"].label = "I would like to be notified about my sessions (such as new and cancelled sessions) via text (SMS)"
        self.fields["full_name"].required = True
        general_settings_fieldset = Fieldset(
            "General Settings",
            "full_name",
            "nickname",
            "can_speak_english",
            HTML(r"""
                <small><a href='{% url 'tutor:unfulfilled-requests' %}'>See unfulfilled requests</a></small>
            """),
            "available",
            
            "race",
            "gender",
            "phone_number",
            "sms_notifications",
        )
        tutor_settings_fieldset = Fieldset(
            "Tutor Settings",
            "offered_sectors",
            "offered_subjects",
            "tutee_contact",
        )
        self.helper.layout = Layout(
            general_settings_fieldset,
            tutor_settings_fieldset,
        )

    def clean(self):
        errors = {}
        if len(self.cleaned_data["available"]) < 2:
            errors["available"] = "Please select at least 3 time slots"
        if errors:
            raise ValidationError(errors)


class BackgroundForm(Form):
    full_name = CharField(required=False)
    phone_number = PhoneNumberField(required=False)
    email = CharField(required=False)
    confirm_sign = forms.CharField(
        label="",
        required = True,
    )
    
    def clean(self):
        errors = {}
        if not self.user.email:
            errors["email"] = "Contact an administrator to update your email"
        if not self.user.profile.phone_number:
            errors["phone_number"] = "Update your phone number in your profile"
        if not self.user.profile.full_name:
            errors["full_name"] = "Update your full name in your profile"
        if errors:
            raise ValidationError(errors)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["full_name"].widget.attrs["readonly"] = True
        self.fields["phone_number"].widget.attrs["readonly"] = True
        self.fields["email"].widget.attrs["readonly"] = True
        submit_button = StrictButton(id="id_submit", type="input", content="Submit", name="send", css_class="btn btn-primary", style="margin: auto")
        self.helper = FormHelper()
        self.helper.layout = Layout(
            "full_name",
            "phone_number",
            "email",
            HTML("""<br>"""),
            "confirm_sign",
            HTML("""{% load static %}By signing above using your full name, you agree to our <a href="{% static '/tutor/Background Check Mandatory Screening Policy.pdf' %}" target="_blank">Background Check Policy</a>.<br><br>"""),
            
            submit_button,
        )


class TutorFilterForm(Form):
    subject = BooleanField(required=False)
    time_availability = BooleanField(required=False)
    available_hours = BooleanField(required=False)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            "subject",
            "time_availability",
            "available_hours",
            layout.Submit("refresh", "Refresh", css_class="btn btn-primary my-2"),
        )


class ProgramCoordinatorRegistrationForm(Form):
    email = CharField(max_length=200)
    username = CharField(max_length=200)
    password = CharField(widget=PasswordInput, max_length=200)
    confirm_password = CharField(widget=PasswordInput, max_length=200)
    full_name = django.forms.models.fields_for_model(Profile)["full_name"]
    full_name.required = True 
    nickname = django.forms.models.fields_for_model(Profile)["nickname"]
    site = ModelChoiceField(
        queryset=Site.objects.exclude(display="Not Specified"), required=True
    )
    site_location = ModelChoiceField(
        queryset=SiteLocation.objects.exclude(display="Not Specified"), required=False
    )

    def clean_username(self):
        errors = []
        if User.objects.filter(username=self.cleaned_data["username"]):
            errors.append("This username is already taken")
        if " " in self.cleaned_data["username"]:
            errors.append("Don't include spaces in your username")
        if errors:
            raise ValidationError(errors)
        return self.cleaned_data["username"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            "email",
            "username",
            "password",
            "confirm_password",
            "full_name",
            "nickname",
            "site",
            "site_location",
            layout.Submit("submit", "Submit", css_class="btn btn-primary my-2"),
        )


class TutorRegistrationForm(Form):
    email = CharField(max_length=200)
    username = CharField(max_length=200)
    password = CharField(widget=PasswordInput, max_length=200)
    confirm_password = CharField(widget=PasswordInput, max_length=200)
    can_you_speak_english = ChoiceField(
        choices=(("No", "No"), ("Yes", "Yes")), widget=RadioSelect()
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.fields["can_you_speak_english"].label = "Is English your native language?"
        self.helper.layout = Layout(
            "email",
            "username",
            "password",
            "confirm_password",
            "can_you_speak_english",
            layout.Submit("submit", "Submit", css_class="btn btn-primary my-2"),
        )

    def clean_username(self):
        errors = []
        if User.objects.filter(username=self.cleaned_data["username"]):
            errors.append("This username is already taken")
        if " " in self.cleaned_data["username"]:
            errors.append("Don't include spaces in your username")
        if errors:
            raise ValidationError(errors)
        return self.cleaned_data["username"]

    def clean(self):
        errors = {}
        if self.data["password"] != self.data["confirm_password"]:
            errors["password"] = "The passwords you entered do not match."
        if len(self.data["password"]) < 8:
            errors["password"] = "Your password must be at least 8 characters"
        if errors:
            raise ValidationError(errors)

        self.cleaned_data["can_you_speak_english"] = False
        if self.data["can_you_speak_english"] == "Yes":
            self.cleaned_data["can_you_speak_english"] = True


class K12RegistrationForm(Form):
    email = CharField(max_length=200)
    username = CharField(max_length=200)
    password = CharField(widget=PasswordInput, max_length=200)
    confirm_password = CharField(widget=PasswordInput, max_length=200)
    student_zip_code = CharField(max_length=5)
    student_speaks_english = ChoiceField(
        choices=(("No", "No"), ("Yes", "Yes")), widget=RadioSelect()
    )
    student_is_in_partner_program = ModelChoiceField(
        queryset=Site.objects.exclude(display="Not Specified"), required=False
    )
    student_is_in_partner_program_location = ModelChoiceField(
        queryset=SiteLocation.objects.exclude(display="Not Specified"), required=False
    )
    student_from_other_location = CharField(max_length = 200, required = False)
    is_parent_or_guardian = ChoiceField(
        choices=(("No", "No"), ("Yes", "Yes")), widget=RadioSelect()
    )
    parent_agree_to_online_tutoring = ChoiceField(
        choices=(("No", "No"), ("Yes", "Yes")), widget=RadioSelect()
    )
    parent_agree_to_meeting_tutor = ChoiceField(
        choices=(("No", "No"), ("Yes", "Yes")), widget=RadioSelect()
    )

    def clean_username(self):
        errors = []
        username = self.cleaned_data["username"]
        if User.objects.filter(username=self.cleaned_data["username"]):
            message = format_html(f'This username is already taken, please choose a different one. If you are {username}, please log in <a href="/login">here</a>.')
            errors.append(message)
        if " " in self.cleaned_data["username"]:
            errors.append("Don't include spaces in your username")
        if errors:
            raise ValidationError(errors)
        return self.cleaned_data["username"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.fields["student_zip_code"].label = "What is the student's zip code?"
        self.fields[
            "student_is_in_partner_program"
        ].label = "Is the student in any of the following programs?"
        self.fields[
            "student_is_in_partner_program_location"
        ].label = "Select the location of the program, if applicable."
        self.fields["student_from_other_location"].label = "Please fill out this field if your program or location is not included in the previous options."
        self.fields["student_speaks_english"].label = "Is English the student's native language?"
        self.fields[
            "is_parent_or_guardian"
        ].label = "Are you the parent or guardian of the student?"
        self.fields[
            "parent_agree_to_online_tutoring"
        ].label = "Do you agree to have your child take part in online tutoring?"
        self.fields[
            "parent_agree_to_meeting_tutor"
        ].label = "Do you agree to meet the tutor for the first 10 minutes of your child's first session?"
        self.helper.layout = Layout(
            "email",
            "username",
            "password",
            "confirm_password",
            "student_zip_code",
            "student_speaks_english",
            "student_is_in_partner_program",
            "student_is_in_partner_program_location",
            "student_from_other_location",
            "is_parent_or_guardian",
            "parent_agree_to_online_tutoring",
            "parent_agree_to_meeting_tutor",
            layout.Submit("submit", "Submit", css_class="btn btn-primary my-2"),
        )

    def clean(self):
        errors = {}
        if not re.match("[0-9]{5}", self.data["student_zip_code"]):
            errors["student_zip_code"] = "Zip code must be 5 digits."
        if self.data["password"] != self.data["confirm_password"]:
            errors["password"] = "The passwords you entered do not match."
        if len(self.data["password"]) < 8:
            errors["password"] = "Your password must be at least 8 characters"
        if self.data["is_parent_or_guardian"] == "No":
            errors[
                "is_parent_or_guardian"
            ] = "You must be the parent or guardian of the student."
        if self.data["parent_agree_to_online_tutoring"] == "No":
            errors[
                "parent_agree_to_online_tutoring"
            ] = "You must agree to online tutoring."
        if self.data["parent_agree_to_meeting_tutor"] == "No":
            errors[
                "parent_agree_to_meeting_tutor"
            ] = "You must agree to meet with the tutor."
        if self.cleaned_data["student_is_in_partner_program_location"] and not self.cleaned_data["student_is_in_partner_program"]:
            site = self.cleaned_data["student_is_in_partner_program_location"].site
            errors["student_is_in_partner_program"] = f"Please select {site} as your site"
        elif self.cleaned_data["student_is_in_partner_program_location"]:
            if self.cleaned_data["student_is_in_partner_program_location"].site != self.cleaned_data["student_is_in_partner_program"]:
                errors["student_is_in_partner_program_location"] = f"The site location you selected is not associated with the partner program you selected above"
        if errors:
            raise ValidationError(errors)

        self.cleaned_data["student_speaks_english"] = False
        if self.data["student_speaks_english"] == "Yes":
            self.cleaned_data["student_speaks_english"] = True


class CollegeRegistrationForm(Form):
    email = CharField(max_length=200)
    username = CharField(max_length=200)
    password = CharField(widget=PasswordInput, max_length=200)
    confirm_password = CharField(widget=PasswordInput, max_length=200)
    student_zip_code = CharField(max_length=5)
    student_speaks_english = ChoiceField(choices=(("No", "No"), ("Yes", "Yes")), widget=RadioSelect())
    student_is_in_partner_program = ModelChoiceField(queryset=Site.objects.exclude(display="Not Specified"), required=False)
    student_is_in_partner_program_location = ModelChoiceField(queryset=SiteLocation.objects.exclude(display="Not Specified"), required=False)
    student_from_other_location = CharField(max_length=200, required = False)

    def clean_username(self):
        errors = []
        if User.objects.filter(username=self.cleaned_data["username"]):
            errors.append("This username is already taken")
        if " " in self.cleaned_data["username"]:
            errors.append("Don't include spaces in your username")
        if errors:
            raise ValidationError(errors)
        return self.cleaned_data["username"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.fields["student_zip_code"].label = "What is your zip code?"
        self.fields["student_is_in_partner_program"].label = "Are you in any of the following programs?"
        self.fields[
            "student_is_in_partner_program_location"
        ].label = "Select the location of the program, if applicable."
        self.fields[
            "student_from_other_location"].label = "Please fill out this field if your program or location is not included in the previous options."
        self.fields["student_speaks_english"].label = "Is English your native language?"
        self.helper.layout = Layout(
            "email",
            "username",
            "password",
            "confirm_password",
            "student_zip_code",
            "student_speaks_english",
            "student_is_in_partner_program",
            "student_is_in_partner_program_location",
            "student_from_other_location",
            layout.Submit('submit', 'Submit', css_class='btn btn-primary my-2'),
        )

    def clean(self):
        errors = {}
        if not re.match("[0-9]{5}", self.data["student_zip_code"]):
            errors["student_zip_code"] = "Zip code must be 5 digits."
        if self.data["password"] != self.data["confirm_password"]:
            errors["password"] = "The passwords you entered do not match."
        if len(self.data["password"]) < 8:
            errors["password"] = "Your password must be at least 8 characters"
        if self.cleaned_data["student_is_in_partner_program_location"] and not self.cleaned_data["student_is_in_partner_program"]:
            site = self.cleaned_data["student_is_in_partner_program_location"].site
            errors["student_is_in_partner_program"] = f"Please select {site} as your site"
        elif self.cleaned_data["student_is_in_partner_program_location"]:
            if self.cleaned_data["student_is_in_partner_program_location"].site != self.cleaned_data["student_is_in_partner_program"]:
                errors["student_is_in_partner_program_location"] = f"The site location you selected is not associated with the partner program you selected above"
        if errors:
            raise ValidationError(errors)

        self.cleaned_data["student_speaks_english"] = False
        if self.data["student_speaks_english"] == "Yes":
            self.cleaned_data["student_speaks_english"] = True


class AdultRegistrationForm(Form):
    email = CharField(max_length=200)
    username = CharField(max_length=200)
    password = CharField(widget=PasswordInput, max_length=200)
    confirm_password = CharField(widget=PasswordInput, max_length=200)
    student_zip_code = CharField(max_length=5)
    student_speaks_english = ChoiceField(choices=(("No", "No"), ("Yes", "Yes")), widget=RadioSelect())
    student_is_in_partner_program = ModelChoiceField(queryset=Site.objects.exclude(display="Not Specified"), required=False)
    student_is_in_partner_program_location = ModelChoiceField(queryset=SiteLocation.objects.exclude(display="Not Specified"), required=False)
    student_from_other_location = CharField(max_length=200, required = False)

    def clean_username(self):
        errors = []
        if User.objects.filter(username=self.cleaned_data["username"]):
            errors.append("This username is already taken")
        if " " in self.cleaned_data["username"]:
            errors.append("Don't include spaces in your username")
        if errors:
            raise ValidationError(errors)
        return self.cleaned_data["username"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.fields["student_zip_code"].label = "What is your zip code?"
        self.fields["student_is_in_partner_program"].label = "Are you in any of the following programs?"
        self.fields[
            "student_is_in_partner_program_location"
        ].label = "Select the location of the program, if applicable."
        self.fields[
            "student_from_other_location"].label = "Please fill out this field if your program or location is not included in the previous options."
        self.fields["student_speaks_english"].label = "Is English your native language?"
        self.helper.layout = Layout(
            "email",
            "username",
            "password",
            "confirm_password",
            "student_zip_code",
            "student_speaks_english",
            "student_is_in_partner_program",
            "student_is_in_partner_program_location",
            "student_from_other_location",
            layout.Submit('submit', 'Submit', css_class='btn btn-primary my-2'),
        )

    def clean(self):
        errors = {}
        if not re.match("[0-9]{5}", self.data["student_zip_code"]):
            errors["student_zip_code"] = "Zip code must be 5 digits."
        if self.data["password"] != self.data["confirm_password"]:
            errors["password"] = "The passwords you entered do not match."
        if len(self.data["password"]) < 8:
            errors["password"] = "Your password must be at least 8 characters"
        if self.cleaned_data["student_is_in_partner_program_location"] and not self.cleaned_data["student_is_in_partner_program"]:
            site = self.cleaned_data["student_is_in_partner_program_location"].site
            errors["student_is_in_partner_program"] = f"Please select {site} as your site"
        elif self.cleaned_data["student_is_in_partner_program_location"]:
            if self.cleaned_data["student_is_in_partner_program_location"].site != self.cleaned_data["student_is_in_partner_program"]:
                errors["student_is_in_partner_program_location"] = f"The site location you selected is not associated with the partner program you selected above"
        if errors:
            raise ValidationError(errors)

        self.cleaned_data["student_speaks_english"] = False
        if self.data["student_speaks_english"] == "Yes":
            self.cleaned_data["student_speaks_english"] = True


class K12OnboardingForm(Form):
    student_full_name = django.forms.models.fields_for_model(Profile)["full_name"]
    student_full_name.required = True
    student_nickname = django.forms.models.fields_for_model(Profile)["nickname"]
    parent_phone_number = PhoneNumberField()
    availability = ModelMultipleChoiceField(
        queryset=TimeSlot.objects.filter(time__gt=6),
        widget=ChosenSelectMultiple(),
    )
    gender = ModelChoiceField(queryset=Gender.objects)
    ethnicity = ModelChoiceField(queryset=Ethnicity.objects)
    sector = ModelChoiceField(
        queryset=Sector.objects.filter(display__in=["Elementary School", "Middle School", "High School"])
    )
    pronouns = ModelChoiceField(queryset=Pronouns.objects)
    used_tutoring_before = ChoiceField(
        choices=(("No", "No"), ("Yes", "Yes")), widget=RadioSelect()
    )

    subject = ModelChoiceField(queryset=Subject.objects.all())
    notes = CharField(required=True, widget=Textarea(attrs={"rows": 4}))

    tutoring_reason = django.forms.models.fields_for_model(Profile)["tutoring_reason"]
    sms_notifications = django.forms.models.fields_for_model(Profile)["sms_notifications"]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.use_required_attribute = False
        self.helper = FormHelper()
        self.fields['availability'].help_text = "Hold control or command to select multiple"
        self.fields[
            "used_tutoring_before"
        ].label = "Has the student used tutoring before?"
        self.fields["ethnicity"].label = "Race"
        self.fields["tutoring_reason"].label = "What led you to request a tutor?"
        self.fields["subject"].label = "Subject you would like support with?"
        self.fields["notes"].label = "What would you like help within in that subject?"
        self.fields["sms_notifications"].label = "I would like to be notified about my sessions (such as new and cancelled sessions) via text (SMS)"
        self.helper.layout = Layout(
            "student_full_name",
            "student_nickname",
            "parent_phone_number",
            "availability",
            "ethnicity",
            "gender",
            "pronouns",
            "sector",
            "used_tutoring_before",
            "tutoring_reason",
            "subject",
            "notes",
            "sms_notifications",
            layout.Submit("submit", "Submit", css_class="btn btn-primary my-2"),
        )

    def clean(self):
        errors = {}
        if "availability" in self.cleaned_data and len(self.cleaned_data["availability"]) < 3:
            errors["availability"] = "Please select at least 3 time slots"
        if errors:
            raise ValidationError(errors)


class CollegeOnboardingForm(Form):
    full_name = django.forms.models.fields_for_model(Profile)["full_name"]
    full_name.required = True
    nickname = django.forms.models.fields_for_model(Profile)["nickname"]
    phone_number = PhoneNumberField()
    availability = ModelMultipleChoiceField(
        queryset=TimeSlot.objects.filter(time__gt=6),
        widget=ChosenSelectMultiple(),
    )
    gender = ModelChoiceField(queryset=Gender.objects)
    ethnicity = ModelChoiceField(queryset=Ethnicity.objects)
    pronouns = ModelChoiceField(queryset=Pronouns.objects)
    used_tutoring_before = ChoiceField(choices=(("No", "No"), ("Yes", "Yes")), widget=RadioSelect())

    subject = ModelChoiceField(queryset=Subject.objects.all())
    notes = CharField(required=True, widget=Textarea(attrs={"rows": 4}))

    tutoring_reason = django.forms.models.fields_for_model(Profile)["tutoring_reason"]
    sms_notifications = django.forms.models.fields_for_model(Profile)["sms_notifications"]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.fields["availability"].widget.attrs['size'] = 10
        self.fields['availability'].help_text = "Hold control or command to select multiple"
        self.fields["ethnicity"].label = "Race"
        self.fields["used_tutoring_before"].label = "Have you used tutoring before?"
        self.fields["tutoring_reason"].label = "What led you to request a tutor?"
        self.fields["subject"].label = "Subject you would like support with?"
        self.fields["notes"].label = "What would you like help within in that subject?"
        self.fields["sms_notifications"].label = "I would like to be notified about my sessions (such as new and cancelled sessions) via text (SMS)"
        self.helper.layout = Layout(
            "full_name",
            "nickname",
            "phone_number",
            "availability",
            "ethnicity",
            "gender",
            "pronouns",
            "used_tutoring_before",
            "subject",
            "notes",
            "tutoring_reason",
            "sms_notifications",
            layout.Submit('submit', 'Submit', css_class='btn btn-primary my-2'),
        )

    def clean(self):
        errors = {}
        if "availability" in self.cleaned_data and len(self.cleaned_data["availability"]) < 3:
            errors["availability"] = "Please select at least 3 time slots"
        if errors:
            raise ValidationError(errors)


class AdultOnboardingForm(Form):
    full_name = django.forms.models.fields_for_model(Profile)["full_name"]
    full_name.required = True
    nickname = django.forms.models.fields_for_model(Profile)["nickname"]
    phone_number = PhoneNumberField()
    availability = ModelMultipleChoiceField(
        queryset=TimeSlot.objects.filter(time__gt=6),
        widget=ChosenSelectMultiple(),
    )
    gender = ModelChoiceField(queryset=Gender.objects)
    ethnicity = ModelChoiceField(queryset=Ethnicity.objects)
    pronouns = ModelChoiceField(queryset=Pronouns.objects)
    used_tutoring_before = ChoiceField(choices=(("No", "No"), ("Yes", "Yes")), widget=RadioSelect())
    tutoring_reason = django.forms.models.fields_for_model(Profile)["tutoring_reason"]
    subject = ModelChoiceField(queryset=Subject.objects.all())
    notes = CharField(required=True, widget=Textarea(attrs={"rows": 4}))
    sms_notifications = django.forms.models.fields_for_model(Profile)["sms_notifications"]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.fields["availability"].widget.attrs['size'] = 10
        self.fields['availability'].help_text = "Hold control or command to select multiple"
        self.fields["ethnicity"].label = "Race"
        self.fields["used_tutoring_before"].label = "Have you used tutoring before?"
        self.fields["tutoring_reason"].label = "What led you to request a tutor?"
        self.fields["subject"].label = "Subject you would like support with?"
        self.fields["notes"].label = "What would you like help within in that subject?"
        self.fields["sms_notifications"].label = "I would like to be notified about my sessions (such as new and cancelled sessions) via text (SMS)"
        self.helper.layout = Layout(
            "full_name",
            "nickname",
            "phone_number",
            "availability",
            "ethnicity",
            "gender",
            "pronouns",
            "used_tutoring_before",
            "subject",
            "notes",
            "tutoring_reason",
            "sms_notifications",
            layout.Submit('submit', 'Submit', css_class='btn btn-primary my-2'),
        )

    def clean(self):
        errors = {}
        if "availability" in self.cleaned_data and len(self.cleaned_data["availability"]) < 3:
            errors["availability"] = "Please select at least 3 time slots"
        if errors:
            raise ValidationError(errors)


class TutorOnboardingForm(Form):
    full_name = django.forms.models.fields_for_model(Profile)["full_name"]
    full_name.required = True
    nickname = django.forms.models.fields_for_model(Profile)["nickname"]
    phone_number = PhoneNumberField()
    availability = ModelMultipleChoiceField(
        queryset=TimeSlot.objects.filter(time__gt=6),
        widget=ChosenSelectMultiple()
    )
    gender = ModelChoiceField(queryset=Gender.objects)
    ethnicity = ModelChoiceField(queryset=Ethnicity.objects)
    pronouns = ModelChoiceField(queryset=Pronouns.objects)

    offered_sectors = ModelMultipleChoiceField(
        queryset=Sector.objects.all(),
        widget=ChosenSelectMultiple()
    )
    offered_subjects = ModelMultipleChoiceField(
        queryset=Subject.objects.all(),
        widget=ChosenSelectMultiple()
    )
    site = ModelChoiceField(
        queryset=Site.objects.exclude(display="Not Specified"), required=False
    )
    site_location = ModelChoiceField(
        queryset=SiteLocation.objects.exclude(display="Not Specified"), required=False
    )
    tutee_contact = django.forms.models.fields_for_model(Profile)["tutee_contact"]
    sms_notifications = django.forms.models.fields_for_model(Profile)["sms_notifications"]
    training_code = CharField(required=False)

    monthly = BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.fields["availability"].widget.attrs["size"] = 10
        self.fields["availability"].label = (
            "What is your availability in Eastern time?"
        )
        self.fields['availability'].help_text = "Hold control or command to select multiple"
        self.fields["offered_sectors"].label = (
            "What sectors are you interested in tutoring?"
        )
        self.fields["offered_subjects"].label = (
            "What subjects are you interested in tutoring?"
        )
        self.fields["tutee_contact"].label = (
            "Describe to the student how they should contact you at your scheduled time"
        )
        self.fields["site"].label = (
            "Do you come from a partner program? If so, please specify:"
        )
        self.fields["monthly"].label = (
            "Would you like to schedule your offered hours for future months (monthly tutor)?"
        )
        self.fields["site_location"].label = (
            "Only answer if you selected a partner program in the previous question: If you are associated with a specific site location, please select it below (otherwise, leave blank)."
        )
        self.fields['tutee_contact'].widget.attrs['placeholder'] = 'Join meeting room at: https://...'
        self.fields["sms_notifications"].label = "I would like to be notified about my sessions (such as new and cancelled sessions) via text (SMS)"
        self.fields["training_code"].label = "If you have completed tutor training, enter code here (otherwise, leave blank)"
        self.fields["sms_notifications"].initial = True

        self.helper.layout = Layout(
            "full_name",
            "nickname",
            "phone_number",
            "availability",
            "ethnicity",
            "gender",
            "pronouns",
            "offered_sectors",
            "offered_subjects",
            "site",
            "site_location",
            "tutee_contact",
            "sms_notifications",
            "training_code",
            "monthly",
            HTML(f"""<div><a class="btn btn-sm btn-outline-primary mb-3" href="{reverse(
            "tutor:monthly-weekly-info")}" target="_blank">What are monthly/weekly tutors?</a></div>"""),
            layout.Submit("submit", "Submit", css_class="btn btn-primary my-2"),
        )

    def clean(self):
        errors = {}
        if "availability" in self.cleaned_data and len(self.cleaned_data["availability"]) < 3:
            errors["availability"] = "Please select at least 3 time slots"
        if self.cleaned_data["site_location"] and not self.cleaned_data["site"]:
            site = self.cleaned_data["site_location"].site.display
            errors["site"] = f"Please select {site} as your site"
        elif self.cleaned_data["site_location"]:
            if self.cleaned_data["site_location"].site != self.cleaned_data["site"]:
                errors["site_location"] = f"The site location you selected is not associated with the partner program you selected above"
        if errors:
            raise ValidationError(errors)


class TutorRequestForm(ModelForm):
    class Meta:
        model = TutorRequest
        exclude = ["user", "status", "timestamp", "meeting", "created_by"]

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["subject"].queryset = Subject.objects.filter(
            sector=user.profile.sector,
            offered=True,
        )
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            "subject",
            Field("notes", rows=2),
            layout.Submit("submit", "Submit", css_class="btn btn-primary my-2"),
        )

    def clean(self):
        errors = []
        new_request_not_allowed = self.user.profile.new_request_not_allowed(subject=self.cleaned_data['subject'])

        if new_request_not_allowed:
            errors.append(new_request_not_allowed)
            raise ValidationError(errors)


class TutorRequestUpdateForm(ModelForm):
    class Meta:
        model = TutorRequest
        exclude = ["user", "status", "timestamp", "meeting", "created_by"]

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["subject"].widget.attrs['readonly'] = True
        self.helper = FormHelper()
        self.helper.form_tag = False
        pk = self.instance.id
        meeting_html = ""
        if self.instance.meeting is None:
            meeting_html = f"""
            <div class="card my-2 border-primary text-primary">
              <div class='card-body'>
                <h4 class='card-title'>We are working on this request!</h4>
                <p class='card-text'>We will notify you when we have found a match.<br>Increase time availability in <a href=\"{{% url 'tutor:profile' %}}\">Settings</a> to be matched more quickly</p>
              </div>
            </div>
            """
        else:
            membership = MeetingMembership.objects.get(user=user, meeting=self.instance.meeting)
            button_html = ""
            card_title = "You have been scheduled!"

            if self.instance.meeting.happened():
                card_title =  "This meeting has happened"
                button_html = f"<a href='/meeting?id={self.instance.meeting.id}' class='btn btn-warning'>Click Here to Request a Repeat</a>"
            elif self.instance.meeting.happening():
                card_title =  "This meeting is occurring now"
                button_html = f"<a href='/meeting?id={self.instance.meeting.id}' class='btn btn-warning'>Click Here to View Details</a>"
            elif membership.status == "Pending Confirmation":
                card_title =  "You have been matched!"
                button_html = f"<a href='/meeting?id={self.instance.meeting.id}' class='btn btn-warning'>Click Here to View and Confirm</a>"
            elif membership.status == "Confirmed":
                card_title =  "This meeting has been confirmed"
                button_html = f"<a href='/meeting?id={self.instance.meeting.id}' class='btn btn-success'>Click Here to View Details</a>"
            meeting_html = f"""
            <div class="card my-2">
              <div class='card-body'>
                <h5 class='card-title'>{card_title}</h5>
                <p class='card-text'>{self.instance.meeting}</p>
                {button_html}
              </div>
            </div>
            """
        update_button = StrictButton(type="input", content="Update Request", name="update", value=f"update-{pk}", css_class="btn btn-primary")
        delete_button = StrictButton(type="input", content="Cancel Request", name="delete", value=f"delete-{pk}", css_class="btn btn-danger")
        self.helper.layout = Layout(
            "subject",
            Field("notes", rows=2),
            HTML(meeting_html),
            update_button,
            delete_button,
        )


class OrientationTrainingForm(ModelForm):
    class Meta:
        model = OrientationTraining
        exclude = ["user"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.render_required_fields = True
        self.fields["tutor_trainer"].queryset = Profile.objects.filter(
            account_type__display="Tutor-Trainer",
            orientation_trainer=True,
        )

        self.helper.layout = Layout(
            Field("tutor_role", rows=2),
            Field("instructor_does", rows=2),
            Field("tutor_does", rows=2),
            "tutor_trainer",
            "tutor_trainer_rating",
            Field("training_practical", rows=2),
            "overall_quality_rating",
            Field("suggestions", rows=2),
            layout.Submit("submit", "Submit", css_class="btn btn-primary my-2"),
        )


class TutorTrainingForm(ModelForm):
    class Meta:
        model = TutorTraining
        exclude = ["user"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.render_required_fields = True
        self.fields["tutor_trainer"].queryset = Profile.objects.filter(
            account_type__display="Tutor-Trainer",
            tutor_training_trainer=True,
        )
        
        self.helper.layout = Layout(
            "what_is_minimalism",
            "resources_for_control",
            "video_conference_applications",
            "facial_and_body_language",
            "speaking_and_language",
            "tutor_trainer",
            "tutor_trainer_rating",
            Field("training_practical", rows=2),
            "overall_quality_rating",
            Field("suggestions", rows=2),
            layout.Submit("submit", "Submit", css_class="btn btn-primary my-2"),
        )


class RoleplayTrainingForm(ModelForm):
    class Meta:
        model = RoleplayTraining
        exclude = ["user"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.render_required_fields = True
        self.fields["tutor_trainer"].queryset = Profile.objects.filter(
            account_type__display="Tutor-Trainer",
            roleplay_trainer=True,
        )
        self.helper.layout = Layout(
            "what_difficulties",
            "what_strategies",
            "what_could_you_have_done_better",
            "how_did_tutor_help",
            "what_did_you_learn",
            "how_can_tutor_improve",
            "tutor_trainer",
            "tutor_trainer_rating",
            Field("training_practical", rows=2),
            "overall_quality_rating",
            Field("suggestions", rows=2),
            layout.Submit("submit", "Submit", css_class="btn btn-primary my-2"),
        )


class UserLoginForm(AuthenticationForm):
    username = UsernameField()
    password = CharField(widget=PasswordInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_errors = False
        self.helper.layout = Layout(
            "username",
            "password",
            layout.Submit("submit", "Login", css_class="btn btn-primary my-2"),
        )

    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise ValidationError(
                _("This account is inactive. Please contact michael.gg.chin@gmail.com for more details"),
                code='inactive',
            )
            


class UserPasswordResetForm(PasswordResetForm):
    email = CharField(widget=forms.EmailInput())
    username = UsernameField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            "email",
            "username",
        layout.Submit("submit", "Request Reset Link", css_class="btn btn-primary my-2"),
        )
        
    def get_users(self, email):
        """
        Instead of getting all users in an email,
        just send the user that we want to reset password for.
        """
        data = self.cleaned_data['email']
        data2 = self.cleaned_data['username']
        associated_users = User.objects.filter(Q(email=data), Q(username=data2))
        return associated_users


class UserPasswordResetConfirmForm(SetPasswordForm):
    error_messages = {
        'password_mismatch': _("The two password fields didn't match."),
    }
    new_password1 = forms.CharField(label=_("New Password"),
                                    widget=forms.PasswordInput)
    new_password2 = forms.CharField(label=_("Confirm Password"),
                                    widget=forms.PasswordInput)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(SetPasswordForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
        "new_password1",
        "new_password2",
        layout.Submit("submit", "Change Password", css_class="btn btn-primary my-2"),
        )


class ConfirmMeetingForm(Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            layout.Submit(
                "confirm", "Confirm Meeting", css_class="btn btn-success my-2"
            ),
        )


class SpecificCancelMeetingForm(Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            layout.Submit("cancel", "Cancel Meeting Attendance", css_class="btn btn-danger my-2"),
        )


class RepeatMeetingForm(Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            layout.Submit("repeat", "Repeat Meeting", css_class="btn btn-success my-2"),
        )


class CreateInPersonMeetingForm(Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            layout.Submit(
                "submit", "Start In Person Meeting", css_class="btn btn-success my-2"
            ),
        )

class DirectoryForm(Form):
    selected_users = UserMultipleChoiceField(
        queryset= None,
        widget=ChosenSelectMultiple(),
        required=True,
    )

    subject = ModelChoiceField(queryset=Subject.objects.all())


    def __init__(self, *args, site_id=None, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        tutee_types = ["K-12-Tutee", "College-Tutee", "Adult-Tutee"]
        user_selected_queryset = User.objects.filter(
            profile__account_type__display__in=tutee_types,
            profile__onboarded=True,
            student_associate__tutor = user
        ).all()
    
        user_all_queryset = User.objects.filter(
            profile__account_type__display__in=tutee_types,
            profile__onboarded=True
        ).all()
    
        if site_id:
            if site_id == "-1":
                user_selected_queryset = user_selected_queryset.filter(profile__site__isnull=True)
                user_all_queryset = user_all_queryset.filter(profile__site__isnull=True)
            else:
                user_selected_queryset = user_selected_queryset.filter(profile__site__isnull=site_id)
                user_all_queryset = user_all_queryset.filter(profile__site__isnull=site_id)
        if user:
            self.fields['selected_users'].queryset = user_selected_queryset.all()
            self.fields['selected_users'].initial = user_selected_queryset.all()
        else:
            self.fields['selected_users'].queryset = user_all_queryset.all()
            self.fields['selected_users'].initial = user_all_queryset.all()
        self.helper = FormHelper()
        self.helper.layout = Layout(
            "selected_users",
            "subject",
            layout.Submit(
                "submit", "Start Meeting", css_class="btn btn-primary my-2"
            ),
        )

class LeaveTicketForm(ModelForm):
    
    check = forms.BooleanField(
        label='By checking this box, your account will be deactivated.',
        required=False)
    
    Choices=(
        ("This is temporary. I'll be back.", "This is temporary. I'll be back."),
        ('I have another account.', 'I have another account.'),
        ('My account was hacked.', 'My account was hacked.'),
        ("I don't find City Tutors useful.", "I don't find City Tutors useful."),
        ("I don't feel safe on City Tutors.", "I don't feel safe on City Tutors."),
        ('I have a privacy concern.', 'I have a privacy concern.'),
        ("Others", "Others")
        )

    leave_reason = forms.ChoiceField(
        choices=Choices,  
        widget=forms.RadioSelect(),
        label="",
        required=False
    )    

    leave_reason_others = forms.CharField(
        label="Please explain further (Max 200 Characters)",
        required = False, 
        widget=forms.Textarea(
            attrs={
                "style": "height:90px; resize:none;",
                "maxlength": '200',
                
            }
        )
    )

    return_date = DateField(
        label="If this is temporary, when are you planning to return?",
        widget=DateInput(
            attrs={
                "type": "date",
            }
        ),
        required=False 
    )

    confirm_sign = forms.CharField(
        label="Please enter your full name:",
        required = False,
        widget=forms.TextInput(
            attrs={
                "style": "width:200px; resize:none;",
                "maxlength": '200',
            }
        ),
    )

    class Meta:
        model = LeaveTicket
        fields = ['leave_reason', 'leave_reason_others', 'return_date']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()

        submit_button = StrictButton(type="input", content="Deactivate", name="submit", css_class="btn btn-danger")
        cancel_button = StrictButton(type="input", content="Cancel", name="cancel", css_class="btn btn-primary")
        self.helper.layout = Layout(
            Field("leave_reason"),
            Field("leave_reason_others"),
            Field("return_date"),
            Field("confirm_sign"),
            Field("check"),
            submit_button,
            cancel_button,

        )
        
class ExitTicketDifficultForm(ModelForm):
    class Meta:
        model = ExitTicketDifficult
        exclude = ["completed", "request", "tutor"]
        widgets = {
            "still_help": forms.RadioSelect(),
            "thank_letter_yesno": forms.RadioSelect(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        middle_choices_4 = [(x+1,str(x+1)) for x in range(1,3)]
        middle_choices_7 = [(x+1,str(x+1)) for x in range(1,6)]

        select_fields_7 = {
            "confidence": [(1, "1 - Not confident at all"), (7, "7 - Very confident")],
        }
        select_fields_4 = {
            "tutor_satisfaction": [(1, "1 - Not satisfied"), (4, "4 - Very satisfied")],
            "tutor_helpful": [(1, "1 - Not helpful"), (4, "4 - Very helpful")],
            "tutor_comfortable": [(1, "1 - Not comfortable/connected"), (4, "4 - Very comfortable/connected")]
        }

        for field_name, choices in select_fields_4.items():
            choices = [("", "----"), choices[0], *middle_choices_4, choices[1]]

            label = self.fields[field_name].label
            self.fields[field_name] = forms.ChoiceField(choices=choices)
            self.fields[field_name].label = label

        for field_name, choices in select_fields_7.items():
            choices = [("", "----"), choices[0], *middle_choices_7, choices[1]]

            label = self.fields[field_name].label
            self.fields[field_name] = forms.ChoiceField(choices=choices)
            self.fields[field_name].label = label

        text_fields = [
            "satisfaction_reason", "helpful_reason", "comfortable_reason",
            "help_concepts", "recommendations", "thank_letter", "additional_comments"
        ]

        for field_name in text_fields:
            self.fields[field_name].widget.attrs.update({
                'rows': '3',
            })

        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Submit'))

    def clean(self):
        errors = {}
        if int(self.cleaned_data["tutor_satisfaction"]) <= 2 and not self.cleaned_data["satisfaction_reason"]:
            errors["satisfaction_reason"] = "Please fill in this field."
        if int(self.cleaned_data["tutor_helpful"]) <= 2 and not self.cleaned_data["helpful_reason"]:
            errors["helpful_reason"] = "Please fill in this field."
        if int(self.cleaned_data["tutor_comfortable"]) <= 2 and not self.cleaned_data["comfortable_reason"]:
            errors["comfortable_reason"] = "Please fill in this field."
        if self.cleaned_data["still_help"] and not self.cleaned_data["help_concepts"]:
            errors["help_concepts"] = "Please fill in this field."
        if not self.cleaned_data["thank_letter_yesno"] and not self.cleaned_data["thank_letter"]:
            errors["thank_letter"] = "Please fill in this field."

        if errors:
            raise ValidationError(errors)


class ExitTicketMediumForm(ModelForm):
    class Meta:
        model = ExitTicketMedium
        exclude = ["completed", "request", "tutor"]
        widgets = {
            "like_tutor": forms.RadioSelect(),
            "be_open": forms.RadioSelect(),
            "tutor_help": forms.RadioSelect(),
            "better_understand": forms.RadioSelect(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Submit'))


class ExitTicketEasyForm(ModelForm):
    class Meta:
        model = ExitTicketEasy
        exclude = ["completed", "request", "tutor"]
        widgets = {
            "like_tutor": forms.RadioSelect(),
            "safe_mistakes": forms.RadioSelect(),
            "tutor_helps": forms.RadioSelect(),
            "understand_better": forms.RadioSelect(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Submit'))


class GradeLevelForm(ModelForm):
    class Meta:
        model = Profile
        fields = ["grade_level"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit('submit-grade', 'Submit'))


class TutorMatchConfirmForm(Form):
    confirm_subject = BooleanField(required=True, label="Your settings indicate that you don't regularly tutor this subject. Please confirm that you are able to tutor this subject.")
    confirm_sector = BooleanField(required=True, label="Your settings indicate that you don't regularly tutor this sector. Please confirm that you are able to tutor this sector.")
    confirm_timeslot = BooleanField(required=True, label="Your settings indicate that you aren't regularly available at this time. Please confirm that you are available to meet at this time.")

    def __init__(self, *args, **kwargs):
        tutor_matches_timeslot =  kwargs.pop("tutor_matches_timeslot", False)
        tutor_matches_subject =  kwargs.pop("tutor_matches_subject", False)
        tutor_matches_sector =  kwargs.pop("tutor_matches_sector", False)

        super().__init__(*args, **kwargs)
        
        if tutor_matches_timeslot:
            del self.fields["confirm_timeslot"]
        if tutor_matches_subject:
            del self.fields["confirm_subject"]
        if tutor_matches_sector:
            del self.fields["confirm_sector"]

        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Confirm'))


class SiteMeetingMembershipForm(ModelForm):
    status = forms.ChoiceField(choices=
        [
            ("Confirmed", "Confirmed"),
            ("Cancelled",  "Cancelled"),
            ("Pending Confirmation",  "Pending Confirmation"),
        ]
    )

    class Meta:
        model = MeetingMembership
        fields = ["status"]


class SiteTutorRequestEditForm(ModelForm):
    notes = CharField(required=True, widget=Textarea(attrs={"rows": 3}))

    class Meta:
        model = TutorRequest
        fields = ["notes"]


class SiteTutorRequestForm(ModelForm):
    notes = CharField(required=True, widget=Textarea(attrs={"rows": 4}))

    class Meta:
        model = TutorRequest
        fields = ["notes", "subject"]

    def __init__(self, *args, user, site, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            "subject",
            "notes",
            layout.Submit(
                "submit",
                "Submit",
                css_class="btn btn-primary my-2",
            ),
        )
        self.site = site
        self.user = user
        self.fields["subject"].queryset = Subject.objects.filter(
            sector=user.profile.sector,
            offered=True,
        )
        self.fields["notes"].label = "What would the student like to get help with within in that subject?"

    def clean(self):
        errors = []

        if self.site.num_remaining_pooled_hours <= 0:
            errors.append(f"{self.site.display} is only allowed up to {self.site.tier.max_pooled_hours} pooled hours")
        
        tutee_request_limit = self.user.profile.new_request_not_allowed(subject=self.cleaned_data['subject'])

        if tutee_request_limit:
            errors.append(tutee_request_limit)
        
        if errors:
            raise ValidationError(errors)


class TutorMonthlyHoursForm(ModelForm):
    class Meta:
        model = TutorOfferedMonthlyHours
        exclude = ["user"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.add_input(Submit('submit_monthly', 'Submit', css_class='btn-primary my-2'))

        today = timezone.now()

        for field_name in list(self.fields):
            if field_name[:2] == "m_":
                month_number = int(field_name.split("_")[1])
                year = int(field_name.split("_")[2])
                if 2000 + year < today.year: # last year or earlier
                    self.fields.pop(field_name)
                elif 2000 + year == today.year and (month_number <= today.month or month_number > today.month + 3):
                    self.fields.pop(field_name)
                elif 2000 + year > today.year and month_number + 12*(2000+year-today.year) > today.month + 3:
                    self.fields.pop(field_name)
                else:
                    self.fields[field_name].label = f"{month_name[month_number]} 20{year}"


class TutorWeeklyHoursForm(ModelForm):
    class Meta:
        model = Profile
        fields = ["offered_hours"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.fields["offered_hours"].help_text = "You will be able to change this later"
        self.helper.add_input(Submit('submit_weekly', 'Submit', css_class='btn-primary my-2'))


def TutorCurrentMonthlyHours(request, instance, field_name, *args, **kwargs):
    class TutorCurrentMonthlyHoursForm(ModelForm):
        class Meta:
            model = TutorOfferedMonthlyHours
            fields = [field_name]

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.helper = FormHelper()
            self.helper.add_input(Submit('submit_current_monthly', 'Submit', css_class='btn-primary my-2'))
            self.fields[field_name].label = f"Current month ({ timezone.now().strftime('%B %Y') })"

    return TutorCurrentMonthlyHoursForm(request, instance=instance)


class TutorHoursTypeForm(ModelForm):
    class Meta:
        model = Profile
        fields = ["tutor_monthly_volunteer"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.add_input(Submit('submit_type', 'Submit', css_class='btn-primary mb-2'))
        self.fields["tutor_monthly_volunteer"].label = "I am a monthly volunteer"

class Orientation1Form(ModelForm):
    
    question1 = forms.ChoiceField(  
        widget=forms.RadioSelect(),
        choices = Orientation1.CHOICES1,
        label="1. When do you schedule the Live Training Session?",
        required=True
    )

    question2 = forms.ChoiceField(
        widget=forms.RadioSelect(),
        choices = Orientation1.CHOICES2,
        label="2. What do you need to fulfill the background check?",
        required=True
    )

    class Meta:
        model = Orientation1
        fields = ['question1', 'question2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("question1"),
            Field("question2"),
        )

class Orientation2Form(ModelForm):
    
    question1 = forms.ChoiceField(  
        widget=forms.RadioSelect(),
        choices = Orientation2.CHOICES1,
        label="1. What are the two fundamental challenges that historically underserved communities face?",
        required=True
    )

    question2 = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(),
        choices = Orientation2.CHOICES2,
        label="2. What makes The City Tutors a learning center? (Check all that apply)",
        required=True
    )

    class Meta:
        model = Orientation2
        fields = ['question1', 'question2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("question1"),
            Field("question2"),
        )

class Orientation3Form(ModelForm):
    
    question1 = forms.MultipleChoiceField(  
        widget=forms.CheckboxSelectMultiple(),
        choices = Orientation3.CHOICES1,
        label="1. Scenario: You've put in your availability into the web-app for tutoring. However, next week you will be unavailable to tutor, and the system has already connected a student to you. What do you do? (Check all that apply)",
        required=True
    )

    question2 = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(),
        choices = Orientation3.CHOICES2,
        label="2. Scenario: While registering for tutoring on the tutor portal, you indicated that you can offer tutoring services for Math only. But after a few sessions, the student you are tutoring requests you also offer tutoring support in Biology.  You don’t feel confident about helping out with Biology. What do you do? (Check all that apply)",
        required=True
    )

    class Meta:
        model = Orientation3
        fields = ['question1', 'question2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("question1"),
            Field("question2"),
        )

class Orientation4Form(ModelForm):
    
    question1 = forms.MultipleChoiceField(  
        widget=forms.CheckboxSelectMultiple(),
        choices = Orientation4.CHOICES1,
        label="1. Scenario: You have been meeting your tutee one-on-one virtually, regularly once a week for over four weeks now. However, due to an upcoming important personal event, you will have to miss the next session. What steps will you take? (Check all that apply)",
        required=True
    )

    question2 = forms.ChoiceField(
        widget=forms.RadioSelect(),
        choices = Orientation4.CHOICES2,
        label="2. Scenario: You signed up for conducting group tutoring sessions and you have been assigned to tutor a group of three, 8th-grade tutees who all attend the same high school. After a few sessions, one of the tutees in the group reaches out to you personally and informs you that he/she has failed the math test in school. How should you handle this situation? (Check all that apply)",
        required=True
    )

    class Meta:
        model = Orientation4
        fields = ['question1', 'question2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("question1"),
            Field("question2"),
        )

class Orientation5Form(ModelForm):
    
    question1 = forms.MultipleChoiceField(  
        widget=forms.CheckboxSelectMultiple(),
        choices = Orientation5.CHOICES1,
        label="1. As a tutor, what would your responsibilities towards your tutees be? (Check all that apply)",
        required=True
    )

    question2 = forms.ChoiceField(
        widget=forms.RadioSelect(),
        choices = Orientation5.CHOICES2,
        label="2. Scenario: A tutee sends you an email mentioning that he/she is having difficulty with a math assignment that is due tomorrow for his/her class in school. He/she asks you if you can complete the math assignment for them and send it to them so that they can submit it by the assignment deadline. How do you respond?",
        required=True
    )

    class Meta:
        model = Orientation5
        fields = ['question1', 'question2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("question1"),
            Field("question2"),
        )

class Orientation6Form(ModelForm):
    
    question1 = forms.MultipleChoiceField(  
        widget=forms.CheckboxSelectMultiple(),
        choices = Orientation6.CHOICES1,
        label="1. Scenario: One of your tutees is having difficulty understanding one of the concepts in their assignment. You have tried to verbally explain it to the tutee multiple times, but when you ask the tutee questions about the same, you can tell that the tutee is still unable to fully understand the concepts. What do you do? (Check all that apply)",
        required=True
    )

    question2 = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(),
        choices = Orientation6.CHOICES2,
        label="2. Scenario: You had a few sessions with a tutee reinforcing concepts that they didn’t understand in class. The following week, the tutee got a D on the assignment related to those concepts. What should you do in your next session? (Check all that apply)",
        required=True
    )

    class Meta:
        model = Orientation6
        fields = ['question1', 'question2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("question1"),
            Field("question2"),
        )

class Orientation7Form(ModelForm):
    
    question1 = forms.MultipleChoiceField(  
        widget=forms.CheckboxSelectMultiple(),
        choices = Orientation7.CHOICES1,
        label="1. What do you need for an online session? (check all that apply)",
        required=True
    )

    question2 = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(),
        choices = Orientation7.CHOICES2,
        label="2. Scenario: You have started an online video session with your tutee, but they have joined on their phone. While they can send you pictures of what their assignment is, they can’t show any work that they have been doing on the assignment. What should we do? (Check all that apply)",
        required=True
    )

    class Meta:
        model = Orientation7
        fields = ['question1', 'question2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("question1"),
            Field("question2"),
        )

class Orientation8Form(ModelForm):
    
    question1 = forms.MultipleChoiceField(  
        widget=forms.CheckboxSelectMultiple(),
        choices = Orientation8.CHOICES1,
        label="1. When the online system connects you to a tutee, what should you do before your first session with them?(check all that apply)",
        required=True
    )

    question2 = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(),
        choices = Orientation8.CHOICES2,
        label="2. What do you do when the student joins the meeting? (Check all that apply)",
        required=True
    )

    class Meta:
        model = Orientation8
        fields = ['question1', 'question2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("question1"),
            Field("question2"),
        )

class Orientation9Form(ModelForm):
    
    question1 = forms.MultipleChoiceField(  
        widget=forms.CheckboxSelectMultiple(),
        choices = Orientation9.CHOICES1,
        label="1. Which of these scenarios shows appropriate tutor body language and positioning? (check all that apply)",
        required=True
    )

    question2 = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(),
        choices = Orientation9.CHOICES2,
        label="2. Which of these scenarios shows appropriate tutor communication with the student? (Check all that apply)",
        required=True
    )

    class Meta:
        model = Orientation9
        fields = ['question1', 'question2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("question1"),
            Field("question2"),
        )

class Orientation10Form(ModelForm):
    
    question1 = forms.MultipleChoiceField(  
        widget=forms.CheckboxSelectMultiple(),
        choices = Orientation10.CHOICES1,
        label="1. You have 5-10 minutes left of the session. What do we do towards the end of the session? (check all that apply)",
        required=True
    )

    question2 = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(),
        choices = Orientation10.CHOICES2,
        label="2. The student has told you that this will be their last session with you. What should you do before they leave? (Check all that apply)",
        required=True
    )

    class Meta:
        model = Orientation10
        fields = ['question1', 'question2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("question1"),
            Field("question2"),
        )

class Orientation11Form(ModelForm):
    
    question1 = forms.MultipleChoiceField(  
        widget=forms.CheckboxSelectMultiple(),
        choices = Orientation11.CHOICES1,
        label="1. Describe how minimalism is used in helping a student solve a problem (check all that apply)",
        required=True
    )

    question2 = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(),
        choices = Orientation11.CHOICES2,
        label="2. How can the tutor help the student if they say they don't understand a concept? (Check all that apply)",
        required=True
    )

    class Meta:
        model = Orientation11
        fields = ['question1', 'question2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("question1"),
            Field("question2"),
        )

class Orientation1ResultForm(ModelForm):
    
    question1 = forms.ChoiceField(  
        widget=forms.RadioSelect(),
        choices = Orientation1.CHOICES1,
        label="1. When do you schedule the Live Training Session?",
        required=True
    )

    question2 = forms.ChoiceField(
        widget=forms.RadioSelect(),
        choices = Orientation1.CHOICES2,
        label="2. What do you need to fulfill the background check?",
        required=True
    )

    class Meta:
        model = Orientation1
        fields = ['question1', 'question2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.fields['question1'].widget.attrs['disabled'] = True
        self.fields['question2'].widget.attrs['disabled'] = True
        self.helper.layout = Layout(
            Field("question1"),
            Field("question2"),
        )

class Orientation2ResultForm(ModelForm):
    
    question1 = forms.ChoiceField(  
        widget=forms.RadioSelect(),
        choices = Orientation2.CHOICES1,
        label="1. What are the two fundamental challenges that historically underserved communities face?",
        required=True
    )

    question2 = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(),
        choices = Orientation2.CHOICES2,
        label="2. What makes The City Tutors a learning center?",
        required=True
    )

    class Meta:
        model = Orientation2
        fields = ['question1', 'question2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.fields['question1'].widget.attrs['disabled'] = True
        self.fields['question2'].widget.attrs['disabled'] = True
        self.helper.layout = Layout(
            Field("question1"),
            Field("question2"),
        )

class Orientation3ResultForm(ModelForm):
    
    question1 = forms.MultipleChoiceField(  
        widget=forms.CheckboxSelectMultiple(),
        choices = Orientation3.CHOICES1,
        label="1. Scenario: You've put in your availability into the web-app for tutoring. However, next week you will be unavailable to tutor, and the system has already connected a student to you. What do you do? (Check all that apply)",
        required=True
    )

    question2 = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(),
        choices = Orientation3.CHOICES2,
        label="2. Scenario: While registering for tutoring on the tutor portal, you indicated that you can offer tutoring services for Math only. But after a few sessions, the student you are tutoring requests you also offer tutoring support in Biology.  You don’t feel confident about helping out with Biology. What do you do? (Check all that apply)",
        required=True
    )

    class Meta:
        model = Orientation3
        fields = ['question1', 'question2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.fields['question1'].widget.attrs['disabled'] = True
        self.fields['question2'].widget.attrs['disabled'] = True
        self.helper.layout = Layout(
            Field("question1"),
            Field("question2"),
        )

class Orientation4ResultForm(ModelForm):
    
    question1 = forms.MultipleChoiceField(  
        widget=forms.CheckboxSelectMultiple(),
        choices = Orientation4.CHOICES1,
        label="1. Scenario: You have been meeting your tutee one-on-one virtually, regularly once a week for over four weeks now. However, due to an upcoming important personal event, you will have to miss the next session. What steps will you take? (Check all that apply)",
        required=True
    )

    question2 = forms.ChoiceField(
        widget=forms.RadioSelect(),
        choices = Orientation4.CHOICES2,
        label="2. Scenario: You signed up for conducting group tutoring sessions and you have been assigned to tutor a group of three, 8th-grade tutees who all attend the same high school. After a few sessions, one of the tutees in the group reaches out to you personally and informs you that he/she has failed the math test in school. How should you handle this situation? (Check all that apply)",
        required=True
    )

    class Meta:
        model = Orientation4
        fields = ['question1', 'question2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.fields['question1'].widget.attrs['disabled'] = True
        self.fields['question2'].widget.attrs['disabled'] = True
        self.helper.layout = Layout(
            Field("question1"),
            Field("question2"),
        )

class Orientation5ResultForm(ModelForm):
    
    question1 = forms.MultipleChoiceField(  
        widget=forms.CheckboxSelectMultiple(),
        choices = Orientation5.CHOICES1,
        label="1. As a tutor, what would your responsibilities towards your tutees be? (Check all that apply)",
        required=True
    )

    question2 = forms.ChoiceField(
        widget=forms.RadioSelect(),
        choices = Orientation5.CHOICES2,
        label="2. Scenario: A tutee sends you an email mentioning that he/she is having difficulty with a math assignment that is due tomorrow for his/her class in school. He/she asks you if you can complete the math assignment for them and send it to them so that they can submit it by the assignment deadline. How do you respond?",
        required=True
    )

    class Meta:
        model = Orientation5
        fields = ['question1', 'question2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.fields['question1'].widget.attrs['disabled'] = True
        self.fields['question2'].widget.attrs['disabled'] = True
        self.helper.layout = Layout(
            Field("question1"),
            Field("question2"),
        )

class Orientation6ResultForm(ModelForm):
    
    question1 = forms.MultipleChoiceField(  
        widget=forms.CheckboxSelectMultiple(),
        choices = Orientation6.CHOICES1,
        label="1. Scenario: One of your tutees is having difficulty understanding one of the concepts in their assignment. You have tried to verbally explain it to the tutee multiple times, but when you ask the tutee questions about the same, you can tell that the tutee is still unable to fully understand the concepts. What do you do? (Check all that apply)",
        required=True
    )

    question2 = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(),
        choices = Orientation6.CHOICES2,
        label="2. Scenario: You had a few sessions with a tutee reinforcing concepts that they didn’t understand in class. The following week, the tutee got a D on the assignment related to those concepts. What should you do in your next session? (Check all that apply)",
        required=True
    )

    class Meta:
        model = Orientation6
        fields = ['question1', 'question2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.fields['question1'].widget.attrs['disabled'] = True
        self.fields['question2'].widget.attrs['disabled'] = True
        self.helper.layout = Layout(
            Field("question1"),
            Field("question2"),
        )

class Orientation7ResultForm(ModelForm):
    
    question1 = forms.MultipleChoiceField(  
        widget=forms.CheckboxSelectMultiple(),
        choices = Orientation7.CHOICES1,
        label="1. What do you need for an online session? (check all that apply)",
        required=True
    )

    question2 = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(),
        choices = Orientation7.CHOICES2,
        label="2. Scenario: You have started an online video session with your tutee, but they have joined on their phone. While they can send you pictures of what their assignment is, they can’t show any work that they have been doing on the assignment. What should we do? (Check all that apply)",
        required=True
    )

    class Meta:
        model = Orientation7
        fields = ['question1', 'question2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.fields['question1'].widget.attrs['disabled'] = True
        self.fields['question2'].widget.attrs['disabled'] = True
        self.helper.layout = Layout(
            Field("question1"),
            Field("question2"),
        )

class Orientation8ResultForm(ModelForm):
    
    question1 = forms.MultipleChoiceField(  
        widget=forms.CheckboxSelectMultiple(),
        choices = Orientation8.CHOICES1,
        label="1. When the online system connects you to a tutee, what should you do before your first session with them?(check all that apply)",
        required=True
    )

    question2 = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(),
        choices = Orientation8.CHOICES2,
        label="2. What do you do when the student joins the meeting? (Check all that apply)",
        required=True
    )

    class Meta:
        model = Orientation8
        fields = ['question1', 'question2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.fields['question1'].widget.attrs['disabled'] = True
        self.fields['question2'].widget.attrs['disabled'] = True
        self.helper.layout = Layout(
            Field("question1"),
            Field("question2"),
        )

class Orientation9ResultForm(ModelForm):
    
    question1 = forms.MultipleChoiceField(  
        widget=forms.CheckboxSelectMultiple(),
        choices = Orientation9.CHOICES1,
        label="1. Which of these scenarios shows appropriate tutor body language and positioning? (check all that apply)",
        required=True
    )

    question2 = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(),
        choices = Orientation9.CHOICES2,
        label="2. Which of these scenarios shows appropriate tutor communication with the student? (Check all that apply)",
        required=True
    )

    class Meta:
        model = Orientation9
        fields = ['question1', 'question2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.fields['question1'].widget.attrs['disabled'] = True
        self.fields['question2'].widget.attrs['disabled'] = True
        self.helper.layout = Layout(
            Field("question1"),
            Field("question2"),
        )

class Orientation10ResultForm(ModelForm):
    
    question1 = forms.MultipleChoiceField(  
        widget=forms.CheckboxSelectMultiple(),
        choices = Orientation10.CHOICES1,
        label="1. You have 5-10 minutes left of the session. What do we do towards the end of the session? (check all that apply)",
        required=True
    )

    question2 = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(),
        choices = Orientation10.CHOICES2,
        label="2. The student has told you that this will be their last session with you. What should you do before they leave? (Check all that apply)",
        required=True
    )

    class Meta:
        model = Orientation10
        fields = ['question1', 'question2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.fields['question1'].widget.attrs['disabled'] = True
        self.fields['question2'].widget.attrs['disabled'] = True
        self.helper.layout = Layout(
            Field("question1"),
            Field("question2"),
        )

class Orientation11ResultForm(ModelForm):
    
    question1 = forms.MultipleChoiceField(  
        widget=forms.CheckboxSelectMultiple(),
        choices = Orientation11.CHOICES1,
        label="1. Describe how minimalism is used in helping a student solve a problem (check all that apply)",
        required=True
    )

    question2 = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(),
        choices = Orientation11.CHOICES2,
        label="2. How can the tutor help the student if they say they don't understand a concept? (Check all that apply)",
        required=True
    )

    class Meta:
        model = Orientation11
        fields = ['question1', 'question2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.fields['question1'].widget.attrs['disabled'] = True
        self.fields['question2'].widget.attrs['disabled'] = True
        self.helper.layout = Layout(
            Field("question1"),
            Field("question2"),
        )

class OrientationLiveSession(ModelForm):
    class Meta:
        model = LiveSession
        exclude = ["user"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.fields["trainer"].queryset = Profile.objects.filter(
            tutor_training_trainer=True,
        )
        submit_button = StrictButton(id="id_submit", type="input", content="Submit", name="Submit", css_class="btn btn-primary")
        self.fields["trainer"].label = "3. Choose the trainer you are currently having live training with:"
        self.fields["q1"].label = (
            "What do you see as the role of the tutor? How do you see yourself as a tutor? <span style='color:red'>*</span>"
        )
        self.fields["q2"].label = (
            "Recall the module: Ethics and Professionalism. Identify 3-4 characteristics, elements, or key points you took from that module <span style='color:red'>*</span>"
        )
        self.fields["q3"].label = (
            "Explain how this topic impacts your practice as a tutor. <span style='color:red'>*</span>"
        )
        self.fields["q4"].label = (
            "What did you work on? What difficulties were you experiencing in the session, and how would you rate the student’s ability to complete the assignment on their own? <span style='color:red'>*</span>"
        )
        self.fields["q5"].label = (
            "What strategies did you use to keep the session on track? <span style='color:red'>*</span>"
        )
        self.fields["q6"].label = (
            "What could you have done better? <span style='color:red'>*</span>"
        )
        self.fields["q7"].label = (
            "What was easy? What went well? <span style='color:red'>*</span>"
        )
        self.fields["q8"].label = (
            "What was difficult? What could be improved? <span style='color:red'>*</span>"
        )
        self.fields["q9"].label = (
            "Where would you like more support? What kind of support would you like to receive? <span style='color:red'>*</span>"
        )
        self.helper.layout = Layout(
            Field("q1", rows=4, required=True),
            Field("q2", rows=4, required=True),
            Field("q3", rows=4, required=True),
            Field("q4", rows=4, required=True),
            Field("q5", rows=4, required=True),
            Field("q6", rows=4, required=True),
            Field("q7", rows=4, required=True),
            Field("q8", rows=4, required=True),
            Field("q9", rows=4, required=True),
            submit_button
        )
