from .models import Booking


def pending_answers_count(request):
    """Inject count of completed bookings with no result uploaded into every template."""
    if request.user.is_authenticated and request.user.is_staff:
        count = Booking.objects.filter(status='completed', result__isnull=True).count()
    else:
        count = 0
    return {'pending_answers_count': count}
