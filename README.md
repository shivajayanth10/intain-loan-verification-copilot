# Intain Loan Verification Copilot

A full-stack loan data verification application built for the Intain FinTech challenge.

The application imports loan tapes, validates loan records using deterministic rules, creates traceable exceptions, provides AI-assisted reviewer guidance, supports human verification, generates SHA-256 record hashes, and maintains an audit trail.

## Technology Stack

- React
- Vite
- FastAPI
- SQLAlchemy
- SQLite

## Core Workflow

1. Import a CSV loan tape.
2. Validate loan records using deterministic validation rules.
3. Identify validation failures and classify exceptions by severity.
4. Open individual loan records for detailed inspection.
5. Generate AI-assisted review recommendations.
6. Review and resolve exceptions.
7. Verify eligible loan records through human reviewer action.
8. Generate a SHA-256 hash for the verified record.
9. Record verification and exception activity in the audit trail.

AI recommendations are advisory only. Deterministic validation remains the source of truth, and human review is required before verification.

## Main Features

### Loan Data Ingestion
Upload a CSV loan tape and process the records through the validation pipeline.

### Deterministic Validation
The application checks rules such as:

- Required fields
- Date validity and ordering
- Numeric values
- Principal and balance limits
- Payment status
- Days-past-due consistency
- Borrower state codes
- Interest-rate ranges
- Document status
- Duplicate loan IDs
- Stale records

### Exception Management
Validation failures are converted into traceable exceptions with severity, field information, and remediation messaging.

### AI-Assisted Review
The AI review layer summarizes validation failures, explains the issue, and suggests a reviewer correction. It does not silently change loan data.

### Human Verification
Eligible loans can be verified by a reviewer after validation checks pass.

### Verified Records
Verified records contain verification status, reviewer decision, timestamp, canonical loan data, and a SHA-256 record hash.

### Audit Trail
Reviewer and exception activity is recorded for traceability.

## Demo Data

Sample loan tape:

`data/test_loan_tape.csv`

The sample contains both valid and intentionally invalid records.

### Example Records

**LN1001**

A clean loan record used to demonstrate successful validation and human verification.

**LN1007**

A record containing an invalid borrower state code used to demonstrate validation failure and AI-assisted review.

## Running the Backend

From the project root:

```powershell
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload
