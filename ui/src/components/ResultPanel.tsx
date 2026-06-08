import { InterpretResponse } from "../App";

interface ResultPanelProps {
  result: InterpretResponse | null;
  errorMessage: string;
  hasError: boolean;
}

function ResultPanel({ result, errorMessage, hasError }: ResultPanelProps) {
  if (hasError) {
    return (
      <div className="result-panel">
        <div className="result-panel__inner result-panel__inner--error">
          <div className="result-header">
            <div className="result-icon result-icon--error">
              <ErrorIcon />
            </div>
            <h2 className="result-title result-title--error">Request Failed</h2>
          </div>
          <p className="result-section-label" style={{ marginBottom: "8px" }}>
            Error details
          </p>
          <div className="error-message">
            <pre style={{ margin: 0, whiteSpace: "pre-wrap", wordBreak: "break-word", fontFamily: "inherit", fontSize: "14px" }}>
              {errorMessage}
            </pre>
          </div>
          <p style={{ marginTop: "12px", fontSize: "13px", color: "var(--color-text-secondary)" }}>
            Check the server logs for more details, or refine your input and try again.
          </p>
        </div>
      </div>
    );
  }

  if (!result) return null;

  /* ---- Clarification needed ---- */
  if (result.clarification_needed) {
    const { questions } = result.clarification_needed;
    return (
      <div className="result-panel">
        <div className="result-panel__inner result-panel__inner--clarification">
          <div className="result-header">
            <div className="result-icon result-icon--clarification">
              <WarningIcon />
            </div>
            <h2 className="result-title result-title--clarification">
              More Information Needed
            </h2>
          </div>
          <p className="result-section-label">
            Please answer the following questions to proceed:
          </p>
          <ol className="clarification-questions">
            {questions.map((q, i) => (
              <li key={i} className="clarification-question">
                <span className="clarification-question__number">{i + 1}</span>
                <span className="clarification-question__text">{q}</span>
              </li>
            ))}
          </ol>
        </div>
      </div>
    );
  }

  /* ---- Rule created ---- */
  if (result.created_rule) {
    const rule = result.created_rule;
    /* Extract common fields if present; fall back to raw JSON */
    const name =
      typeof rule["name"] === "string" ? rule["name"] : null;
    const status =
      typeof rule["status"] === "string" ? rule["status"] : null;
    const id =
      typeof rule["id"] === "string" || typeof rule["id"] === "number"
        ? String(rule["id"])
        : null;
    const description =
      typeof rule["description"] === "string" ? rule["description"] : null;

    return (
      <div className="result-panel">
        <div className="result-panel__inner result-panel__inner--success">
          <div className="result-header">
            <div className="result-icon result-icon--success">
              <CheckIcon />
            </div>
            <h2 className="result-title result-title--success">
              Rule Created Successfully
              {result.dry_run && (
                <span
                  style={{
                    fontSize: "12px",
                    fontWeight: 500,
                    marginLeft: "10px",
                    color: "var(--color-text-secondary)",
                  }}
                >
                  (dry run)
                </span>
              )}
            </h2>
          </div>

          {(name || status || id || description) && (
            <div className="rule-details" style={{ marginBottom: "16px" }}>
              {name && (
                <div className="rule-detail-row">
                  <span className="rule-detail-label">Name</span>
                  <span className="rule-detail-value">{name}</span>
                </div>
              )}
              {id && (
                <div className="rule-detail-row">
                  <span className="rule-detail-label">ID</span>
                  <span className="rule-detail-value rule-detail-value--mono">{id}</span>
                </div>
              )}
              {status && (
                <div className="rule-detail-row">
                  <span className="rule-detail-label">Status</span>
                  <span
                    className="rule-detail-value"
                    style={{
                      color:
                        status.toLowerCase() === "enabled" ||
                        status.toLowerCase() === "active"
                          ? "var(--color-success)"
                          : "var(--color-text-primary)",
                      fontWeight: 600,
                    }}
                  >
                    {status}
                  </span>
                </div>
              )}
              {description && (
                <div className="rule-detail-row">
                  <span className="rule-detail-label">Description</span>
                  <span className="rule-detail-value">{description}</span>
                </div>
              )}
            </div>
          )}

          <p className="result-section-label">Full rule details</p>
          <pre className="rule-raw">{JSON.stringify(rule, null, 2)}</pre>
        </div>
      </div>
    );
  }

  /* ---- Fallback: show raw result ---- */
  return (
    <div className="result-panel">
      <div className="result-panel__inner">
        <div className="result-header">
          <div className="result-icon result-icon--success">
            <CheckIcon />
          </div>
          <h2 className="result-title">Response</h2>
        </div>
        <pre className="rule-raw">{JSON.stringify(result, null, 2)}</pre>
      </div>
    </div>
  );
}

/* ---- Inline SVG icons ---- */

function CheckIcon() {
  return (
    <svg
      className="icon"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

function WarningIcon() {
  return (
    <svg
      className="icon"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  );
}

function ErrorIcon() {
  return (
    <svg
      className="icon"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="10" />
      <line x1="15" y1="9" x2="9" y2="15" />
      <line x1="9" y1="9" x2="15" y2="15" />
    </svg>
  );
}

export default ResultPanel;
