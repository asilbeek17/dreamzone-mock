from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from .models import User, Booking, Feedback, Result
from datetime import datetime


class UserRegistrationForm(UserCreationForm):
    """User registration form"""
    full_name = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Full Name')
        })
    )
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Username')
        })
    )
    phone_number = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Phone Number')
        })
    )
    password1 = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Password')
        })
    )
    password2 = forms.CharField(
        label=_("Confirm Password"),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Confirm Password')
        })
    )

    class Meta:
        model = User
        fields = ['full_name', 'username', 'phone_number', 'password1', 'password2']


class UserLoginForm(AuthenticationForm):
    """User login form"""
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Username')
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Password')
        })
    )


class BookingForm(forms.ModelForm):
    """Booking form for mock tests"""
    test_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'min': timezone.localtime(timezone.now()).strftime('%Y-%m-%d')
        }),
        label=_("Test Date")
    )
    test_time = forms.CharField(
        max_length=5,
        widget=forms.TextInput(attrs={
            'class': 'form-control'
        }),
        label=_("Test Time")
    )
    payment_screenshot = forms.ImageField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        }),
        label=_("Payment Screenshot")
    )

    class Meta:
        model = Booking
        fields = ['test_date', 'test_time', 'payment_screenshot']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_test_time(self):
        """Validate test_time format"""
        test_time = self.cleaned_data.get('test_time')
        if test_time:
            try:
                datetime.strptime(test_time, '%H:%M').time()
                return test_time
            except ValueError:
                raise forms.ValidationError(_("Invalid time format. Please select a valid time."))
        return test_time

    def clean(self):
        cleaned_data = super().clean()
        test_date = cleaned_data.get('test_date')
        test_time = cleaned_data.get('test_time')

        if test_date and test_time:
            try:
                time_obj = datetime.strptime(test_time, '%H:%M').time()
                now_local = timezone.localtime(timezone.now())
                now_naive = now_local.replace(tzinfo=None)
                today = now_naive.date()

                # Reject past dates
                if test_date < today:
                    raise forms.ValidationError(_("Cannot book a test in the past."))

                # If booking for today, reject already-passed time slots
                if test_date == today:
                    slot_dt = datetime.combine(test_date, time_obj)
                    if slot_dt <= now_naive:
                        raise forms.ValidationError(_("This time slot has already passed today."))

                # Check slot availability
                if not Booking.is_slot_available(test_date, time_obj):
                    raise forms.ValidationError(_("This time slot is fully booked. Please select another time."))

                # Prevent the same user from booking the same date AND same time twice
                if self.user:
                    already_booked = Booking.objects.filter(
                        user=self.user,
                        test_date=test_date,
                        test_time=time_obj,
                        status__in=['pending', 'accepted']
                    ).exists()
                    if already_booked:
                        raise forms.ValidationError(_("You already have an active booking at this time on this date."))

            except ValueError:
                raise forms.ValidationError(_("Invalid time format"))

        return cleaned_data


class FeedbackForm(forms.ModelForm):
    """Feedback form"""
    rating = forms.IntegerField(
        min_value=1,
        max_value=5,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'max': '5'
        }),
        label=_("Rating (1-5)")
    )
    comment = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': _('Write your feedback here...')
        }),
        label=_("Comment")
    )

    class Meta:
        model = Feedback
        fields = ['rating', 'comment']


class ResultForm(forms.ModelForm):
    """Admin form for uploading results"""

    class Meta:
        model = Result
        fields = ['listening', 'listening_correct', 'reading', 'reading_correct',
                  'writing_task1', 'writing_task2', 'speaking']
        widgets = {
            'listening': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.5',
                'min': '0',
                'max': '9',
                'placeholder': 'Band score (e.g., 7.5)'
            }),
            'listening_correct': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '40',
                'placeholder': 'Correct answers (0-40)'
            }),
            'reading': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.5',
                'min': '0',
                'max': '9',
                'placeholder': 'Band score (e.g., 7.0)'
            }),
            'reading_correct': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '40',
                'placeholder': 'Correct answers (0-40)'
            }),
            'writing_task1': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.5',
                'min': '0',
                'max': '9',
                'placeholder': 'Task 1 band (e.g., 6.0)'
            }),
            'writing_task2': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.5',
                'min': '0',
                'max': '9',
                'placeholder': 'Task 2 band (e.g., 6.5)'
            }),
            'speaking': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.5',
                'min': '0',
                'max': '9',
                'placeholder': 'Band score (e.g., 7.0)'
            }),
        }