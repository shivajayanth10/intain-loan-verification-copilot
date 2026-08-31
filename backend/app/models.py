from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(30))

    audit_logs: Mapped[list["AuditLog"]] = relationship(
        back_populates="user"
    )


class ImportBatch(Base):
    __tablename__ = "imports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String(255))
    source_system: Mapped[str | None] = mapped_column(String(100), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    successful_rows: Mapped[int] = mapped_column(Integer, default=0)
    failed_rows: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(30), default="uploaded")

    loans: Mapped[list["Loan"]] = relationship(
        back_populates="import_batch"
    )


class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    loan_id: Mapped[str] = mapped_column(String(100), index=True)
    borrower_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    loan_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    origination_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    maturity_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    original_principal: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2), nullable=True
    )
    current_balance: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2), nullable=True
    )

    interest_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 4), nullable=True
    )
    term_months: Mapped[int | None] = mapped_column(Integer, nullable=True)

    borrower_state: Mapped[str | None] = mapped_column(
        String(10), nullable=True
    )
    loan_purpose: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    credit_grade: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )
    employment_length: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    income_band: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )

    payment_status: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    days_past_due: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )

    servicer_name: Mapped[str | None] = mapped_column(
        String(150), nullable=True
    )
    last_payment_date: Mapped[date | None] = mapped_column(
        Date, nullable=True
    )
    last_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    document_status: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    source_system: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )

    import_id: Mapped[int] = mapped_column(
        ForeignKey("imports.id"), index=True
    )

    import_batch: Mapped["ImportBatch"] = relationship(
        back_populates="loans"
    )

    validation_results: Mapped[list["ValidationResult"]] = relationship(
        back_populates="loan",
        cascade="all, delete-orphan",
    )

    exceptions: Mapped[list["ExceptionRecord"]] = relationship(
        back_populates="loan",
        cascade="all, delete-orphan",
    )


class ValidationResult(Base):
    __tablename__ = "validation_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    loan_id: Mapped[int] = mapped_column(
        ForeignKey("loans.id"), index=True
    )

    rule_code: Mapped[str] = mapped_column(String(100))
    rule_name: Mapped[str] = mapped_column(String(200))
    passed: Mapped[bool] = mapped_column(Boolean, default=True)
    severity: Mapped[str] = mapped_column(String(30), default="info")
    message: Mapped[str] = mapped_column(Text)

    checked_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    loan: Mapped["Loan"] = relationship(
        back_populates="validation_results"
    )


class ExceptionRecord(Base):
    __tablename__ = "exceptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    loan_id: Mapped[int] = mapped_column(
        ForeignKey("loans.id"), index=True
    )

    exception_type: Mapped[str] = mapped_column(String(100))
    severity: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(
        String(30), default="open"
    )

    field_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    message: Mapped[str] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    loan: Mapped["Loan"] = relationship(
        back_populates="exceptions"
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    loan_id: Mapped[int | None] = mapped_column(
        ForeignKey("loans.id"), nullable=True, index=True
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )

    action: Mapped[str] = mapped_column(String(100))
    details: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    user: Mapped["User"] = relationship(
        back_populates="audit_logs"
    )
class VerifiedLoan(Base):
    __tablename__ = "verified_loans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    loan_id: Mapped[str] = mapped_column(String(100), index=True)
    source_file: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    validation_status: Mapped[str] = mapped_column(
        String(30), default="passed"
    )

    reviewer_decision: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )

    ai_recommendation: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    verified_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    verified_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    record_hash: Mapped[str] = mapped_column(
        String(64), index=True
    )

    canonical_data: Mapped[str] = mapped_column(
        Text
    )