@echo off
echo ========================================
echo CDI Mock System - Quick Start
echo ========================================
echo.

echo Creating virtual environment...
python -m venv venv
call venv\Scripts\activate

echo.
echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Running migrations...
python manage.py makemigrations
python manage.py migrate

echo.
echo ========================================
echo Setup complete!
echo.
echo To create an admin user, run:
echo python manage.py createsuperuser
echo.
echo To start the server, run:
echo python manage.py runserver
echo.
echo Then open: http://127.0.0.1:8000/
echo ========================================
pause
