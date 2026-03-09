from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils.translation import gettext as _
from django.http import JsonResponse
from django.db.models import Q
from datetime import datetime, timedelta
from collections import defaultdict
from django.utils import timezone
from .models import User, Booking, Result, Feedback
from .forms import UserRegistrationForm, UserLoginForm, BookingForm, FeedbackForm, ResultForm


def is_admin(user):
    """Check if user is admin"""
    return user.is_staff or user.is_superuser


def auto_complete_expired_bookings():
    """
    Mark accepted bookings as completed when 3 hours have passed since the test time.
    Uses a cutoff = now - 3h so comparisons work correctly even across midnight.
    """
    from datetime import timedelta
    now_local = timezone.localtime(timezone.now())
    cutoff = now_local - timedelta(hours=3)
    cutoff_date = cutoff.date()
    cutoff_time = cutoff.time()

    expired = Booking.objects.filter(status='accepted').filter(
        Q(test_date__lt=cutoff_date) |
        Q(test_date=cutoff_date, test_time__lte=cutoff_time)
    )
    return expired.update(status='completed')


def register_view(request):
    """User registration view"""
    if request.user.is_authenticated:
        return redirect('dashboard')


    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, _('Registration successful! Welcome to CDI Mock System.'))
            return redirect('dashboard')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'register.html', {'form': form})


def login_view(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, _('Login successful!'))
                return redirect('dashboard')
    else:
        form = UserLoginForm()
    
    return render(request, 'login.html', {'form': form})


def logout_view(request):
    """User logout view"""
    logout(request)
    messages.success(request, _('Logged out successfully!'))
    return redirect('login')


@login_required
def dashboard_view(request):
    """User dashboard view"""
    if request.user.is_staff:
        return redirect('admin_dashboard')

    auto_complete_expired_bookings()

    now_local = timezone.localtime(timezone.now())
    today = now_local.date()
    current_time = now_local.time()

    # Upcoming: datetime is strictly in the future
    upcoming_bookings = Booking.objects.filter(user=request.user).filter(
        Q(test_date__gt=today) |
        Q(test_date=today, test_time__gt=current_time)
    ).order_by('test_date', 'test_time')

    # Q object for bookings whose scheduled time has already passed
    past_datetime_q = Q(test_date__lt=today) | Q(test_date=today, test_time__lte=current_time)

    # IDs of bookings that already have a result posted
    result_booking_ids = Result.objects.filter(
        booking__user=request.user
    ).values_list('booking_id', flat=True)

    # Waiting for results: time has passed, no result yet, not rejected
    waiting_bookings = Booking.objects.filter(user=request.user).filter(
        past_datetime_q
    ).exclude(id__in=result_booking_ids).exclude(status='rejected').order_by('-test_date', '-test_time')

    # Past bookings: time has passed AND (result exists or booking was rejected)
    past_bookings = Booking.objects.filter(user=request.user).filter(
        past_datetime_q
    ).filter(
        Q(id__in=result_booking_ids) | Q(status='rejected')
    ).order_by('-test_date', '-test_time')

    # Get results
    results = Result.objects.filter(booking__user=request.user).select_related('booking')

    context = {
        'upcoming_bookings': upcoming_bookings,
        'waiting_bookings': waiting_bookings,
        'past_bookings': past_bookings,
        'results': results,
    }

    return render(request, 'dashboard.html', context)


@login_required
def book_test_view(request):
    """Book a mock test"""
    if request.method == 'POST':
        form = BookingForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.user = request.user

            # Convert time string to time object
            time_str = form.cleaned_data['test_time']
            booking.test_time = datetime.strptime(time_str, '%H:%M').time()

            try:
                booking.save()
                messages.success(request, _('Booking submitted successfully! Please wait for admin approval.'))
                return redirect('dashboard')
            except ValueError as e:
                messages.error(request, str(e))
    else:
        form = BookingForm(user=request.user)

    # Compute min_date: use today only if today still has future slots, otherwise tomorrow
    now_local = timezone.localtime(timezone.now())
    today = now_local.date()
    now_naive = now_local.replace(tzinfo=None)

    today_slots = ['09:00', '13:00', '16:00'] if today.weekday() == 6 else ['10:00', '14:00']
    today_has_future_slots = any(
        datetime.combine(today, datetime.strptime(t, '%H:%M').time()) > now_naive
        for t in today_slots
    )
    min_date = today.strftime('%Y-%m-%d') if today_has_future_slots else (today + timedelta(days=1)).strftime('%Y-%m-%d')
    
    return render(request, 'book_test.html', {'form': form, 'min_date': min_date})


@login_required
def get_available_times(request):
    """AJAX view to get available time slots for a date"""
    date_str = request.GET.get('date')
    if not date_str:
        return JsonResponse({'times': []})
    
    try:
        test_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        weekday = test_date.weekday()
        
        # Get time slots based on day
        if weekday == 6:  # Sunday
            time_slots = ['09:00', '13:00', '16:00']
        else:  # Monday-Saturday
            time_slots = ['10:00', '14:00']
        
        # Check availability for each slot
        now_local = timezone.localtime(timezone.now())
        now_naive = now_local.replace(tzinfo=None)
        available_times = []
        for time_str in time_slots:
            time_obj = datetime.strptime(time_str, '%H:%M').time()

            # Skip already-passed slots when booking for today
            if test_date == now_naive.date() and datetime.combine(test_date, time_obj) <= now_naive:
                continue

            available_count = Booking.get_available_slots_count(test_date, time_obj)
            if available_count > 0:
                available_times.append({
                    'time': time_str,
                    'available': available_count
                })
        
        return JsonResponse({'times': available_times})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def booking_detail_view(request, booking_id):
    """View booking details"""
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    # Check if result exists
    try:
        result = booking.result
    except Result.DoesNotExist:
        result = None
    
    # Check if feedback exists
    feedback = Feedback.objects.filter(booking=booking, user=request.user).first()
    
    context = {
        'booking': booking,
        'result': result,
        'feedback': feedback,
    }
    
    return render(request, 'booking_detail.html', context)


@login_required
def submit_feedback_view(request, booking_id):
    """Submit feedback for a completed booking"""
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    # Check if feedback already exists
    if Feedback.objects.filter(booking=booking, user=request.user).exists():
        messages.warning(request, _('You have already submitted feedback for this booking.'))
        return redirect('booking_detail', booking_id=booking_id)
    
    # Check if booking is completed or has result
    if booking.status != 'completed' and not hasattr(booking, 'result'):
        messages.error(request, _('You can only submit feedback after receiving your results.'))
        return redirect('booking_detail', booking_id=booking_id)
    
    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.user = request.user
            feedback.booking = booking
            feedback.save()
            messages.success(request, _('Thank you for your feedback!'))
            return redirect('booking_detail', booking_id=booking_id)
    else:
        form = FeedbackForm()
    
    return render(request, 'submit_feedback.html', {'form': form, 'booking': booking})


# Admin Views
@login_required
@user_passes_test(is_admin)
def admin_dashboard_view(request):
    """Admin dashboard"""
    auto_complete_expired_bookings()
    # Get statistics
    total_bookings = Booking.objects.count()
    pending_bookings = Booking.objects.filter(status='pending').count()
    accepted_bookings = Booking.objects.filter(status='accepted').count()
    completed_bookings = Booking.objects.filter(status='completed').count()
    total_users = User.objects.filter(is_staff=False).count()
    
    # Get recent bookings
    recent_bookings = Booking.objects.all().order_by('-created_at')[:10]
    
    # Get pending bookings
    pending_list = Booking.objects.filter(status='pending').order_by('test_date', 'test_time')
    
    context = {
        'total_bookings': total_bookings,
        'pending_bookings': pending_bookings,
        'accepted_bookings': accepted_bookings,
        'completed_bookings': completed_bookings,
        'total_users': total_users,
        'recent_bookings': recent_bookings,
        'pending_list': pending_list,
    }
    
    return render(request, 'admin_dashboard.html', context)


@login_required
@user_passes_test(is_admin)
def admin_bookings_view(request):
    """View all bookings"""
    auto_complete_expired_bookings()
    status_filter = request.GET.get('status', 'all')
    
    bookings = Booking.objects.all().order_by('-test_date', '-test_time')
    
    if status_filter != 'all':
        bookings = bookings.filter(status=status_filter)
    
    context = {
        'bookings': bookings,
        'status_filter': status_filter,
    }
    
    return render(request, 'admin_bookings.html', context)


