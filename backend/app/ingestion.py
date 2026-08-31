import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from .models import (
    ImportBatch,
    Loan,
    ValidationResult,
    ExceptionRecord,
)

from .validation import validate_loan


# =========================================================
# Parsing helpers
# =========================================================

def parse_date(value):
    """
    Convert common CSV date formats into a Python date.
    """
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    formats = [
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
    ]

    for date_format in formats:
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            continue

    raise ValueError(f"Invalid date format: {value}")


def parse_datetime(value):
    """
    Convert common timestamp formats into a Python datetime.
    """
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ]

    for datetime_format in formats:
        try:
            return datetime.strptime(value, datetime_format)
        except ValueError:
            continue

    raise ValueError(f"Invalid timestamp format: {value}")


def parse_decimal(value):
    """
    Convert a CSV value into Decimal.
    """
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    try:
        return Decimal(value.replace(",", ""))
    except InvalidOperation:
        raise ValueError(f"Invalid numeric value: {value}")


def parse_integer(value):
    """
    Convert a CSV value into integer.
    """
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    try:
        return int(value)
    except ValueError:
        raise ValueError(f"Invalid integer value: {value}")


def clean_value(value):
    """
    Normalize empty CSV strings to None.
    """
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    return value


# =========================================================
# Build Loan object from CSV row
# =========================================================

def build_loan_from_row(row, import_id):
    """
    Convert one CSV row into a Loan SQLAlchemy object.
    """

    loan_id = clean_value(row.get("loan_id"))

    if not loan_id:
        raise ValueError("loan_id is missing")

    return Loan(
        loan_id=loan_id,

        borrower_id=clean_value(
            row.get("borrower_id")
        ),

        loan_type=clean_value(
            row.get("loan_type")
        ),

        origination_date=parse_date(
            row.get("origination_date")
        ),

        maturity_date=parse_date(
            row.get("maturity_date")
        ),

        original_principal=parse_decimal(
            row.get("original_principal")
        ),

        current_balance=parse_decimal(
            row.get("current_balance")
        ),

        interest_rate=parse_decimal(
            row.get("interest_rate")
        ),

        term_months=parse_integer(
            row.get("term_months")
        ),

        borrower_state=clean_value(
            row.get("borrower_state")
        ),

        loan_purpose=clean_value(
            row.get("loan_purpose")
        ),

        credit_grade=clean_value(
            row.get("credit_grade")
        ),

        employment_length=clean_value(
            row.get("employment_length")
        ),

        income_band=clean_value(
            row.get("income_band")
        ),

        payment_status=clean_value(
            row.get("payment_status")
        ),

        days_past_due=parse_integer(
            row.get("days_past_due")
        ),

        servicer_name=clean_value(
            row.get("servicer_name")
        ),

        last_payment_date=parse_date(
            row.get("last_payment_date")
        ),

        last_updated_at=parse_datetime(
            row.get("last_updated_at")
        ),

        document_status=clean_value(
            row.get("document_status")
        ),

        source_system=clean_value(
            row.get("source_system")
        ),

        import_id=import_id,
    )


# =========================================================
# CSV Import
# =========================================================

