from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Service, Booking

booking_bp = Blueprint("booking", __name__)


@booking_bp.route("/<slug>", methods=["GET", "POST"])
@login_required
def new_booking(slug):
    service = Service.query.filter_by(slug=slug, is_bookable=True, is_active=True).first_or_404()

    if request.method == "POST":
        date_str = request.form.get("date")
        time_str = request.form.get("time")
        location = request.form.get("location", "").strip()
        event_type = request.form.get("event_type", "").strip()
        notes = request.form.get("notes", "").strip()

        error = None
        preferred_date = preferred_time = None
        try:
            preferred_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            preferred_time = datetime.strptime(time_str, "%H:%M").time()
        except (ValueError, TypeError):
            error = "Please choose a valid date and time."

        if not error and preferred_date < datetime.utcnow().date():
            error = "Please choose a date in the future."

        open_hr = current_app.config["BUSINESS_OPEN_HOUR"]
        close_hr = current_app.config["BUSINESS_CLOSE_HOUR"]
        if not error and preferred_time and not (open_hr <= preferred_time.hour < close_hr):
            error = f"Our booking hours are {open_hr}:00 – {close_hr}:00. Please pick a time in this range."

        if error:
            flash(error, "error")
            return render_template("booking/new.html", service=service, form_data=request.form)

        booking = Booking(
            user_id=current_user.id,
            service_id=service.id,
            preferred_date=preferred_date,
            preferred_time=preferred_time,
            location=location,
            event_type=event_type,
            notes=notes,
        )
        db.session.add(booking)
        db.session.commit()

        flash(f"Booking request sent! Your reference is {booking.reference}. We'll confirm shortly.", "success")
        return redirect(url_for("dashboard.my_bookings"))

    return render_template("booking/new.html", service=service, form_data={})
