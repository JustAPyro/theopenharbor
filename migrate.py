#!/usr/bin/env python3
"""
Simple database migration script for The Open Harbor.
This wraps Alembic commands to make them easier to use.
"""

import sys
import os
from pathlib import Path

# Add the project directory to Python path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

# Import after path setup
import subprocess
from flask import Flask


def run_command(command):
    """Run a command and return the result."""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=project_dir)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"Error running command: {e}", file=sys.stderr)
        return False


def show_help():
    """Show help message."""
    help_text = """
The Open Harbor Database Migration Tool

Usage:
    python migrate.py <command>

Commands:
    status          Show current migration status
    upgrade         Apply all pending migrations
    upgrade <rev>   Upgrade to specific revision
    downgrade <rev> Downgrade to specific revision
    history         Show migration history
    current         Show current revision
    create <name>   Create a new migration file
    help            Show this help message

Examples:
    python migrate.py status       # Check what migrations need to be applied
    python migrate.py upgrade      # Apply all pending migrations
    python migrate.py create "Add user preferences"  # Create new migration
    python migrate.py history      # Show all migrations

Before running migrations in production:
1. Backup your database
2. Test migrations in a staging environment
3. Review the migration files in migrations/versions/

Current migrations:
- 71dda59686db: Initial schema (creates users, collections, files tables)
- 5b09ebe23c76: Add R2 storage fields (adds storage_backend, metadata_json)
"""
    print(help_text)


def main():
    if len(sys.argv) < 2:
        show_help()
        return

    command = sys.argv[1].lower()

    # Ensure we're in the project directory
    os.chdir(project_dir)

    if command == 'help':
        show_help()

    elif command == 'status':
        print("🔍 Checking migration status...")
        if not run_command(".venv/bin/alembic current"):
            print("❌ Failed to get current revision")
            return
        print("\n📋 Pending migrations:")
        run_command(".venv/bin/alembic heads")

    elif command == 'upgrade':
        if len(sys.argv) > 2:
            revision = sys.argv[2]
            print(f"⬆️  Upgrading to revision {revision}...")
            success = run_command(f".venv/bin/alembic upgrade {revision}")
        else:
            print("⬆️  Applying all pending migrations...")
            success = run_command(".venv/bin/alembic upgrade head")

        if success:
            print("✅ Migration completed successfully!")
        else:
            print("❌ Migration failed!")

    elif command == 'downgrade':
        if len(sys.argv) < 3:
            print("❌ Downgrade requires a revision. Usage: python migrate.py downgrade <revision>")
            return

        revision = sys.argv[2]
        print(f"⬇️  Downgrading to revision {revision}...")
        print("⚠️  WARNING: This will remove data! Make sure you have a backup.")

        confirm = input("Are you sure you want to downgrade? (yes/no): ").lower()
        if confirm != 'yes':
            print("❌ Downgrade cancelled.")
            return

        success = run_command(f".venv/bin/alembic downgrade {revision}")
        if success:
            print("✅ Downgrade completed!")
        else:
            print("❌ Downgrade failed!")

    elif command == 'history':
        print("📜 Migration history:")
        run_command(".venv/bin/alembic history --verbose")

    elif command == 'current':
        print("📍 Current revision:")
        run_command(".venv/bin/alembic current --verbose")

    elif command == 'create':
        if len(sys.argv) < 3:
            print("❌ Create requires a message. Usage: python migrate.py create 'Migration description'")
            return

        message = sys.argv[2]
        print(f"📝 Creating new migration: {message}")
        success = run_command(f'.venv/bin/alembic revision -m "{message}"')
        if success:
            print("✅ Migration file created! Don't forget to edit it.")
            print("💡 Tip: Use 'alembic revision --autogenerate' if you've changed models")
        else:
            print("❌ Failed to create migration!")

    else:
        print(f"❌ Unknown command: {command}")
        print("💡 Use 'python migrate.py help' to see available commands")


if __name__ == '__main__':
    main()