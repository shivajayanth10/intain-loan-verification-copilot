from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import hashlib
import json
from .database import SessionLocal
from .models import (
    Loan,
    ExceptionRecord,
    AuditLog,
    VerifiedLoan,
)


router = APIRouter()


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# ============================================================
# LOANS
# ============================================================

@router.get("/loans")
def get_loans(
    db: Session = Depends(get_db),
):
    loans = (
        db.query(Loan)
        .order_by(Loan.id.desc())
        .all()
    )

    return {
        "total": len(loans),
        "loans": [
            {
                "id": loan.id,
                "loan_id": loan.loan_id,
                "borrower_id": loan.borrower_id,
                "loan_type": loan.loan_type,
                "original_principal": loan.original_principal,
                "current_balance": loan.current_balance,
                "interest_rate": loan.interest_rate,
                "borrower_state": loan.borrower_state,
                "payment_status": loan.payment_status,
                "days_past_due": loan.days_past_due,
                "document_status": loan.document_status,
                "source_system": loan.source_system,
                "import_id": loan.import_id,
            }
            for loan in loans
        ],
    }


# ============================================================
# EXCEPTIONS
# ============================================================

@router.get("/exceptions")
def get_exceptions(
    db: Session = Depends(get_db),
):
    exceptions = (
        db.query(ExceptionRecord)
        .filter(ExceptionRecord.status == "open")
        .order_by(ExceptionRecord.id.desc())
        .all()
    )

    return {
        "total": len(exceptions),
        "exceptions": [
            {
                "id": exception.id,
                "loan_id": exception.loan_id,
                "exception_type": exception.exception_type,
                "severity": exception.severity,
                "status": exception.status,
                "field_name": exception.field_name,
                "message": exception.message,
                "created_at": exception.created_at,
            }
            for exception in exceptions
        ],
    }


# ============================================================
# SINGLE LOAN
# ============================================================

@router.get("/loans/{loan_id}")
def get_loan(
    loan_id: str,
    db: Session = Depends(get_db),
):
    loan = (
        db.query(Loan)
        .filter(Loan.loan_id == loan_id)
        .order_by(Loan.id.desc())
        .first()
    )

    if not loan:
        raise HTTPException(
            status_code=404,
            detail=f"Loan {loan_id} not found.",
        )

    return {
        "id": loan.id,
        "loan_id": loan.loan_id,
        "borrower_id": loan.borrower_id,
        "loan_type": loan.loan_type,
        "origination_date": loan.origination_date,
        "maturity_date": loan.maturity_date,
        "original_principal": loan.original_principal,
        "current_balance": loan.current_balance,
        "interest_rate": loan.interest_rate,
        "term_months": loan.term_months,
        "borrower_state": loan.borrower_state,
        "loan_purpose": loan.loan_purpose,
        "credit_grade": loan.credit_grade,
        "employment_length": loan.employment_length,
        "income_band": loan.income_band,
        "payment_status": loan.payment_status,
        "days_past_due": loan.days_past_due,
        "servicer_name": loan.servicer_name,
        "last_payment_date": loan.last_payment_date,
        "last_updated_at": loan.last_updated_at,
        "document_status": loan.document_status,
        "source_system": loan.source_system,
        "import_id": loan.import_id,
        "validation_results": [
            {
                "rule_code": result.rule_code,
                "rule_name": result.rule_name,
                "passed": result.passed,
                "severity": result.severity,
                "message": result.message,
                "checked_at": result.checked_at,
            }
            for result in loan.validation_results
        ],
        "exceptions": [
            {
                "id": exception.id,
                "exception_type": exception.exception_type,
                "severity": exception.severity,
                "status": exception.status,
                "field_name": exception.field_name,
                "message": exception.message,
                "created_at": exception.created_at,
                "resolved_at": exception.resolved_at,
            }
            for exception in loan.exceptions
        ],
    }


# ============================================================
# RESOLVE EXCEPTION
# ============================================================

