# app/blueprints/auth/routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models import User
from datetime import datetime

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    # If already logged in, redirect based on role
    if current_user.is_authenticated:
        return redirect_after_login()
    
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        remember = bool(request.form.get("remember"))
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            
            # Update last login
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            # Store user role in session
            session['user_role'] = 'admin' if user.is_admin else 'user'
            
            # Redirect based on role
            return redirect_after_login()
        else:
            flash("Invalid email or password.", "error")
    
    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    # If already logged in, redirect based on role
    if current_user.is_authenticated:
        return redirect_after_login()
    
    # Initialize form_data for GET requests
    form_data = {}
    
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        
        # Store form data for repopulating
        form_data = {
            'full_name': full_name,
            'email': email,
            'phone': phone
        }
        
        # Validation
        if not full_name or not email or not password:
            flash("All required fields must be filled.", "error")
            return render_template("auth/register.html", form_data=form_data)
        
        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("auth/register.html", form_data=form_data)
        
        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template("auth/register.html", form_data=form_data)
        
        if User.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "error")
            return render_template("auth/register.html", form_data=form_data)
        
        # Create user (non-admin by default)
        user = User(
            full_name=full_name,
            email=email,
            phone=phone,
            is_admin=False
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        # Log in the new user
        login_user(user)
        session['user_role'] = 'user'
        
        flash("Account created successfully! Welcome to Les Starry Corporate.", "success")
        return redirect(url_for('catalog.list_services'))
    
    return render_template("auth/register.html", form_data=form_data)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('auth.login'))


def redirect_after_login():
    """Redirect users based on their role."""
    # If there's a 'next' parameter, use that first
    next_url = request.args.get('next')
    if next_url and next_url.startswith('/'):
        return redirect(next_url)
    
    # Redirect based on role
    if current_user.is_admin:
        return redirect(url_for('admin.dashboard'))
    else:
        return redirect(url_for('catalog.list_services'))


# Optional: Add a forgot password route
@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """Forgot password page."""
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        user = User.query.filter_by(email=email).first()
        
        if user:
            # TODO: Send password reset email
            flash("If an account exists with this email, you will receive a password reset link.", "info")
        else:
            flash("If an account exists with this email, you will receive a password reset link.", "info")
        
        return redirect(url_for('auth.login'))
    
    return render_template("auth/forgot_password.html")