def import_csv(
    db: Session,
    filename: str,
    file_content: bytes,
):
    """
    Import a CSV loan tape into the database.

    Each CSV row is processed independently.

    A validation failure does NOT make the import row fail.
    Instead, the loan is stored with validation results and
    exception records.

    A true import/database/parsing error causes only that
    row to fail.
    """

    # -----------------------------------------------------
    # 1. Decode CSV
    # -----------------------------------------------------

    try:
        text = file_content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError(
            "CSV file must be UTF-8 encoded."
        )

    reader = csv.DictReader(
        io.StringIO(text)
    )

    if not reader.fieldnames:
        raise ValueError(
            "CSV file contains no header row."
        )

    # Normalize header names
    reader.fieldnames = [
        field.strip()
        if field is not None
        else field
        for field in reader.fieldnames
    ]

    # -----------------------------------------------------
    # 2. Required CSV columns
    # -----------------------------------------------------

    required_columns = {
        "loan_id",
        "borrower_id",
        "origination_date",
        "maturity_date",
        "original_principal",
        "current_balance",
        "payment_status",
        "document_status",
    }

    actual_columns = set(
        reader.fieldnames
    )

    missing_columns = (
        required_columns - actual_columns
    )

    if missing_columns:
        raise ValueError(
            "CSV is missing required columns: "
            + ", ".join(
                sorted(missing_columns)
            )
        )

    # -----------------------------------------------------
    # 3. Read rows
    # -----------------------------------------------------

    rows = list(reader)

    # -----------------------------------------------------
    # 4. Create ImportBatch
    # -----------------------------------------------------

    import_batch = ImportBatch(
        filename=filename,
        source_system="CSV_UPLOAD",
        total_rows=len(rows),
        successful_rows=0,
        failed_rows=0,
        status="processing",
    )

    db.add(import_batch)

    # Flush so import_batch.id is available
    db.flush()

    import_id = import_batch.id

    # -----------------------------------------------------
    # 5. Counters and result collection
    # -----------------------------------------------------

    successful_rows = 0
    failed_rows = 0

    import_results = []

    # Track duplicate loan IDs inside this upload
    seen_loan_ids = set()

    # -----------------------------------------------------
    # 6. Process every CSV row
    # -----------------------------------------------------

    for row_number, row in enumerate(
        rows,
        start=2,
    ):

        loan_id = clean_value(
            row.get("loan_id")
        )

        try:

            # -------------------------------------------------
            # Check loan ID before database work
            # -------------------------------------------------

            if not loan_id:
                raise ValueError(
                    "loan_id is missing"
                )

            if loan_id in seen_loan_ids:
                raise ValueError(
                    f"Duplicate loan_id '{loan_id}' "
                    "in uploaded file."
                )

            seen_loan_ids.add(loan_id)

            # -------------------------------------------------
            # Check whether this loan already exists in database
            # -------------------------------------------------

            existing_loan = (
                db.query(Loan)
                .filter(Loan.loan_id == loan_id)
                .first()
            )

            if existing_loan:
                raise ValueError(
                    f"Loan '{loan_id}' already exists in the database."
                )

            # -------------------------------------------------
            # Use a SAVEPOINT for this individual row
            # -------------------------------------------------

            with db.begin_nested():

                # ---------------------------------------------
                # Build Loan object
                # ---------------------------------------------

                loan = build_loan_from_row(
                    row=row,
                    import_id=import_id,
                )

                # ---------------------------------------------
                # Insert Loan
                # ---------------------------------------------

                db.add(loan)

                # Flush so loan.id becomes available
                db.flush()

                # ---------------------------------------------
                # Run validation engine
                # ---------------------------------------------

                validation_results = validate_loan(
    loan,
    db=db,
)

                # ---------------------------------------------
                # Determine whether validation failed
                # ---------------------------------------------

                has_failures = any(
                    not result["passed"]
                    for result in validation_results
                )

                # ---------------------------------------------
                # Store ALL validation results
                # ---------------------------------------------

                for result in validation_results:

                    validation_record = ValidationResult(
                        loan_id=loan.id,
                        rule_code=result["rule_code"],
                        rule_name=result["rule_name"],
                        passed=result["passed"],
                        severity=result["severity"],
                        message=result["message"],
                    )

                    db.add(
                        validation_record
                    )

                    # -----------------------------------------
                    # Create exception ONLY for failed rules
                    # -----------------------------------------

                    if not result["passed"]:

                        exception_record = ExceptionRecord(
                            loan_id=loan.id,
                            exception_type=result["rule_code"],
                            severity=result["severity"],
                            status="open",
                            field_name=None,
                            message=result["message"],
                        )

                        db.add(
                            exception_record
                        )

                # ---------------------------------------------
                # Flush validation records and exceptions
                # ---------------------------------------------

                db.flush()

                # ---------------------------------------------
                # Determine row status
                # ---------------------------------------------

                if has_failures:
                    row_status = "validation_failed"
                else:
                    row_status = "validated"

            # -------------------------------------------------
            # SAVEPOINT succeeded
            # -------------------------------------------------

            successful_rows += 1

            import_results.append(
                {
                    "row": row_number,
                    "loan_id": loan_id,
                    "status": row_status,
                    "validation": validation_results,
                }
            )

        except Exception as error:

            # -------------------------------------------------
            # Only this row failed.
            #
            # The SAVEPOINT has already rolled back its
            # database changes.
            #
            # Do NOT call db.rollback() here because that
            # would roll back the ImportBatch and successful
            # rows as well.
            # -------------------------------------------------

            failed_rows += 1

            import_results.append(
                {
                    "row": row_number,
                    "loan_id": loan_id,
                    "status": "import_failed",
                    "error": str(error),
                }
            )

    # ---------------------------------------------------------
    # 7. Update final ImportBatch statistics
    # ---------------------------------------------------------

    import_batch.successful_rows = (
        successful_rows
    )

    import_batch.failed_rows = (
        failed_rows
    )

    # ---------------------------------------------------------
    # 8. Determine final import status
    # ---------------------------------------------------------

    if len(rows) == 0:
        import_batch.status = "completed"

    elif failed_rows == len(rows):
        import_batch.status = "failed"

    elif failed_rows > 0:
        import_batch.status = (
            "completed_with_errors"
        )

    else:
        import_batch.status = "completed"

    # ---------------------------------------------------------
    # 9. Commit the entire import
    # ---------------------------------------------------------

    db.commit()

    # ---------------------------------------------------------
    # 10. Return import summary
    # ---------------------------------------------------------

    return {
        "import_id": import_batch.id,
        "filename": filename,
        "total_rows": len(rows),
        "successful_rows": successful_rows,
        "failed_rows": failed_rows,
        "status": import_batch.status,
        "rows": import_results,
    }