@router.patch("/exceptions/{exception_id}/resolve")
def resolve_exception(
    exception_id: int,
    db: Session = Depends(get_db),
):
    exception = (
        db.query(ExceptionRecord)
        .filter(ExceptionRecord.id == exception_id)
        .first()
    )

    if not exception:
        raise HTTPException(
            status_code=404,
            detail=f"Exception {exception_id} not found.",
        )

    if exception.status == "resolved":
        return {
            "message": "Exception is already resolved.",
            "exception_id": exception.id,
            "loan_id": exception.loan_id,
            "exception_type": exception.exception_type,
            "severity": exception.severity,
            "status": exception.status,
            "resolved_at": exception.resolved_at,
        }

    # Mark exception as resolved
    resolved_at = datetime.utcnow()

    exception.status = "resolved"
    exception.resolved_at = resolved_at

    # Create audit trail record
    audit_log = AuditLog(
        loan_id=exception.loan_id,
        user_id=None,
        action="exception_resolved",
        details=(
            f"Resolved {exception.exception_type} exception "
            f"#{exception.id}: {exception.message}"
        ),
        created_at=resolved_at,
    )

    db.add(audit_log)

    try:
        db.commit()
    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Could not resolve exception.",
        )

    return {
        "message": "Exception resolved successfully.",
        "exception_id": exception.id,
        "loan_id": exception.loan_id,
        "exception_type": exception.exception_type,
        "severity": exception.severity,
        "status": exception.status,
        "resolved_at": exception.resolved_at,
    }


# ============================================================
# AUDIT TRAIL
# ============================================================

@router.get("/audit-logs")
def get_audit_logs(
    db: Session = Depends(get_db),
):
    logs = (
        db.query(AuditLog)
        .order_by(AuditLog.id.desc())
        .all()
    )

    return {
        "total": len(logs),
        "audit_logs": [
            {
                "id": log.id,
                "loan_id": log.loan_id,
                "user_id": log.user_id,
                "action": log.action,
                "details": log.details,
                "created_at": log.created_at,
            }
            for log in logs
        ],
    }
# ============================================================
# VERIFIED LOANS
# ============================================================

@router.get("/verified-loans")
def get_verified_loans(
    db: Session = Depends(get_db),
):
    verified_loans = (
        db.query(VerifiedLoan)
        .order_by(VerifiedLoan.id.desc())
        .all()
    )

    return {
        "total": len(verified_loans),
        "verified_loans": [
            {
                "id": verified.id,
                "loan_id": verified.loan_id,
                "source_file": verified.source_file,
                "validation_status": verified.validation_status,
                "reviewer_decision": verified.reviewer_decision,
                "ai_recommendation": verified.ai_recommendation,
                "verified_at": verified.verified_at,
                "verified_by": verified.verified_by,
                "record_hash": verified.record_hash,
            }
            for verified in verified_loans
        ],
    }


@router.get("/verified-loans/{loan_id}")
def get_verified_loan(
    loan_id: str,
    db: Session = Depends(get_db),
):
    verified = (
        db.query(VerifiedLoan)
        .filter(VerifiedLoan.loan_id == loan_id)
        .order_by(VerifiedLoan.id.desc())
        .first()
    )

    if not verified:
        raise HTTPException(
            status_code=404,
            detail=f"Verified loan {loan_id} not found.",
        )

    return {
        "id": verified.id,
        "loan_id": verified.loan_id,
        "source_file": verified.source_file,
        "validation_status": verified.validation_status,
        "reviewer_decision": verified.reviewer_decision,
        "ai_recommendation": verified.ai_recommendation,
        "verified_at": verified.verified_at,
        "verified_by": verified.verified_by,
        "record_hash": verified.record_hash,
        "canonical_data": json.loads(verified.canonical_data),
    }


@router.get("/summary")
def get_summary(
    db: Session = Depends(get_db),
):
    total_loans = db.query(Loan).count()

    open_exceptions = (
        db.query(ExceptionRecord)
        .filter(ExceptionRecord.status == "open")
        .count()
    )

    high_severity = (
        db.query(ExceptionRecord)
        .filter(
            ExceptionRecord.status == "open",
            ExceptionRecord.severity == "high",
        )
        .count()
    )

    verified_count = db.query(VerifiedLoan).count()

    return {
        "total_loans": total_loans,
        "open_exceptions": open_exceptions,
        "high_severity_exceptions": high_severity,
        "verified_loans": verified_count,
    }
# ============================================================
# CREATE VERIFIED LOAN
# ============================================================

# ============================================================
# AI REVIEW ASSISTANT
# ============================================================

