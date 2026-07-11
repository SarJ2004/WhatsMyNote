from sqlalchemy import inspect, text

from db.schema import Base
from db.config import engine


def _ensure_column(table_name: str, column_name: str, column_sql: str) -> None:
    inspector = inspect(engine)
    existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
    if column_name in existing_columns:
        return

    with engine.begin() as connection:
        connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}"))


def migrate_schema():
    _ensure_column("account_records", "current_balance", "current_balance INTEGER NOT NULL DEFAULT 0")
    _ensure_column("account_records", "is_default", "is_default BOOLEAN NOT NULL DEFAULT FALSE")
    _ensure_column("lending_records", "source_account", "source_account VARCHAR(255) NULL")
    _ensure_column("income_records", "deposit_account", "deposit_account VARCHAR(255) NULL")

def setup_rls():
    print("Setting up Row Level Security (RLS)...")
    tables = [
        "records", "account_records", "expense_records", 
        "lending_records", "income_records", "budget_records", "transfer_records"
    ]
    with engine.begin() as conn:
        # Grant permissions to the authenticated role
        conn.execute(text("GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;"))
        conn.execute(text("GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO authenticated;"))

        for table in tables:
            conn.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;"))
            
        # Policy for the main records table
        conn.execute(text("DROP POLICY IF EXISTS tenant_isolation ON records;"))
        conn.execute(text("""
            CREATE POLICY tenant_isolation ON records 
            FOR ALL 
            USING (user_id = current_setting('request.jwt.claim.sub', true))
            WITH CHECK (user_id = current_setting('request.jwt.claim.sub', true));
        """))

        # Policies for child tables
        for child in tables[1:]:
            conn.execute(text(f"DROP POLICY IF EXISTS tenant_isolation ON {child};"))
            conn.execute(text(f"""
                CREATE POLICY tenant_isolation ON {child} 
                FOR ALL 
                USING (record_id IN (SELECT id FROM records WHERE user_id = current_setting('request.jwt.claim.sub', true)))
                WITH CHECK (record_id IN (SELECT id FROM records WHERE user_id = current_setting('request.jwt.claim.sub', true)));
            """))


def reset_database():
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)

    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    migrate_schema()
    setup_rls()

    print("Done!")


if __name__ == "__main__":
    reset_database()
