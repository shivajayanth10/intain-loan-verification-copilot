import { useEffect, useState } from "react";
import "./App.css";

const API = "https://intain-loan-verification-copilot.onrender.com";

function App() {
  const [loans, setLoans] = useState([]);
  const [exceptions, setExceptions] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [selectedLoan, setSelectedLoan] = useState(null);

  const [loading, setLoading] = useState(true);
  const [apiStatus, setApiStatus] = useState("Checking...");

  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [importResult, setImportResult] = useState(null);
  const [resolvingException, setResolvingException] = useState(null);
  const [verifyingLoan, setVerifyingLoan] = useState(null);

const [aiReview, setAiReview] = useState(null);

  

 
 
  const [aiReviewLoading, setAiReviewLoading] = useState(false);

  const loadDashboard = async () => {
    try {
      setLoading(true);

      const [
        healthRes,
        loansRes,
        exceptionsRes,
        auditRes,
      ] = await Promise.all([
        fetch(`${API}/health`),
        fetch(`${API}/loans`),
        fetch(`${API}/exceptions`),
        fetch(`${API}/audit-logs`),
      ]);

      if (
        !healthRes.ok ||
        !loansRes.ok ||
        !exceptionsRes.ok ||
        !auditRes.ok
      ) {
        throw new Error(
          "Backend request failed"
        );
      }

      const health =
        await healthRes.json();

      const loanData =
        await loansRes.json();

      const exceptionData =
        await exceptionsRes.json();

      const auditData =
        await auditRes.json();

      setApiStatus(
        health.status === "healthy"
          ? "Connected"
          : "Unavailable"
      );

      setLoans(
        loanData.loans || []
      );

      setExceptions(
        exceptionData.exceptions || []
      );

      setAuditLogs(
        auditData.audit_logs || []
      );
    } catch (error) {
      console.error(error);
      setApiStatus("Offline");
    } finally {
      setLoading(false);
    }
  };

  const openLoan = async (loanId) => {
    try {
      const response = await fetch(
        `${API}/loans/${loanId}`
      );

      if (!response.ok) {
        throw new Error(
          "Could not load loan"
        );
      }

      const data =
        await response.json();

      setSelectedLoan(data);
      setAiReview(null);
setAiReviewLoading(true);

try {
  const aiResponse = await fetch(
    `${API}/loans/${loanId}/ai-review`
  );

  if (aiResponse.ok) {
    const aiData = await aiResponse.json();
    setAiReview(aiData);
  }
} catch (error) {
  console.error("AI review unavailable:", error);
} finally {
  setAiReviewLoading(false);
}
    } catch (error) {
      console.error(error);

      alert(
        "Could not load loan details."
      );
    }
  };

  const uploadLoanFile = async () => {
    if (!selectedFile) {
      alert(
        "Please select a CSV file first."
      );
      return;
    }

    try {
      setUploading(true);
      setImportResult(null);

      const formData =
        new FormData();

      formData.append(
        "file",
        selectedFile
      );

      const response = await fetch(
        `${API}/import`,
        {
          method: "POST",
          body: formData,
        }
      );

      const data =
        await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "Import failed"
        );
      }

      setImportResult(data);
      setSelectedFile(null);

      await loadDashboard();
    } catch (error) {
      console.error(error);

      alert(
        error.message ||
          "Could not import CSV file."
      );
    } finally {
      setUploading(false);
    }
  };
    const verifyLoan = async (loanId) => {
  try {
    setVerifyingLoan(loanId);

    const response = await fetch(
      `${API}/loans/${loanId}/verify`,
      {
        method: "POST",
      }
    );

    const data = await response.json();

    if (!response.ok) {
  const detail =
    typeof data.detail === "string"
      ? data.detail
      : data.detail?.message ||
        "Loan cannot be verified while validation failures remain.";

  throw new Error(detail);
}

    alert(
      `Loan ${loanId} verified successfully.`
    );

    await loadDashboard();
    await openLoan(loanId);
  } catch (error) {
    console.error(error);

    alert(
      error.message ||
        "Could not verify loan."
    );
  } finally {
    setVerifyingLoan(null);
  }
};

  const resolveException = async (
    exceptionId
  ) => {
    try {
      setResolvingException(
        exceptionId
      );

      const response = await fetch(
        `${API}/exceptions/${exceptionId}/resolve`,
        {
          method: "PATCH",
        }
      );

      const data =
        await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "Could not resolve exception."
        );
      }

      await loadDashboard();

      if (
        selectedLoan &&
        selectedLoan.exceptions?.some(
          (exception) =>
            exception.id ===
            exceptionId
        )
      ) {
        await openLoan(
          selectedLoan.loan_id
        );
      }
    } catch (error) {
      console.error(error);

      alert(
        error.message ||
          "Could not resolve exception."
      );
    } finally {
      setResolvingException(null);
    }
        };


  useEffect(() => {
    loadDashboard();
  }, []);

  const highExceptions =
    exceptions.filter(
      (item) =>
        item.severity === "high"
    ).length;

  const mediumExceptions =
    exceptions.filter(
      (item) =>
        item.severity === "medium"
    ).length;

  const delinquentLoans =
    loans.filter(
      (loan) =>
        loan.payment_status ===
          "delinquent" ||
        loan.days_past_due > 0
    ).length;

  const getLoanDisplayId = (
    databaseLoanId
  ) => {
    const loan = loans.find(
      (item) =>
        item.id === databaseLoanId
    );

    return loan
      ? loan.loan_id
      : `Loan #${databaseLoanId}`;
  };

  const formatAuditAction = (
    action
  ) => {
    if (
      action ===
      "exception_resolved"
    ) {
      return "Exception resolved";
    }

    return action
      .replaceAll("_", " ")
      .replace(
        /\b\w/g,
        (letter) =>
          letter.toUpperCase()
      );
  };

  const formatAuditTime = (
    timestamp
  ) => {
    if (!timestamp) {
      return "Unknown time";
    }

    return new Date(
      timestamp
    ).toLocaleString();
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <div className="brand">
            INTAIN
          </div>

          <div className="product-name">
            Loan Data Verification Copilot
          </div>
        </div>

        <div className="topbar-right">
          <span
            className={`connection-dot ${
              apiStatus ===
              "Connected"
                ? "online"
                : ""
            }`}
          />

          <span>
            {apiStatus}
          </span>

          <button
            className="refresh-btn"
            onClick={
              loadDashboard
            }
          >
            Refresh
          </button>
        </div>
      </header>

      <main className="dashboard">
        <section className="hero">
          <p className="eyebrow">
            PORTFOLIO CONTROL CENTER
          </p>

          <h1>
            Loan Verification Dashboard
          </h1>

          <p className="hero-text">
            Review imported loan data,
            validation results, and
            exceptions from one place.
          </p>
        </section>

        <section className="upload-panel">
          <div className="upload-content">
            <div>
              <p className="eyebrow">
                DATA INGESTION
              </p>

              <h2>
                Import Loan Tape
              </h2>

              <p>
                Upload a CSV loan tape
                to validate records and
                generate traceable
                exceptions.
              </p>
            </div>

            <div className="upload-controls">
              <label className="file-input">
                <input
                  type="file"
                  accept=".csv"
                  onChange={(event) =>
                    setSelectedFile(
                      event.target
                        .files?.[0] ||
                        null
                    )
                  }
                />

                <span>
                  {selectedFile
                    ? selectedFile.name
                    : "Choose CSV file"}
                </span>
              </label>

              <button
                className="upload-btn"
                onClick={
                  uploadLoanFile
                }
                disabled={
                  uploading ||
                  !selectedFile
                }
              >
                {uploading
                  ? "Importing..."
                  : "Import Loan Tape"}
              </button>
            </div>
          </div>

          {importResult && (
            <div className="import-result">
              <div>
                <strong>
                  Import completed
                </strong>

                <span>
                  {importResult.filename}
                </span>
              </div>

              <div className="import-summary">
                <span>
                  <strong>
                    {
                      importResult.total_rows
                    }
                  </strong>
                  Total
                </span>

                <span>
                  <strong>
                    {
                      importResult.successful_rows
                    }
                  </strong>
                  Successful
                </span>

                <span>
                  <strong>
                    {
                      importResult.failed_rows
                    }
                  </strong>
                  Failed
                </span>

                <span>
                  <strong>
                    {
                      importResult.status
                    }
                  </strong>
                  Status
                </span>
              </div>
            </div>
          )}
        </section>

        <section className="stats-grid">
          <div className="stat-card">
            <span>
              Total Loans
            </span>

            <strong>
              {loading
                ? "—"
                : loans.length}
            </strong>

            <small>
              Imported records
            </small>
          </div>

          <div className="stat-card warning">
            <span>
              Open Exceptions
            </span>

            <strong>
              {loading
                ? "—"
                : exceptions.length}
            </strong>

            <small>
              {highExceptions} high
              severity
            </small>
          </div>

          <div className="stat-card danger">
            <span>
              High Severity
            </span>

            <strong>
              {loading
                ? "—"
                : highExceptions}
            </strong>

            <small>
              {mediumExceptions} medium
              severity
            </small>
          </div>

          <div className="stat-card">
            <span>
              Delinquency Signals
            </span>

            <strong>
              {loading
                ? "—"
                : delinquentLoans}
            </strong>

            <small>
              Payment / DPD indicators
            </small>
          </div>
        </section>

        <section className="content-grid">
          <div className="panel">
            <div className="panel-header">
              <div>
                <h2>
                  Loan Portfolio
                </h2>

                <p>
                  Select a loan to
                  inspect validation
                  details.
                </p>
              </div>

              <span className="count-badge">
                {loans.length}
              </span>
            </div>

            {loading ? (
              <div className="empty-state">
                Loading loans...
              </div>
            ) : loans.length ===
              0 ? (
              <div className="empty-state">
                No loans found.
              </div>
            ) : (
              <div className="loan-list">
                {loans.map(
                  (loan) => (
                    <button
                      className="loan-row"
                      key={`${loan.id}-${loan.import_id}`}
                      onClick={() =>
                        openLoan(
                          loan.loan_id
                        )
                      }
                    >
                      <div className="loan-main">
                        <strong>
                          {
                            loan.loan_id
                          }
                        </strong>

                        <span>
                          {loan.loan_type ||
                            "Unknown type"}{" "}
                          ·{" "}
                          {loan.borrower_state ||
                            "N/A"}
                        </span>
                      </div>

                      <div className="loan-balance">
                        <strong>
                          $
                          {Number(
                            loan.current_balance ||
                              0
                          ).toLocaleString()}
                        </strong>

                        <span>
                          {
                            loan.interest_rate
                          }
                          % interest
                        </span>
                      </div>

                      <span
                        className={`status ${
                          loan.payment_status ===
                          "current"
                            ? "current"
                            : "problem"
                        }`}
                      >
                        {
                          loan.payment_status
                        }
                      </span>
                    </button>
                  )
                )}
              </div>
            )}
          </div>

          <div className="panel">
            <div className="panel-header">
              <div>
                <h2>
                  Open Exceptions
                </h2>

                <p>
                  Issues requiring
                  review or remediation.
                </p>
              </div>

              <span className="count-badge">
                {exceptions.length}
              </span>
            </div>

            {exceptions.length ===
            0 ? (
              <div className="empty-state success-state">
                No open exceptions.
              </div>
            ) : (
              <div className="exception-list">
                {exceptions.map(
                  (item) => (
                    <div
                      className="exception-card"
                      key={item.id}
                    >
                      <div className="exception-top">
                        <span
                          className={`severity ${item.severity}`}
                        >
                          {
                            item.severity
                          }
                        </span>

                        <span>
                          #{item.id}
                        </span>
                      </div>

                      <strong>
                        {
                          item.exception_type
                        }
                      </strong>

                      <p>
                        {item.message}
                      </p>

                      <div className="exception-actions">
                        <button
                          className="text-btn"
                          onClick={() =>
                            openLoan(
                              item.loan_id
                            )
                          }
                        >
                          View loan →
                        </button>

                        <button
                          className="resolve-btn"
                          onClick={() =>
                            resolveException(
                              item.id
                            )
                          }
                          disabled={
                            resolvingException ===
                            item.id
                          }
                        >
                          {resolvingException ===
                          item.id
                            ? "Resolving..."
                            : "Resolve"}
                        </button>
                      </div>
                    </div>
                  )
                )}
              </div>
            )}
          </div>
        </section>

        <section className="panel audit-panel">
          <div className="panel-header">
            <div>
              <h2>
                Audit Trail
              </h2>

              <p>
                Traceable record of
                reviewer actions and
                exception changes.
              </p>
            </div>

            <span className="count-badge">
              {auditLogs.length}
            </span>
          </div>

          {auditLogs.length ===
          0 ? (
            <div className="empty-state">
              No audit activity yet.
            </div>
          ) : (
            <div className="audit-list">
              {auditLogs.map(
                (log) => (
                  <div
                    className="audit-row"
                    key={log.id}
                  >
                    <div className="audit-icon">
                      ✓
                    </div>

                    <div className="audit-main">
                      <strong>
                        {formatAuditAction(
                          log.action
                        )}
                      </strong>

                      <span>
                        {getLoanDisplayId(
                          log.loan_id
                        )}
                      </span>

                      <p>
                        {log.details}
                      </p>
                    </div>

                    <div className="audit-time">
                      {formatAuditTime(
                        log.created_at
                      )}
                    </div>
                  </div>
                )
              )}
            </div>
          )}
        </section>
      </main>

      {selectedLoan && (
        <div
          className="modal-backdrop"
          onClick={() =>
            setSelectedLoan(null)
          }
        >
          <div
            className="loan-modal"
            onClick={(event) =>
              event.stopPropagation()
            }
          >
            <div className="modal-header">
              <div>
                <span className="eyebrow">
                  LOAN RECORD
                </span>

                <h2>
                  {
                    selectedLoan.loan_id
                  }
                </h2>
              </div>

              <button
                className="close-btn"
                onClick={() =>
                  setSelectedLoan(null)
                }
              >
                ×
              </button>
            </div>

            <div className="detail-grid">
              <div>
                <span>
                  Borrower
                </span>

                <strong>
                  {
                    selectedLoan.borrower_id ||
                    "N/A"
                  }
                </strong>
              </div>

              <div>
                <span>
                  Loan Type
                </span>

                <strong>
                  {
                    selectedLoan.loan_type ||
                    "N/A"
                  }
                </strong>
              </div>

              <div>
                <span>
                  Principal
                </span>

                <strong>
                  $
                  {Number(
                    selectedLoan.original_principal ||
                      0
                  ).toLocaleString()}
                </strong>
              </div>

              <div>
                <span>
                  Current Balance
                </span>

                <strong>
                  $
                  {Number(
                    selectedLoan.current_balance ||
                      0
                  ).toLocaleString()}
                </strong>
              </div>

              <div>
                <span>
                  Interest Rate
                </span>

                <strong>
                  {
                    selectedLoan.interest_rate
                  }
                  %
                </strong>
              </div>

              <div>
                <span>
                  Payment Status
                </span>

                <strong>
                  {
                    selectedLoan.payment_status
                  }
                </strong>
              </div>

              <div>
                <span>
                  Days Past Due
                </span>

                <strong>
                  {
                    selectedLoan.days_past_due
                  }
                </strong>
              </div>

              <div>
                <span>
                  Document Status
                </span>

                <strong>
                  {
                    selectedLoan.document_status ||
                    "Missing"
                  }
                </strong>
              </div>
            </div>

            <div className="modal-actions">
              <button
                className="verify-btn"
                onClick={() => verifyLoan(selectedLoan.loan_id)}
                disabled={verifyingLoan === selectedLoan.loan_id}
              >
                {verifyingLoan === selectedLoan.loan_id
                  ? "Verifying..."
                  : "Verify Loan"}
              </button>
            </div>

            <div className="validation-section">
              <h3>
                Validation Results
              </h3>

              {selectedLoan.validation_results?.map(
                (
                  result,
                  index
                ) => (
                  <div
                    className={`validation-row ${
                      result.passed
                        ? "passed"
                        : "failed"
                    }`}
                    key={`${result.rule_code}-${index}`}
                  >
                    <div>
                      <strong>
                        {
                          result.rule_name
                        }
                      </strong>

                      <p>
                        {
                          result.message
                        }
                      </p>
                    </div>

                    <span>
                      {result.passed
                        ? "PASS"
                        : "FAIL"}
                    </span>
                  </div>
                )
              )}
            </div>

            {selectedLoan.exceptions?.length > 0 && (
              <div className="validation-section">
                <h3>Exceptions</h3>

                {selectedLoan.exceptions.map((exception) => (
                  <div
                    className="modal-exception"
                    key={exception.id}
                  >
                    <span
                      className={`severity ${exception.severity}`}
                    >
                      {exception.severity}
                    </span>

                    <strong>{exception.exception_type}</strong>

                    <p>{exception.message}</p>

                    {exception.status === "open" && (
                      <button
                        className="resolve-modal-btn"
                        onClick={() => resolveException(exception.id)}
                        disabled={resolvingException === exception.id}
                      >
                        {resolvingException === exception.id
                          ? "Resolving..."
                          : "Resolve exception"}
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}

            <div className="validation-section">
              <h3>AI Review</h3>

              {aiReviewLoading ? (
                <div className="empty-state">
                  Generating review...
                </div>
              ) : aiReview ? (
                <>
                  <div className="ai-review-card">
                    <strong>
                      Recommendation: {aiReview.recommendation || "Review required"}
                    </strong>

                    <p>
                      {aiReview.summary ||
                        "AI review completed for this loan."}
                    </p>
                  </div>

                  {aiReview.recommendations?.map(
                    (recommendation, index) => (
                      <div
                        className="modal-exception"
                        key={`${recommendation.rule_code || "recommendation"}-${index}`}
                      >
                        {recommendation.severity && (
                          <span
                            className={`severity ${recommendation.severity}`}
                          >
                            {recommendation.severity}
                          </span>
                        )}

                        <strong>
                          {recommendation.rule_code ||
                            "AI recommendation"}
                        </strong>

                        {recommendation.explanation && (
                          <p>{recommendation.explanation}</p>
                        )}

                        {recommendation.suggested_correction && (
                          <p>
                            <strong>Suggested correction:</strong>{" "}
                            {recommendation.suggested_correction}
                          </p>
                        )}

                        {recommendation.reviewer_note && (
                          <p>
                            <strong>Reviewer note:</strong>{" "}
                            {recommendation.reviewer_note}
                          </p>
                        )}
                      </div>
                    )
                  )}

                  {aiReview.reviewer_note && (
                    <p className="ai-advisory-note">
                      {aiReview.reviewer_note}
                    </p>
                  )}
                </>
              ) : (
                <div className="empty-state">
                  AI review unavailable.
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
