from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """Custom User model with phone number"""
    phone_number = models.CharField(max_length=20, verbose_name=_("Phone Number"))
    full_name = models.CharField(max_length=255, verbose_name=_("Full Name"))

    def __str__(self):
        return f"{self.full_name} ({self.username})"

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")


class Booking(models.Model):
    """Mock test booking model"""
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('accepted', _('Accepted')),
        ('rejected', _('Rejected')),
        ('completed', _('Completed')),
    ]

    WEEKDAY_CHOICES = [
        (0, _('Monday')),
        (1, _('Tuesday')),
        (2, _('Wednesday')),
        (3, _('Thursday')),
        (4, _('Friday')),
        (5, _('Saturday')),
        (6, _('Sunday')),
    ]

    TIME_SLOTS = {
        'weekday': ['10:00', '14:00'],  # Monday-Saturday
        'sunday': ['09:00', '13:00', '16:00'],  # Sunday
    }

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings', verbose_name=_("User"))
    test_date = models.DateField(verbose_name=_("Test Date"))
    test_time = models.TimeField(verbose_name=_("Test Time"))
    payment_screenshot = models.ImageField(upload_to='payment_screenshots/', verbose_name=_("Payment Screenshot"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name=_("Status"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
    admin_notes = models.TextField(blank=True, null=True, verbose_name=_("Admin Notes"))

    class Meta:
        verbose_name = _("Booking")
        verbose_name_plural = _("Bookings")
        ordering = ['-test_date', '-test_time']
        unique_together = ['user', 'test_date', 'test_time']

    def __str__(self):
        return f"{self.user.full_name} - {self.test_date} at {self.test_time}"

    @classmethod
    def get_available_slots_count(cls, test_date, test_time):
        """Get number of available slots for a specific date and time"""
        booked_count = cls.objects.filter(
            test_date=test_date,
            test_time=test_time,
            status__in=['pending', 'accepted']
        ).count()
        return 6 - booked_count

    @classmethod
    def is_slot_available(cls, test_date, test_time):
        """Check if a slot is available"""
        return cls.get_available_slots_count(test_date, test_time) > 0

    def save(self, *args, **kwargs):
        """Override save to validate slot availability"""
        if not self.pk:  # Only check for new bookings
            if not self.is_slot_available(self.test_date, self.test_time):
                raise ValueError(_("This time slot is fully booked"))
        super().save(*args, **kwargs)


class Result(models.Model):
    """Test results model"""
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='result', verbose_name=_("Booking"))

    # Listening with raw score
    listening = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(9)],
        verbose_name=_("Listening Band")
    )
    listening_correct = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(40)],
        verbose_name=_("Listening Correct Answers"),
        help_text=_("Number of correct answers out of 40")
    )

    # Reading with raw score
    reading = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(9)],
        verbose_name=_("Reading Band")
    )
    reading_correct = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(40)],
        verbose_name=_("Reading Correct Answers"),
        help_text=_("Number of correct answers out of 40")
    )

    # Writing split into Task 1 and Task 2
    writing_task1 = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(9)],
        verbose_name=_("Writing Task 1"),
        help_text=_("Writing Task 1 band score")
    )
    writing_task2 = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(9)],
        verbose_name=_("Writing Task 2"),
        help_text=_("Writing Task 2 band score")
    )
    writing = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(9)],
        verbose_name=_("Writing Overall"),
        help_text=_("Calculated from Task 1 and Task 2")
    )

    # Speaking
    speaking = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(9)],
        verbose_name=_("Speaking")
    )

    # Overall
    overall = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(9)],
        verbose_name=_("Overall")
    )

    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Uploaded At"))

    class Meta:
        verbose_name = _("Result")
        verbose_name_plural = _("Results")
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Result for {self.booking.user.full_name} - Overall: {self.overall}"

    def save(self, *args, **kwargs):
        """Auto-calculate writing and overall scores with IELTS rounding rules"""
        # Calculate Writing overall from Task 1 and Task 2
        # Formula: (Task1 + Task2 * 2) / 3
        if self.writing_task1 is not None and self.writing_task2 is not None:
            writing_raw = (float(self.writing_task1) + float(self.writing_task2) * 2) / 3
            self.writing = self._apply_ielts_rounding(writing_raw)

        # Calculate Overall from all four skills
        if self.listening is not None and self.reading is not None and self.writing is not None and self.speaking is not None:
            total = float(self.listening) + float(self.reading) + float(self.writing) + float(self.speaking)
            average = total / 4
            self.overall = self._apply_ielts_rounding(average)

        super().save(*args, **kwargs)

    def _apply_ielts_rounding(self, score):
        """Apply IELTS rounding rules to a score"""
        # IELTS rounding rules:
        # .25 rounds down to .0
        # .75 rounds up to next .0
        # Anything else rounds to nearest .5
        decimal_part = score - int(score)

        if decimal_part < 0.25:
            return int(score)
        elif decimal_part < 0.75:
            return int(score) + 0.5
        else:
            return int(score) + 1.0


class Feedback(models.Model):
    """User feedback model"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feedbacks', verbose_name=_("User"))
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='feedbacks', verbose_name=_("Booking"))
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name=_("Rating")
    )
    comment = models.TextField(verbose_name=_("Comment"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    class Meta:
        verbose_name = _("Feedback")
        verbose_name_plural = _("Feedbacks")
        ordering = ['-created_at']

    def __str__(self):
        return f"Feedback by {self.user.full_name} - {self.rating} stars"