@router.get("/loans/{loan_id}/ai-review")
def ai_review_loan(
    loan_id: str,
    db: Session = Depends(get_db),
):
    loan = (
        db.query(Loan)
        .filter(Loan.loan_id == loan_id)
        .order_by(Loan.id.desc())
        .first()
    )

    if not loan:
        raise HTTPException(
            status_code=404,
            detail=f"Loan {loan_id} not found.",
        )

    failed_results = [
        result
        for result in loan.validation_results
        if not result.passed
    ]

    recommendations = []

    for result in failed_results:
        if result.rule_code == "NEGATIVE_PRINCIPAL":
            recommendation = {
                "rule_code": result.rule_code,
                "severity": result.severity,
                "explanation": (
                    "The original principal is negative, "
                    "which is not a valid loan principal value."
                ),
                "suggested_correction": (
                    "Review the source loan tape and correct "
                    "the original principal to the intended "
                    "positive value."
                ),
                "reviewer_note": (
                    "Principal value requires source-document "
                    "review before verification."
                ),
            }

        elif result.rule_code == "BALANCE_LIMIT":
            recommendation = {
                "rule_code": result.rule_code,
                "severity": result.severity,
                "explanation": (
                    "The current balance is greater than the "
                    "original principal."
                ),
                "suggested_correction": (
                    "Compare the current balance with the "
                    "servicing record and correct the "
                    "inconsistent value."
                ),
                "reviewer_note": (
                    "Balance relationship should be confirmed "
                    "against the source record."
                ),
            }

        elif result.rule_code == "DATE_ORDER":
            recommendation = {
                "rule_code": result.rule_code,
                "severity": result.severity,
                "explanation": (
                    "The maturity date occurs before the "
                    "origination date."
                ),
                "suggested_correction": (
                    "Review both dates in the source record "
                    "and correct the date ordering."
                ),
                "reviewer_note": (
                    "Date inconsistency requires reviewer "
                    "confirmation."
                ),
            }

        elif result.rule_code == "STATE_CODE":
            recommendation = {
                "rule_code": result.rule_code,
                "severity": result.severity,
                "explanation": (
                    "The borrower state value is not a valid "
                    "state code."
                ),
                "suggested_correction": (
                    "Verify the borrower's address in the "
                    "source record and replace the invalid "
                    "state code with the correct value."
                ),
                "reviewer_note": (
                    "State information should be confirmed "
                    "against the source record."
                ),
            }

        elif result.rule_code == "REQUIRED_FIELD":
            recommendation = {
                "rule_code": result.rule_code,
                "severity": result.severity,
                "explanation": (
                    "A required loan field is missing from "
                    "the imported record."
                ),
                "suggested_correction": (
                    "Retrieve the missing value from the "
                    "source document or servicing record."
                ),
                "reviewer_note": (
                    "Required field must be reviewed before "
                    "verification."
                ),
            }

        elif result.rule_code == "STATUS_DPD_CONSISTENCY":
            recommendation = {
                "rule_code": result.rule_code,
                "severity": result.severity,
                "explanation": (
                    "Payment status and days-past-due "
                    "information are inconsistent."
                ),
                "suggested_correction": (
                    "Compare payment status and DPD against "
                    "the latest servicing record."
                ),
                "reviewer_note": (
                    "Servicing status should be confirmed "
                    "before approval."
                ),
            }

        elif result.rule_code == "DOCUMENT_STATUS":
            recommendation = {
                "rule_code": result.rule_code,
                "severity": result.severity,
                "explanation": (
                    "The required document status is missing "
                    "or incomplete."
                ),
                "suggested_correction": (
                    "Review the document manifest and update "
                    "the document status."
                ),
                "reviewer_note": (
                    "Document availability should be confirmed "
                    "before verification."
                ),
            }

        else:
            recommendation = {
                "rule_code": result.rule_code,
                "severity": result.severity,
                "explanation": result.message,
                "suggested_correction": (
                    "Review the validation failure against "
                    "the source record and determine the "
                    "correct value."
                ),
                "reviewer_note": (
                    "Manual review is recommended before "
                    "verification."
                ),
            }

        recommendations.append(recommendation)

    if not recommendations:
        overall_recommendation = "approve"
        summary = (
            "All validation rules currently pass. "
            "The loan is eligible for reviewer approval."
        )
        reviewer_note = (
            "No failed validation rules were detected. "
            "Reviewer retains final approval authority."
        )
    else:
        overall_recommendation = "review_required"

        severity_order = {
            "high": 3,
            "medium": 2,
            "low": 1,
            "info": 0,
        }

        highest_severity = max(
            recommendations,
            key=lambda item: severity_order.get(
                item["severity"].lower(),
                0,
            ),
        )["severity"]

        summary = (
            f"{len(recommendations)} validation rule(s) failed. "
            f"Highest severity: {highest_severity}."
        )

        reviewer_note = (
            "AI recommendations are advisory only. "
            "Review the suggested corrections against the "
            "source record before making a human decision."
        )

    return {
        "loan_id": loan.loan_id,
        "recommendation": overall_recommendation,
        "summary": summary,
        "reviewer_note": reviewer_note,
        "validation_failures_reviewed": len(recommendations),
        "recommendations": recommendations,
    }
