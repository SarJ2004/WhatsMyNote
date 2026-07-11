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


def reset_database():
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)

    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    migrate_schema()

    print("Done!")


if __name__ == "__main__":
    reset_database()
