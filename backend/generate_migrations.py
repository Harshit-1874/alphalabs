#!/usr/bin/env python3
"""
Generate SQL migration files from SQLAlchemy models.

This script creates SQL CREATE TABLE statements for all models
that don't have corresponding migration files yet.

Usage:
    python generate_migrations.py
"""
import sys
from pathlib import Path
from sqlalchemy.schema import CreateTable
from models import Base

def get_existing_migrations():
    """Get list of tables that already have migrations."""
    migrations_dir = Path(__file__).parent / "migrations"
    if not migrations_dir.exists():
        migrations_dir.mkdir()
        return set()
    
    existing = set()
    for sql_file in migrations_dir.glob("*.sql"):
        # Extract table name from filename like "001_create_users_table.sql"
        if "_create_" in sql_file.stem:
            table_name = sql_file.stem.split("_create_")[1].replace("_table", "")
            existing.add(table_name)
    
    return existing

def generate_create_table_sql(table):
    """Generate CREATE TABLE SQL for a SQLAlchemy table."""
    from sqlalchemy.schema import CreateIndex
    from sqlalchemy.dialects import postgresql
    
    # Get the CREATE TABLE statement using PostgreSQL dialect
    create_stmt = str(
        CreateTable(table).compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True}
        )
    )
    
    # Format it nicely
    lines = []
    lines.append(f"-- Create {table.name} table")
    lines.append(create_stmt + ";")
    lines.append("")
    
    # Add indexes
    for index in table.indexes:
        try:
            index_sql = str(
                CreateIndex(index).compile(
                    dialect=postgresql.dialect(),
                    compile_kwargs={"literal_binds": True}
                )
            )
            if index_sql:
                lines.append(f"-- Index: {index.name}")
                lines.append(index_sql + ";")
                lines.append("")
        except Exception:
            # Skip indexes that can't be compiled
            pass
    
    return "\n".join(lines)

def get_next_migration_number():
    """Get the next migration file number."""
    migrations_dir = Path(__file__).parent / "migrations"
    if not migrations_dir.exists():
        return 1
    
    existing_numbers = []
    for sql_file in migrations_dir.glob("*.sql"):
        try:
            num = int(sql_file.stem.split("_")[0])
            existing_numbers.append(num)
        except (ValueError, IndexError):
            continue
    
    return max(existing_numbers, default=0) + 1

def main():
    print("=" * 60)
    print("SQL Migration Generator")
    print("=" * 60)
    print()
    
    migrations_dir = Path(__file__).parent / "migrations"
    migrations_dir.mkdir(exist_ok=True)
    
    # Get existing migrations
    existing_tables = get_existing_migrations()
    print(f"Found {len(existing_tables)} existing migration(s)")
    
    # Get all model tables
    all_tables = Base.metadata.tables
    print(f"Found {len(all_tables)} model table(s)")
    print()
    
    # Find tables that need migrations
    tables_to_migrate = []
    for table_name, table in sorted(all_tables.items()):
        if table_name not in existing_tables:
            tables_to_migrate.append((table_name, table))
    
    if not tables_to_migrate:
        print("✓ All tables already have migrations!")
        return 0
    
    print(f"Generating migrations for {len(tables_to_migrate)} table(s):")
    print()
    
    # Generate migration files
    migration_num = get_next_migration_number()
    
    for table_name, table in tables_to_migrate:
        # Generate filename
        filename = f"{migration_num:03d}_create_{table_name}_table.sql"
        filepath = migrations_dir / filename
        
        # Generate SQL
        sql_content = generate_create_table_sql(table)
        
        # Write file
        with open(filepath, 'w') as f:
            f.write(sql_content)
        
        print(f"✓ Created: {filename}")
        migration_num += 1
    
    print()
    print("=" * 60)
    print(f"✓ Generated {len(tables_to_migrate)} migration file(s)")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Review the generated SQL files in backend/migrations/")
    print("  2. Run migrations: python migrate.py")
    print()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