# ============================================================
# VERIFY LOAN
# ============================================================

@router.post("/loans/{loan_id}/verify")
def verify_loan(
    loan_id: str,
    db: Session = Depends(get_db),
):
    import hashlib
    import json

    loan = (
        db.query(Loan)
        .filter(Loan.loan_id == loan_id)
        .order_by(Loan.id.desc())
        .first()
    )

    if not loan:
        raise HTTPException(
            status_code=404,
            detail=f"Loan {loan_id} not found.",
        )

    # A loan can only be verified when all validation
    # rules currently pass.
    failed_results = [
        result
        for result in loan.validation_results
        if not result.passed
    ]

    if failed_results:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Loan cannot be verified while validation failures remain.",
                "loan_id": loan_id,
                "failed_rules": [
                    {
                        "rule_code": result.rule_code,
                        "severity": result.severity,
                        "message": result.message,
                    }
                    for result in failed_results
                ],
            },
        )

    canonical_data = {
        "borrower_id": loan.borrower_id,
        "borrower_state": loan.borrower_state,
        "credit_grade": loan.credit_grade,
        "current_balance": f"{loan.current_balance:.2f}",
        "days_past_due": loan.days_past_due,
        "document_status": loan.document_status,
        "employment_length": loan.employment_length,
        "income_band": loan.income_band,
        "interest_rate": f"{loan.interest_rate:.4f}",
        "last_payment_date": (
            loan.last_payment_date.isoformat()
            if loan.last_payment_date
            else None
        ),
        "last_updated_at": (
            loan.last_updated_at.isoformat()
            if loan.last_updated_at
            else None
        ),
        "loan_id": loan.loan_id,
        "loan_purpose": loan.loan_purpose,
        "loan_type": loan.loan_type,
        "maturity_date": loan.maturity_date.isoformat(),
        "original_principal": f"{loan.original_principal:.2f}",
        "origination_date": loan.origination_date.isoformat(),
        "payment_status": loan.payment_status,
        "servicer_name": loan.servicer_name,
        "source_system": loan.source_system,
        "term_months": loan.term_months,
    }

    canonical_json = json.dumps(
        canonical_data,
        sort_keys=True,
        separators=(",", ":"),
    )

    record_hash = hashlib.sha256(
        canonical_json.encode("utf-8")
    ).hexdigest()

    existing = (
        db.query(VerifiedLoan)
        .filter(VerifiedLoan.loan_id == loan.loan_id)
        .first()
    )

    if existing:
        return {
            "message": "Loan is already verified.",
            "loan_id": loan.loan_id,
            "validation_status": existing.validation_status,
            "reviewer_decision": existing.reviewer_decision,
            "verified_at": existing.verified_at,
            "record_hash": existing.record_hash,
        }

    verified_at = datetime.utcnow()

    verified = VerifiedLoan(
        loan_id=loan.loan_id,
        source_file="test_loan_tape.csv",
        validation_status="verified",
        reviewer_decision="approved",
        ai_recommendation=None,
        verified_at=verified_at,
        verified_by=None,
        record_hash=record_hash,
        canonical_data=canonical_json,
    )

    db.add(verified)

    audit_log = AuditLog(
        loan_id=loan.id,
        user_id=None,
        action="verified_record_created",
        details=(
            f"Verified loan {loan.loan_id}. "
            f"SHA-256 record hash: {record_hash}"
        ),
        created_at=verified_at,
    )

    db.add(audit_log)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not create verified loan record.",
        )

    return {
        "message": "Loan verified successfully.",
        "loan_id": loan.loan_id,
        "validation_status": "verified",
        "reviewer_decision": "approved",
        "verified_at": verified_at,
        "record_hash": record_hash,
    }