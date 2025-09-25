# Database Migrations for The Open Harbor

This document explains how to use the database migration system for The Open Harbor project.

## Overview

We use **Alembic** (SQLAlchemy's migration tool) to manage database schema changes. This ensures that:
- Database changes are version-controlled
- Schema updates can be applied safely in production
- Changes can be rolled back if needed
- Multiple developers can sync database schemas

## Quick Start

### For Developers

```bash
# Check current migration status
python3 migrate.py status

# Apply all pending migrations (most common)
python3 migrate.py upgrade

# Create a new migration after changing models
python3 migrate.py create "Description of your change"
```

### For Production Deployment

```bash
# 1. Always backup your database first!
# 2. Check what migrations will be applied
python3 migrate.py status

# 3. Apply migrations
python3 migrate.py upgrade

# 4. Verify the application works correctly
```

## Current Migrations

### Migration History

1. **71dda59686db - Initial schema** (Base)
   - Creates `users` table
   - Creates `collections` table
   - Creates `files` table (original version)

2. **5b09ebe23c76 - Add R2 storage fields** (Current)
   - Adds `storage_backend` column to `files` table
   - Adds `metadata_json` column to `files` table
   - Adds database indexes for performance
   - Ensures backward compatibility with existing files

## Available Commands

| Command | Description | Example |
|---------|-------------|---------|
| `status` | Show current migration status | `python3 migrate.py status` |
| `upgrade` | Apply all pending migrations | `python3 migrate.py upgrade` |
| `upgrade <rev>` | Upgrade to specific revision | `python3 migrate.py upgrade 71dda59686db` |
| `downgrade <rev>` | Downgrade to specific revision | `python3 migrate.py downgrade 71dda59686db` |
| `history` | Show migration history | `python3 migrate.py history` |
| `current` | Show current revision | `python3 migrate.py current` |
| `create <name>` | Create new migration file | `python3 migrate.py create "Add user settings"` |
| `help` | Show help message | `python3 migrate.py help` |

## Understanding Migration Files

Migration files are stored in `migrations/versions/` and contain:

- **Upgrade function**: Applies the schema changes
- **Downgrade function**: Reverses the schema changes
- **Revision ID**: Unique identifier for this migration
- **Down revision**: Previous migration this depends on

Example migration file:
```python
def upgrade() -> None:
    """Add new column."""
    op.add_column('users', sa.Column('last_login', sa.DateTime()))

def downgrade() -> None:
    """Remove column."""
    op.drop_column('users', 'last_login')
```

## Creating New Migrations

### After Changing Models

1. Update your model in `app/models.py`
2. Create a migration: `python3 migrate.py create "Describe your change"`
3. Edit the generated migration file in `migrations/versions/`
4. Test the migration: `python3 migrate.py upgrade`
5. Test the rollback: `python3 migrate.py downgrade <previous_rev>`

### Migration Best Practices

✅ **DO:**
- Always review generated migration files
- Test migrations on a copy of production data
- Use descriptive migration messages
- Make backward-compatible changes when possible
- Backup database before running migrations in production

❌ **DON'T:**
- Edit migration files after they've been applied in production
- Skip migrations or apply them out of order
- Delete migration files
- Make breaking changes without planning downtime

## Common Scenarios

### Adding a New Column
```python
def upgrade() -> None:
    op.add_column('users', sa.Column('phone', sa.String(20), nullable=True))

def downgrade() -> None:
    op.drop_column('users', 'phone')
```

### Adding an Index
```python
def upgrade() -> None:
    op.create_index('ix_users_email', 'users', ['email'])

def downgrade() -> None:
    op.drop_index('ix_users_email', table_name='users')
```

### Updating Existing Data
```python
def upgrade() -> None:
    # Add column first
    op.add_column('files', sa.Column('storage_backend', sa.String(20)))

    # Update existing records
    op.execute("UPDATE files SET storage_backend = 'local' WHERE storage_backend IS NULL")

def downgrade() -> None:
    op.drop_column('files', 'storage_backend')
```

## Troubleshooting

### "No such column" errors
This usually means you need to run migrations:
```bash
python3 migrate.py upgrade
```

### Migration conflicts
If you get conflicts, check:
1. Are you on the right branch?
2. Do you need to pull latest migrations?
3. Are there uncommitted migration files?

### Rolling back a migration
```bash
# Check current revision
python3 migrate.py current

# Rollback to previous revision
python3 migrate.py downgrade <previous_revision_id>
```

### Starting fresh (development only)
```bash
# Delete database file
rm openharbor.db

# Run all migrations
python3 migrate.py upgrade
```

## Production Deployment Process

### Automated Deployment
```bash
#!/bin/bash
# deployment-script.sh

# 1. Backup database
pg_dump mydb > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Apply migrations
python3 migrate.py upgrade

# 3. Restart application
systemctl restart openharbor

# 4. Verify health
curl -f http://localhost:5000/health || exit 1
```

### Manual Deployment
1. **Before deployment:**
   - Review all migration files
   - Test migrations on staging
   - Schedule maintenance window if needed
   - Backup database

2. **During deployment:**
   - Pull latest code
   - Run migrations: `python3 migrate.py upgrade`
   - Restart application
   - Verify functionality

3. **After deployment:**
   - Monitor application logs
   - Check database integrity
   - Verify core functionality works

## Files and Directories

```
├── alembic.ini              # Alembic configuration
├── migrate.py               # Simple migration helper script
├── migrations/
│   ├── env.py              # Alembic environment setup
│   ├── script.py.mako      # Migration template
│   └── versions/           # Migration files
│       ├── 71dda59686db_initial_schema.py
│       └── 5b09ebe23c76_add_r2_storage_fields.py
└── DATABASE_MIGRATIONS.md  # This documentation
```

## Getting Help

- **Migration issues:** Check `migrations/versions/` files
- **Alembic docs:** https://alembic.sqlalchemy.org/
- **SQLAlchemy docs:** https://docs.sqlalchemy.org/
- **Project help:** `python3 migrate.py help`

## R2 Storage Migration Details

The R2 storage integration adds two new fields to the `files` table:

- **storage_backend** (String): `'local'` or `'r2'` - indicates where the file is stored
- **metadata_json** (Text): JSON blob storing R2-specific metadata (upload method, parts count, etc.)

These changes are **backward compatible**:
- Existing files automatically get `storage_backend='local'`
- New R2 files get `storage_backend='r2'` and appropriate metadata
- The application works with both old and new file records

This migration enables the CloudflareR2 integration while preserving existing functionality.