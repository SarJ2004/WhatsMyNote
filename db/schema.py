# models.py
from datetime import datetime, date, timezone
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from enum import Enum
from sqlalchemy import (
    String,
    Text,
    Integer,
    DateTime,
    Date,
    ForeignKey,
    Enum as SqlEnum,
)


class RecordType(str, Enum):
    LENDING = "lending"
    EXPENSE = "expense"
    TRANSFER = "transfer"
    INCOME = "income"
    REMINDER = "reminder"
    TASK = "task"


class LendingDirection(str, Enum):
    LENT = "lent"
    BORROWED = "borrowed"


class Base(DeclarativeBase):
    pass


class BaseRecord(Base):
    __tablename__ = "records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    record_type: Mapped[RecordType] = mapped_column(SqlEnum(RecordType), nullable=False)
    lending: Mapped["LendingRecord"] = relationship(
        "LendingRecord",
        back_populates="record",
        uselist=False,
        cascade="all, delete-orphan",
    )
    expense: Mapped["ExpenseRecord"] = relationship(
        "ExpenseRecord",
        back_populates="record",
        uselist=False,
        cascade="all, delete-orphan",
    )
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    settled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class LendingRecord(Base):
    __tablename__ = "lending_records"

    record_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("records.id", ondelete="CASCADE"),
        primary_key=True,
    )
    person: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    direction: Mapped[LendingDirection] = mapped_column(
        SqlEnum(LendingDirection), nullable=False
    )
    expected_payback_by: Mapped[date | None] = mapped_column(Date, nullable=True)
    record: Mapped["BaseRecord"] = relationship(
        "BaseRecord",
        back_populates="lending",
        uselist=False,
    )


class ExpenseRecord(Base):
    __tablename__ = "expense_records"

    record_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("records.id", ondelete="CASCADE"),
        primary_key=True,
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(255), nullable=False)
    merchant: Mapped[str] = mapped_column(String(255), nullable=True)
    payment_source: Mapped[str] = mapped_column(String(255), nullable=True)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    item: Mapped[str] = mapped_column(String(255), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    record: Mapped["BaseRecord"] = relationship(
        "BaseRecord",
        back_populates="expense",
        uselist=False,
    )
