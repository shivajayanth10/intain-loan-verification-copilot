from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from .models import Loan


VALID_PAYMENT_STATUSES = {
    "current",
    "delinquent",
    "late",
    "default",
    "closed",
    "paid",
}

VALID_STATE_CODES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE",
    "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS",
    "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS",
    "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY",
    "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV",
    "WI", "WY",
}


def _result(
    rule_code,
    rule_name,
    passed,
    severity,
    message,
):
    return {
        "rule_code": rule_code,
        "rule_name": rule_name,
        "passed": passed,
        "severity": severity,
        "message": message,
    }


def validate_loan(loan, db: Session | None = None):
    """
    Run all validation rules against one Loan object.

    Returns a list of dictionaries containing:
        rule_code
        rule_name
        passed
        severity
        message
    """

    results = []

    # ---------------------------------------------------------
    # 1. Required fields
    # ---------------------------------------------------------

    required_fields = {
        "loan_id": loan.loan_id,
        "borrower_id": loan.borrower_id,
        "loan_type": loan.loan_type,
        "origination_date": loan.origination_date,
        "maturity_date": loan.maturity_date,
        "original_principal": loan.original_principal,
        "current_balance": loan.current_balance,
        "interest_rate": loan.interest_rate,
        "payment_status": loan.payment_status,
        "document_status": loan.document_status,
    }

    missing_fields = [
        field_name
        for field_name, value in required_fields.items()
        if value is None or str(value).strip() == ""
    ]

    if missing_fields:
        results.append(
            _result(
                "REQUIRED_FIELD",
                "Required field present",
                False,
                "high",
                "Required field(s) missing: "
                + ", ".join(missing_fields)
                + ".",
            )
        )
    else:
        results.append(
            _result(
                "REQUIRED_FIELD",
                "Required field present",
                True,
                "info",
                "All required fields are present.",
            )
        )

    # ---------------------------------------------------------
    # 2. Valid dates
    # ---------------------------------------------------------

    origination_valid = (
        loan.origination_date is None
        or isinstance(loan.origination_date, date)
    )

    maturity_valid = (
        loan.maturity_date is None
        or isinstance(loan.maturity_date, date)
    )

    if origination_valid and maturity_valid:
        results.append(
            _result(
                "VALID_DATES",
                "Valid dates",
                True,
                "info",
                "Loan dates are valid.",
            )
        )
    else:
        results.append(
            _result(
                "VALID_DATES",
                "Valid dates",
                False,
                "high",
                "One or more loan dates are invalid.",
            )
        )

    # ---------------------------------------------------------
    # 3. Maturity date after origination date
    # ---------------------------------------------------------

    if loan.origination_date and loan.maturity_date:
        if loan.maturity_date > loan.origination_date:
            results.append(
                _result(
                    "DATE_ORDER",
                    "Maturity after origination",
                    True,
                    "info",
                    "Date sequence is valid.",
                )
            )
        else:
            results.append(
                _result(
                    "DATE_ORDER",
                    "Maturity after origination",
                    False,
                    "high",
                    "Maturity date must be after origination date.",
                )
            )
    else:
        results.append(
            _result(
                "DATE_ORDER",
                "Maturity after origination",
                False,
                "high",
                "Origination and maturity dates are required.",
            )
        )

    # ---------------------------------------------------------
    # 4. Numeric values
    # ---------------------------------------------------------

    numeric_fields = {
        "original_principal": loan.original_principal,
        "current_balance": loan.current_balance,
        "interest_rate": loan.interest_rate,
        "term_months": loan.term_months,
        "days_past_due": loan.days_past_due,
    }

    invalid_numeric_fields = []

    for field_name, value in numeric_fields.items():
        if value is None:
            continue

        try:
            Decimal(str(value))
        except Exception:
            invalid_numeric_fields.append(field_name)

    if invalid_numeric_fields:
        results.append(
            _result(
                "NUMERIC_VALUES",
                "Valid numeric values",
                False,
                "high",
                "Invalid numeric value(s): "
                + ", ".join(invalid_numeric_fields)
                + ".",
            )
        )
    else:
        results.append(
            _result(
                "NUMERIC_VALUES",
                "Valid numeric values",
                True,
                "info",
                "Numeric values are valid.",
            )
        )

    # ---------------------------------------------------------
    # 5. Non-negative principal
    # ---------------------------------------------------------

    if loan.original_principal is None:
        results.append(
            _result(
                "NEGATIVE_PRINCIPAL",
                "Non-negative principal",
                False,
                "high",
                "Original principal is required.",
            )
        )
    elif loan.original_principal >= 0:
        results.append(
            _result(
                "NEGATIVE_PRINCIPAL",
                "Non-negative principal",
                True,
                "info",
                "Original principal is valid.",
            )
        )
    else:
        results.append(
            _result(
                "NEGATIVE_PRINCIPAL",
                "Non-negative principal",
                False,
                "high",
                "Original principal cannot be negative.",
            )
        )

    # ---------------------------------------------------------
    # 6. Non-negative current balance
    # ---------------------------------------------------------

    if loan.current_balance is None:
        results.append(
            _result(
                "NEGATIVE_BALANCE",
                "Non-negative balance",
                False,
                "high",
                "Current balance is required.",
            )
        )
    elif loan.current_balance >= 0:
        results.append(
            _result(
                "NEGATIVE_BALANCE",
                "Non-negative balance",
                True,
                "info",
                "Current balance is valid.",
            )
        )
    else:
        results.append(
            _result(
                "NEGATIVE_BALANCE",
                "Non-negative balance",
                False,
                "high",
                "Current balance cannot be negative.",
            )
        )

    # ---------------------------------------------------------
    # 7. Balance cannot exceed principal
    # ---------------------------------------------------------

    if (
        loan.original_principal is not None
        and loan.current_balance is not None
    ):
        if loan.current_balance <= loan.original_principal:
            results.append(
                _result(
                    "BALANCE_LIMIT",
                    "Balance does not exceed principal",
                    True,
                    "info",
                    "Current balance is within the allowed principal amount.",
                )
            )
        else:
            results.append(
                _result(
                    "BALANCE_LIMIT",
                    "Balance does not exceed principal",
                    False,
                    "high",
                    "Current balance is greater than original principal.",
                )
            )
    else:
        results.append(
            _result(
                "BALANCE_LIMIT",
                "Balance does not exceed principal",
                False,
                "high",
                "Principal and current balance are required.",
            )
        )

    # ---------------------------------------------------------
    # 8. Valid payment status
    # ---------------------------------------------------------

    payment_status = (
        str(loan.payment_status).strip().lower()
        if loan.payment_status is not None
        else ""
    )

    if payment_status in VALID_PAYMENT_STATUSES:
        results.append(
            _result(
                "PAYMENT_STATUS",
                "Valid payment status",
                True,
                "info",
                "Payment status is recognized.",
            )
        )
    else:
        results.append(
            _result(
                "PAYMENT_STATUS",
                "Valid payment status",
                False,
                "high",
                "Invalid payment status."
                if payment_status
                else "Payment status is missing.",
            )
        )

    # ---------------------------------------------------------
    # 9. Payment status vs DPD consistency
    # ---------------------------------------------------------

    dpd = loan.days_past_due

    if dpd is None:
        results.append(
            _result(
                "STATUS_DPD_CONSISTENCY",
                "Payment status matches delinquency",
                False,
                "medium",
                "Days past due is missing.",
            )
        )
    elif dpd < 0:
        results.append(
            _result(
                "STATUS_DPD_CONSISTENCY",
                "Payment status matches delinquency",
                False,
                "high",
                "Days past due cannot be negative.",
            )
        )
    elif payment_status == "current" and dpd > 0:
        results.append(
            _result(
                "STATUS_DPD_CONSISTENCY",
                "Payment status matches delinquency",
                False,
                "high",
                "Loan is marked current but has days past due.",
            )
        )
    elif payment_status in {
        "delinquent",
        "late",
        "default",
    } and dpd == 0:
        results.append(
            _result(
                "STATUS_DPD_CONSISTENCY",
                "Payment status matches delinquency",
                False,
                "medium",
                "Loan is marked delinquent/late/default but days past due is zero.",
            )
        )
    else:
        results.append(
            _result(
                "STATUS_DPD_CONSISTENCY",
                "Payment status matches delinquency",
                True,
                "info",
                "Payment status and days past due are consistent.",
            )
        )

    # ---------------------------------------------------------
    # 10. Valid borrower state
    # ---------------------------------------------------------

    state = (
        str(loan.borrower_state).strip().upper()
        if loan.borrower_state is not None
        else ""
    )

    if state in VALID_STATE_CODES:
        results.append(
            _result(
                "STATE_CODE",
                "Valid state code",
                True,
                "info",
                "Borrower state code is valid.",
            )
        )
    else:
        results.append(
            _result(
                "STATE_CODE",
                "Valid state code",
                False,
                "medium",
                f"Invalid borrower state code '{state}'.",
            )
        )

    # ---------------------------------------------------------
    # 11. Interest rate range
    # ---------------------------------------------------------

    if loan.interest_rate is None:
        results.append(
            _result(
                "INTEREST_RATE_RANGE",
                "Interest rate within expected range",
                False,
                "high",
                "Interest rate is missing.",
            )
        )
    elif 0 <= loan.interest_rate <= 100:
        results.append(
            _result(
                "INTEREST_RATE_RANGE",
                "Interest rate within expected range",
                True,
                "info",
                "Interest rate is within the expected range.",
            )
        )
    else:
        results.append(
            _result(
                "INTEREST_RATE_RANGE",
                "Interest rate within expected range",
                False,
                "high",
                "Interest rate must be between 0 and 100 percent.",
            )
        )

    # ---------------------------------------------------------
    # 12. Document status
    # ---------------------------------------------------------

    document_status = (
        str(loan.document_status).strip()
        if loan.document_status is not None
        else ""
    )

    if document_status:
        results.append(
            _result(
                "DOCUMENT_STATUS",
                "Document status available",
                True,
                "info",
                "Document status is available.",
            )
        )
    else:
        results.append(
            _result(
                "DOCUMENT_STATUS",
                "Document status available",
                False,
                "high",
                "Required document status is missing.",
            )
        )

    # ---------------------------------------------------------
    # 13. Duplicate loan detection
    # ---------------------------------------------------------

    if db is not None and loan.loan_id:
        duplicate_query = (
            db.query(Loan)
            .filter(
                Loan.loan_id == loan.loan_id,
                Loan.id != loan.id,
            )
        )

        duplicate_exists = duplicate_query.first() is not None

        if duplicate_exists:
            results.append(
                _result(
                    "DUPLICATE_LOAN_ID",
                    "Duplicate loan detection",
                    False,
                    "high",
                    f"Duplicate loan ID '{loan.loan_id}' detected.",
                )
            )
        else:
            results.append(
                _result(
                    "DUPLICATE_LOAN_ID",
                    "Duplicate loan detection",
                    True,
                    "info",
                    "Loan ID is unique.",
                )
            )
    else:
        results.append(
            _result(
                "DUPLICATE_LOAN_ID",
                "Duplicate loan detection",
                True,
                "info",
                "Duplicate check completed.",
            )
        )

    # ---------------------------------------------------------
    # 14. Stale record detection
    # ---------------------------------------------------------

    if loan.last_updated_at is None:
        results.append(
            _result(
                "STALE_RECORD",
                "Stale record detection",
                False,
                "medium",
                "Last updated timestamp is missing.",
            )
        )
    else:
        now = datetime.utcnow()

        if loan.last_updated_at < now - timedelta(days=180):
            results.append(
                _result(
                    "STALE_RECORD",
                    "Stale record detection",
                    False,
                    "medium",
                    "Loan record has not been updated within the expected period.",
                )
            )
        else:
            results.append(
                _result(
                    "STALE_RECORD",
                    "Stale record detection",
                    True,
                    "info",
                    "Loan record is sufficiently recent.",
                )
            )

    # ---------------------------------------------------------
    # 15. Closed loan with positive balance
    # ---------------------------------------------------------

    if payment_status == "closed":
        if loan.current_balance is not None and loan.current_balance > 0:
            results.append(
                _result(
                    "CLOSED_BALANCE",
                    "Closed loan balance",
                    False,
                    "high",
                    "Loan is marked closed but still has a positive balance.",
                )
            )
        else:
            results.append(
                _result(
                    "CLOSED_BALANCE",
                    "Closed loan balance",
                    True,
                    "info",
                    "Closed loan has no positive outstanding balance.",
                )
            )
    else:
        results.append(
            _result(
                "CLOSED_BALANCE",
                "Closed loan balance",
                True,
                "info",
                "Closed-loan balance rule does not apply.",
            )
        )

    return results