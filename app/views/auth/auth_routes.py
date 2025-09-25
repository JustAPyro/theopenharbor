"""
Authentication routes for The Open Harbor application.
"""

from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from app.forms import LoginForm, SignUpForm
from app.models import db, User
from datetime import datetime, timezone
import logging

from . import auth as bp

# Set up logging
logger = logging.getLogger(__name__)


@bp.route('/sign-up', methods=['GET', 'POST'])
def signup():
    """Handle user registration."""
    # Redirect if already logged in
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    form = SignUpForm()

    if form.validate_on_submit():
        try:
            # Create new user
            user = User(email=form.email.data.lower().strip())
            user.set_password(form.password.data)

            # Save to database
            db.session.add(user)
            db.session.commit()

            # Log the user in immediately after registration
            login_user(user, remember=False)
            user.last_login = datetime.now(timezone.utc)
            db.session.commit()

            flash('Welcome to The Open Harbor! Your account has been created.', 'success')
            logger.info(f"New user registered: {user.email}")

            # Redirect to intended page or home
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('main.home'))

        except ValueError as e:
            flash(str(e), 'error')
            logger.warning(f"Registration failed for {form.email.data}: {str(e)}")
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'error')
            logger.error(f"Registration error for {form.email.data}: {str(e)}")

    return render_template('auth/signup.html', form=form)


@bp.route('/log-in', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    # Redirect if already logged in
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    form = LoginForm()

    if form.validate_on_submit():
        try:
            # Find user by email
            user = User.query.filter_by(email=form.email.data.lower().strip()).first()

            # Check credentials
            if user and user.check_password(form.password.data):
                if not user.is_active:
                    flash('Your account has been deactivated. Please contact support.', 'error')
                    logger.warning(f"Inactive user attempted login: {user.email}")
                    return render_template('auth/login.html', form=form)

                # Log the user in
                login_user(user, remember=form.remember_me.data)
                user.last_login = datetime.now(timezone.utc)
                db.session.commit()

                flash(f'Welcome back!', 'success')
                logger.info(f"User logged in: {user.email}")

                # Redirect to intended page or home
                next_page = request.args.get('next')
                if next_page and next_page.startswith('/'):
                    return redirect(next_page)
                return redirect(url_for('main.home'))
            else:
                flash('Invalid email or password. Please try again.', 'error')
                logger.warning(f"Failed login attempt for: {form.email.data}")

        except Exception as e:
            flash('An error occurred during login. Please try again.', 'error')
            logger.error(f"Login error for {form.email.data}: {str(e)}")

    return render_template('auth/login.html', form=form)


@bp.route('/log-out')
@login_required
def logout():
    """Handle user logout."""
    user_email = current_user.email if current_user.is_authenticated else "Unknown"
    logout_user()
    flash('You have been logged out successfully.', 'info')
    logger.info(f"User logged out: {user_email}")
    return redirect(url_for('main.home'))


# Error handlers for the auth blueprint
@bp.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors in auth blueprint."""
    return render_template('errors/404.html'), 404


@bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors in auth blueprint."""
    db.session.rollback()
    return render_template('errors/500.html'), 500
