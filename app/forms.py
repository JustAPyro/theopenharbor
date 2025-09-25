"""
WTForms for The Open Harbor application.
"""

from flask_wtf import FlaskForm
from flask_wtf.file import MultipleFileField
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, Optional
from app.models import User


class LoginForm(FlaskForm):
    """Form for user login."""

    email = StringField(
        'Email',
        validators=[
            DataRequired(message="Email is required"),
            Email(message="Please enter a valid email address")
        ],
        render_kw={"placeholder": "your@email.com", "class": "form-control"}
    )

    password = PasswordField(
        'Password',
        validators=[DataRequired(message="Password is required")],
        render_kw={"placeholder": "Enter your password", "class": "form-control"}
    )

    remember_me = BooleanField(
        'Remember Me',
        render_kw={"class": "form-check-input"}
    )

    submit = SubmitField(
        'Log In',
        render_kw={"class": "btn btn-primary w-100"}
    )


class SignUpForm(FlaskForm):
    """Form for user registration."""

    email = StringField(
        'Email',
        validators=[
            DataRequired(message="Email is required"),
            Email(message="Please enter a valid email address"),
            Length(max=120, message="Email must be less than 120 characters")
        ],
        render_kw={"placeholder": "your@email.com", "class": "form-control"}
    )

    password = PasswordField(
        'Password',
        validators=[
            DataRequired(message="Password is required"),
            Length(min=8, message="Password must be at least 8 characters long")
        ],
        render_kw={"placeholder": "Create a strong password", "class": "form-control"}
    )

    password2 = PasswordField(
        'Confirm Password',
        validators=[
            DataRequired(message="Please confirm your password"),
            EqualTo('password', message="Passwords must match")
        ],
        render_kw={"placeholder": "Confirm your password", "class": "form-control"}
    )

    submit = SubmitField(
        'Create Account',
        render_kw={"class": "btn btn-primary w-100"}
    )

    def validate_email(self, email):
        """Check if email is already registered."""
        user = User.query.filter_by(email=email.data.lower()).first()
        if user:
            raise ValidationError('Email already registered. Please use a different email.')

    def validate_password(self, password):
        """Validate password complexity."""
        if not User._is_valid_password(password.data):
            raise ValidationError(
                'Password must contain at least 8 characters including '
                'uppercase, lowercase, and one digit.'
            )


class CollectionForm(FlaskForm):
    """Form for creating a new collection."""

    name = StringField(
        'Collection Name',
        validators=[
            DataRequired(message="Collection name is required"),
            Length(min=1, max=100, message="Name must be between 1 and 100 characters")
        ],
        render_kw={"placeholder": "Enter collection name", "class": "form-control", "maxlength": "100"}
    )

    description = TextAreaField(
        'Description',
        validators=[
            Optional(),
            Length(max=500, message="Description must be less than 500 characters")
        ],
        render_kw={"placeholder": "Add a description for your collection", "class": "form-control", "rows": "3", "maxlength": "500"}
    )

    privacy = SelectField(
        'Privacy',
        choices=[
            ('unlisted', 'Unlisted - Only people with the link can access'),
            ('public', 'Public - Anyone can find this collection'),
            ('password', 'Password Protected - Requires password to access')
        ],
        default='unlisted',
        validators=[DataRequired()],
        render_kw={"class": "form-select"}
    )

    password = PasswordField(
        'Password',
        validators=[
            Optional(),
            Length(min=4, message="Password must be at least 4 characters")
        ],
        render_kw={"placeholder": "Enter password for protected collection", "class": "form-control"}
    )

    expiration = SelectField(
        'Expiration',
        choices=[
            ('', 'Never'),
            ('1_week', '1 Week'),
            ('1_month', '1 Month'),
            ('3_months', '3 Months'),
            ('1_year', '1 Year')
        ],
        default='',
        validators=[Optional()],
        render_kw={"class": "form-select"}
    )

    submit = SubmitField(
        'Create Collection',
        render_kw={"class": "btn btn-primary"}
    )