@login_required
@user_passes_test(is_admin)
def admin_booking_detail_view(request, booking_id):
    """Admin view for booking details"""
    booking = get_object_or_404(Booking, id=booking_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'accept':
            booking.status = 'accepted'
            booking.admin_notes = request.POST.get('admin_notes', '')
            booking.save()
            messages.success(request, _('Booking accepted successfully!'))
        
        elif action == 'reject':
            booking.status = 'rejected'
            booking.admin_notes = request.POST.get('admin_notes', '')
            booking.save()
            messages.success(request, _('Booking rejected.'))
        
        elif action == 'complete':
            booking.status = 'completed'
            booking.save()
            messages.success(request, _('Booking marked as completed.'))
        
        return redirect('admin_booking_detail', booking_id=booking_id)
    
    # Check if result exists
    try:
        result = booking.result
    except Result.DoesNotExist:
        result = None
    
    context = {
        'booking': booking,
        'result': result,
    }
    
    return render(request, 'admin_booking_detail.html', context)


@login_required
@user_passes_test(is_admin)
def admin_upload_result_view(request, booking_id):
    """Upload test results"""
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Check if result already exists
    try:
        result = booking.result
        form = ResultForm(request.POST or None, instance=result)
    except Result.DoesNotExist:
        form = ResultForm(request.POST or None)
    
    if request.method == 'POST':
        if form.is_valid():
            result = form.save(commit=False)
            result.booking = booking
            result.save()
            
            # Mark booking as completed
            booking.status = 'completed'
            booking.save()
            
            messages.success(request, _('Result uploaded successfully!'))
            return redirect('admin_booking_detail', booking_id=booking_id)
    
    context = {
        'form': form,
        'booking': booking,
    }
    
    return render(request, 'admin_upload_result.html', context)


@login_required
@user_passes_test(is_admin)
def admin_feedbacks_view(request):
    """View all feedbacks"""
    feedbacks = Feedback.objects.all().order_by('-created_at')
    
    context = {
        'feedbacks': feedbacks,
    }
    
    return render(request, 'admin_feedbacks.html', context)


@login_required
@user_passes_test(is_admin)
def admin_users_view(request):
    """View all users"""
    users = User.objects.filter(is_staff=False).order_by('-date_joined')

    context = {
        'users': users,
    }

    return render(request, 'admin_users.html', context)


@login_required
@user_passes_test(is_admin)
def admin_answers_view(request):
    """Completed bookings that still have no result uploaded."""
    bookings = (
        Booking.objects.filter(status='completed', result__isnull=True)
        .select_related('user')
        .order_by('test_date', 'test_time')
    )
    return render(request, 'admin_answers.html', {'bookings': bookings})


@login_required
@user_passes_test(is_admin)
def admin_schedule_view(request):
    """Schedule view: bookings grouped by date then time slot"""
    auto_complete_expired_bookings()
    today = timezone.localtime(timezone.now()).date()
    show_all = request.GET.get('show_all') == '1'

    bookings_qs = Booking.objects.select_related('user').order_by('test_date', 'test_time')
    if not show_all:
        bookings_qs = bookings_qs.filter(test_date__gte=today)

    # Build {date: {time: [bookings]}}
    raw = defaultdict(lambda: defaultdict(list))
    for booking in bookings_qs:
        raw[booking.test_date][booking.test_time].append(booking)

    # Convert to sorted list for the template
    schedule_list = []
    for date in sorted(raw.keys()):
        slots = [(t, raw[date][t]) for t in sorted(raw[date].keys())]
        total = sum(len(b) for _, b in slots)
        schedule_list.append({'date': date, 'slots': slots, 'total': total})

    context = {
        'schedule_list': schedule_list,
        'today': today,
        'show_all': show_all,
    }
    return render(request, 'admin_schedule.html', context)

# now everything is in this website is in English Language, can we make it language switch function, Uzbek, Russian and English, main is englis, but it should work
#   perfectly and translate very accurate and perfect, please do it for me, it is very important

