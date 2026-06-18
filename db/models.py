from datetime import datetime, date
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, DateTime, Date


class Base(DeclarativeBase):
    pass


# defining the schema as well as creating the table using sqlalchemy  ORM.
class LendingRecord(Base):
    __tablename__ = "lending_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    person: Mapped[str] = mapped_column(String(255))
    amount: Mapped[int] = mapped_column(Integer)
    direction: Mapped[str] = mapped_column(String(10))
    expected_payback_by: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    raw_text: Mapped[str] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
