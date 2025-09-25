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
- `app/routes.py`: Main routes blueprint with basic home route
- `.env`: Environment variables (TSH_SECRET_KEY required)

**Key Components:**
- Uses Flask application factory pattern via `create_app()`
- Environment variables loaded with python-dotenv
- Routes organized as Flask blueprints
- Runtime validation of required environment variables

**Running the Application:**
The application uses Flask's standard patterns. To run locally, ensure the virtual environment is activated and environment variables are set.