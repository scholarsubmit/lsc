# app/blueprints/booking/routes.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, date, time
from app.extensions import db
from app.models import Service, Booking

booking_bp = Blueprint("booking", __name__)


@booking_bp.route("/new/<slug>", methods=["GET", "POST"])
@login_required
def new_booking(slug):
    service = Service.query.filter_by(slug=slug, is_active=True).first_or_404()
    
    if not service.is_bookable:
        flash("This service is not bookable.", "error")
        return redirect(url_for("catalog.detail", slug=service.slug))
    
    form_data = {}
    
    if request.method == "POST":
        # Get form data
        preferred_date_str = request.form.get("preferred_date", "").strip()
        preferred_time_str = request.form.get("preferred_time", "").strip()
        location = request.form.get("location", "").strip()
        event_type = request.form.get("event_type", "").strip()
        notes = request.form.get("notes", "").strip()
        
        # Store form data for repopulating
        form_data = {
            'preferred_date': preferred_date_str,
            'preferred_time': preferred_time_str,
            'location': location,
            'event_type': event_type,
            'notes': notes
        }
        
        # Validate date and time
        if not preferred_date_str or not preferred_time_str:
            flash("Please select a valid date and time.", "error")
            return render_template("booking/new.html", service=service, form_data=form_data)
        
        try:
            # Parse date and time
            preferred_date = datetime.strptime(preferred_date_str, "%Y-%m-%d").date()
            preferred_time = datetime.strptime(preferred_time_str, "%H:%M").time()
        except ValueError:
            flash("Invalid date or time format. Please try again.", "error")
            return render_template("booking/new.html", service=service, form_data=form_data)
        
        # Validate date is not in the past
        today = date.today()
        if preferred_date < today:
            flash("Please select today or a future date.", "error")
            return render_template("booking/new.html", service=service, form_data=form_data)
        
        # Validate time is within business hours (9 AM - 6 PM)
        business_open = time(9, 0)
        business_close = time(18, 0)
        if preferred_time < business_open or preferred_time > business_close:
            flash("Please select a time between 9:00 AM and 6:00 PM.", "error")
            return render_template("booking/new.html", service=service, form_data=form_data)
        
        # Create booking
        booking = Booking(
            user_id=current_user.id,
            service_id=service.id,
            preferred_date=preferred_date,
            preferred_time=preferred_time,
            location=location,
            event_type=event_type,
            notes=notes,
            status="pending"
        )
        
        db.session.add(booking)
        db.session.commit()
        
        flash(f"Booking confirmed! Your reference is {booking.reference}. We'll send you a confirmation email shortly.", "success")
        return redirect(url_for("dashboard.bookings"))
    
    # GET request - set default date to tomorrow
    from datetime import timedelta
    tomorrow = date.today() + timedelta(days=1)
    form_data = {
        'preferred_date': tomorrow.strftime("%Y-%m-%d"),
        'preferred_time': "10:00"
    }
    
    return render_template("booking/new.html", service=service, form_data=form_data)