import { CATEGORY_LABELS, errorMessage } from "../utils.js";

export function Logo({ size = 28 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <rect width="32" height="32" rx="8" fill="var(--accent)" />
      <rect x="6" y="9" width="20" height="14" rx="3" fill="none" stroke="#fff" strokeWidth="2" />
      <path d="M7 11l9 6.5L25 11" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function Spinner({ label }) {
  return (
    <div className="spinner-wrap" role="status">
      <span className="spinner" />
      {label ? <span className="muted">{label}</span> : null}
    </div>
  );
}

export function CategoryBadge({ category }) {
  if (!category) return null;
  return <span className={`badge cat-${category}`}>{CATEGORY_LABELS[category] ?? category}</span>;
}

export function StatusBadge({ status }) {
  const labels = { draft: "Awaiting review", sent: "Sent", rejected: "Discarded" };
  return <span className={`badge status-${status}`}>{labels[status] ?? status}</span>;
}

export function ErrorNote({ error, onRetry }) {
  if (!error) return null;
  return (
    <div className="note note-error" role="alert">
      <span>{errorMessage(error)}</span>
      {onRetry ? (
        <button className="btn btn-small" onClick={onRetry}>
          Retry
        </button>
      ) : null}
    </div>
  );
}

export function Empty({ title, children }) {
  return (
    <div className="empty">
      <h3>{title}</h3>
      {children ? <p className="muted">{children}</p> : null}
    </div>
  );
}
