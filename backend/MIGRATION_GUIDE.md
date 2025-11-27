# Database Migration Guide

## Quick Start

### 1. Generate Migration Files

When you add new models or modify existing ones, generate SQL migration files:

```bash
cd backend
python generate_migrations.py
```

This will:
- Scan all SQLAlchemy models
- Compare with existing migrations
- Generate SQL files for any new tables
- Use PostgreSQL-specific syntax

### 2. Run Migrations

Apply the generated migrations to your database:

```bash
python migrate.py
```

This will:
- Connect to your database
- Run all `.sql` files in `migrations/` directory
- Skip migrations that have already been applied
- Report success/failure for each migration

**Note:** If migrations fail due to foreign key dependencies, just run `python migrate.py` again. The script will automatically skip already-created tables and create the remaining ones.

### 3. Validate Database

Verify everything is set up correctly:

```bash
python init_db.py
```

This will:
- Check database connection
- Verify all tables exist
- Validate schema matches models
- Provide detailed diagnostics

## Complete Workflow Example

```bash
# 1. Make changes to your models
vim backend/models/user.py

# 2. Generate migrations
python generate_migrations.py

# 3. Review the generated SQL (optional but recommended)
cat backend/migrations/014_create_new_table.sql

# 4. Run migrations (may need to run 2-3 times for dependencies)
python migrate.py
python migrate.py  # Run again if some failed due to dependencies

# 5. Validate everything works
python init_db.py

# 6. Start your application
python app.py
```

## Migration Files

### Naming Convention

Migration files follow this pattern:
```
NNN_create_TABLENAME_table.sql
```

Examples:
- `001_create_users_table.sql`
- `002_create_activity_logs_table.sql`
- `013_add_missing_users_columns.sql`

### Manual Migrations

For schema changes (not new tables), create manual migration files:

```sql
-- 014_add_user_avatar_column.sql
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(500);
```

Then run:
```bash
python migrate.py
```

## Troubleshooting

### Foreign Key Dependency Errors

**Problem:** Migration fails with "relation does not exist"

**Solution:** Run `python migrate.py` multiple times. Each run will create more tables until all dependencies are satisfied.

```bash
python migrate.py  # Creates some tables
python migrate.py  # Creates more tables
python migrate.py  # All tables created
```

### Table Already Exists

**Problem:** Migration fails with "relation already exists"

**Solution:** This is normal! The migration script doesn't track which migrations have run, so it tries to run all of them. Tables that already exist will show errors, but this is expected.

### Schema Mismatch

**Problem:** `init_db.py` reports missing or extra columns

**Solution:** 
1. Check if you modified a model after creating its table
2. Create a manual migration to add/remove columns
3. Run `python migrate.py`

Example:
```sql
-- 015_update_users_schema.sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS new_field VARCHAR(100);
ALTER TABLE users DROP COLUMN IF EXISTS old_field;
```

### Connection Errors

**Problem:** Cannot connect to database

**Solution:**
1. Check your `.env` file has correct credentials
2. Verify database is running
3. Test connection: `python init_db.py`

## Environment Variables

The migration tools use the same database configuration as your app:

```bash
# Option 1: Full connection string
DATABASE_URL=postgresql://user:password@host:5432/database

# Option 2: Individual components
SUPABASE_DB_HOST=your-host.supabase.com
SUPABASE_DB_PORT=5432
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=postgres.xxxxx
SUPABASE_DB_PASSWORD=your-password

# Option 3: Legacy (for migrate.py only)
DB_CONNECTION_STRING=postgresql://user:password@host:5432/database
```

## Best Practices

### 1. Always Generate Migrations

Don't manually create tables in production. Always use migrations:
```bash
python generate_migrations.py
python migrate.py
```

### 2. Review Generated SQL

Before running migrations, review the generated SQL:
```bash
cat backend/migrations/NNN_*.sql
```

### 3. Test Locally First

Always test migrations on your local database before production:
```bash
# Local testing
python migrate.py
python init_db.py

# If all good, run on production
```

### 4. Backup Before Migrations

For production databases, always backup first:
```bash
# Supabase: Use dashboard to create backup
# Or use pg_dump
pg_dump $DATABASE_URL > backup.sql
```

### 5. Version Control

Commit migration files to git:
```bash
git add backend/migrations/*.sql
git commit -m "Add migrations for new tables"
```

## Advanced: Migration Tracking

The current migration system is simple and doesn't track which migrations have been applied. For production use, consider:

1. **Alembic** - Full-featured migration tool for SQLAlchemy
2. **Custom tracking** - Add a `migrations` table to track applied migrations
3. **Supabase Migrations** - Use Supabase's built-in migration system

Example with tracking table:
```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT NOW()
);
```

## Summary

- **Generate:** `python generate_migrations.py`
- **Apply:** `python migrate.py` (run 2-3 times if needed)
- **Validate:** `python init_db.py`
- **Start app:** `python app.py` (validates automatically)

Your database is now fully set up with all 12 tables! 🎉
