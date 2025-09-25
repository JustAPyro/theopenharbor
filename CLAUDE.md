# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Setup

**Dependencies Installation:**
```bash
pip install -r .requirements.txt
```

**Environment Configuration:**
- Copy `.env` file and ensure `TSH_SECRET_KEY` is set
- Required environment variables are validated at startup

## Project Architecture

**Flask Application Structure:**
- `app/__init__.py`: Application factory pattern with environment validation and blueprint registration
- `app/routes.py`: Main routes blueprint rendering The Open Harbor homepage
- `app/templates/`: Jinja2 templates using base template inheritance
- `app/static/css/`: Brand design system CSS with The Open Harbor colors and typography
- `.env`: Environment variables (TSH_SECRET_KEY required)

**Key Components:**
- Uses Flask application factory pattern via `create_app()`
- Environment variables loaded with python-dotenv
- Routes organized as Flask blueprints
- Template inheritance with base.html and page-specific templates
- Bootstrap 5 + custom CSS following The Open Harbor brand guidelines
- Runtime validation of required environment variables

**Brand System:**
- Primary color: #1E5F74 (Harbor Trust)
- Secondary color: #F4A259 (Beacon Light)
- Typography: Poppins (headings) + Inter (body)
- Design tokens in CSS custom properties

**Running the Application:**
The application uses Flask's standard patterns. To run locally, ensure the virtual environment is activated and environment variables are set.

## Testing

**Test Framework:**
- Uses pytest for comprehensive testing
- Test configuration in `pytest.ini`
- Shared fixtures in `tests/conftest.py`

**Running Tests:**
```bash
# Run all tests
python run_tests.py

# Run with coverage
python run_tests.py --coverage

# Run with linting
python run_tests.py --lint

# Run specific test file
python run_tests.py --test-file tests/test_routes.py

# Direct pytest usage
python -m pytest tests/ -v
```

**Test Structure:**
- `tests/test_routes.py`: Route and page loading tests
- `tests/test_application.py`: Application factory and configuration tests
- `tests/conftest.py`: Shared pytest fixtures

**Development Dependencies:**
```bash
pip install -r requirements-dev.txt
```