# CDI Mock System - Computer Delivered IELTS Mock Test Booking System

A comprehensive web application for managing IELTS mock test bookings, built with Django and Bootstrap.

## Features

### For Students:
- ✅ User registration and authentication
- ✅ Book mock tests with date and time selection
- ✅ Upload payment screenshots
- ✅ View booking status (Pending/Accepted/Rejected)
- ✅ View test results (Listening, Reading, Writing, Speaking, Overall)
- ✅ Submit feedback and ratings
- ✅ Bilingual support (English/Uzbek)

### For Admins:
- ✅ Admin dashboard with statistics
- ✅ Approve/reject bookings with payment verification
- ✅ Upload test results for students
- ✅ View all bookings and filter by status
- ✅ Manage users
- ✅ View student feedbacks
- ✅ Add admin notes for bookings

### System Features:
- 📅 Time slot management (max 6 students per session)
- 🕐 Monday-Saturday: 10:00, 14:00
- 🕐 Sunday: 09:00, 13:00, 16:00
- ⏰ 24-hour advance booking requirement
- 💰 Payment: 50,000 UZS
- 🌐 Bilingual interface (English/Uzbek)

## Installation

### Prerequisites:
- Python 3.8 or higher
- pip (Python package manager)

### Setup Instructions:

1. **Extract the ZIP file**
   ```bash
   unzip cdi_mock_system.zip
   cd cdi_mock_system
   ```

2. **Create a virtual environment**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # Mac/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Create a superuser (admin)**
   ```bash
   python manage.py createsuperuser
   ```
   Follow the prompts to create an admin account.

6. **Create media directory**
   ```bash
   # Windows
   mkdir media\payment_screenshots

   # Mac/Linux
   mkdir -p media/payment_screenshots
   ```

7. **Run the development server**
   ```bash
   python manage.py runserver
   ```

8. **Access the application**
   - Open your browser and go to: `http://127.0.0.1:8000/`
   - Admin panel: `http://127.0.0.1:8000/admin/`

## Usage

### For Students:

1. **Register an Account**
   - Click on "Register here" on the login page
   - Fill in your details (Full Name, Username, Email, Phone Number, Password)
   - Submit the form

2. **Book a Test**
   - Login to your account
   - Click "Book New Test" button
   - Select test date (must be at least 24 hours in advance)
   - Select available time slot
   - Upload payment screenshot
   - Submit booking

3. **View Bookings**
   - Check your dashboard for upcoming and past tests
   - View booking status
   - Once results are uploaded, you can see your scores

4. **Submit Feedback**
   - After receiving results, you can submit feedback
   - Rate the service (1-5 stars)
   - Add comments

### For Admins:

1. **Login to Admin Panel**
   - Go to `http://127.0.0.1:8000/admin/`
   - Use superuser credentials

2. **Review Bookings**
   - Navigate to Admin Dashboard
   - View pending bookings
   - Click "Review" to see payment screenshot
   - Accept or Reject bookings
   - Add admin notes if needed

3. **Upload Results**
   - Go to accepted/completed bookings
   - Click "Upload Results"
   - Enter band scores for each section (0-9, with 0.5 increments)
   - Overall score is calculated automatically
   - Submit results

4. **Manage System**
   - View all bookings with filters
   - View registered users
   - Read student feedbacks
   - Track statistics

## Project Structure

```
cdi_mock_system/
├── cdi_project/              # Django project settings
│   ├── __init__.py
│   ├── settings.py           # Project settings
│   ├── urls.py               # Main URL configuration
│   ├── wsgi.py              # WSGI configuration
│   └── asgi.py              # ASGI configuration
├── cdi_app/                  # Main application
│   ├── migrations/           # Database migrations
│   ├── templates/            # HTML templates
│   │   ├── base.html
│   │   ├── login.html
│   │   ├── register.html
│   │   ├── dashboard.html
│   │   ├── book_test.html
│   │   ├── booking_detail.html
│   │   ├── submit_feedback.html
│   │   ├── admin_dashboard.html
│   │   ├── admin_bookings.html
│   │   ├── admin_booking_detail.html
│   │   ├── admin_upload_result.html
│   │   ├── admin_users.html
│   │   └── admin_feedbacks.html
│   ├── static/               # Static files
│   │   ├── css/
│   │   │   └── style.css
│   │   └── js/
│   │       └── script.js
│   ├── __init__.py
│   ├── admin.py             # Django admin configuration
│   ├── apps.py              # App configuration
│   ├── models.py            # Database models
│   ├── forms.py             # Django forms
│   ├── views.py             # View functions
│   └── urls.py              # App URL configuration
├── media/                    # Uploaded files
│   └── payment_screenshots/
├── manage.py                # Django management script
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Database Models

### User
- Extended Django User model
- Fields: full_name, phone_number, username, email, password

### Booking
- Fields: user, test_date, test_time, payment_screenshot, status, admin_notes
- Status choices: pending, accepted, rejected, completed
- Automatic slot availability checking (max 6 per session)

### Result
- Fields: booking, listening, reading, writing, speaking, overall
- Auto-calculates overall score from individual scores

### Feedback
- Fields: user, booking, rating (1-5), comment
- Created after test completion

## Time Slots Configuration

The system automatically provides time slots based on the selected date:

- **Monday to Saturday**: 10:00 AM, 2:00 PM
- **Sunday**: 9:00 AM, 1:00 PM, 4:00 PM

Each slot can accommodate a maximum of 6 students.

## Language Support

The application supports two languages:
- English (en)
- Uzbek (uz)

Users can switch languages using the language selector in the navigation bar.

## Security Features

- Password hashing
- CSRF protection
- User authentication required for all user actions
- Admin-only access for management functions
- File upload validation

## Troubleshooting

### Common Issues:

1. **"No module named 'django'"**
   - Make sure virtual environment is activated
   - Run: `pip install -r requirements.txt`

2. **"Table doesn't exist"**
   - Run migrations: `python manage.py migrate`

3. **Static files not loading**
   - Run: `python manage.py collectstatic`

4. **Can't upload images**
   - Make sure media/payment_screenshots directory exists
   - Check file permissions

## Development

To make changes to the project:

1. Modify the code
2. If you changed models, run:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```
3. Restart the server

## Production Deployment

For production deployment:

1. Set `DEBUG = False` in settings.py
2. Change `SECRET_KEY` to a secure random key
3. Configure `ALLOWED_HOSTS`
4. Use a production database (PostgreSQL/MySQL)
5. Configure static files with `collectstatic`
6. Use a production server (Gunicorn + Nginx)

## Support

For issues or questions:
- Check the Django documentation: https://docs.djangoproject.com/
- Review the code comments
- Check the admin panel for data management

## License

This project is created for educational purposes.

## Version

Version 1.0 - February 2024

---

**Developed for CDI Mock System**
Computer Delivered IELTS Mock Test Management
