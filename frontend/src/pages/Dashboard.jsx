import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import * as api from "../api.js";
import { CategoryBadge, Empty, ErrorNote, Spinner } from "../components/ui.jsx";
import { CATEGORIES, CATEGORY_LABELS, formatDate } from "../utils.js";

export default function Dashboard() {
  const [emails, setEmails] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [category, setCategory] = useState("all");
  const [awaitingOnly, setAwaitingOnly] = useState(false);
  const [creatingId, setCreatingId] = useState(null);
  const [createError, setCreateError] = useState(null);

  const navigate = useNavigate();

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      setEmails(await api.listEmails());
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const counts = useMemo(() => {
    const c = {
      all: emails?.length ?? 0,
    };

    for (const cat of CATEGORIES) {
      c[cat] = 0;
    }

    for (const email of emails ?? []) {
      c[email.category] = (c[email.category] ?? 0) + 1;
    }

    return c;
  }, [emails]);

  const visible = useMemo(() => {
    return (emails ?? []).filter((email) => {
      const matchesCategory =
        category === "all" || email.category === category;

      const matchesAwaiting =
        !awaitingOnly || email.awaiting_reply;

      return matchesCategory && matchesAwaiting;
    });
  }, [emails, category, awaitingOnly]);

  const awaitingCount = (emails ?? []).filter(
    (email) => email.awaiting_reply && !email.followup_sent
  ).length;

  const draftsCount = (emails ?? []).filter(
    (email) => email.has_followup && !email.followup_sent
  ).length;

  const sentCount = (emails ?? []).filter(
    (email) => email.followup_sent
  ).length;

  async function handleFollowUp(event, threadId) {
    event.preventDefault();
    event.stopPropagation();

    setCreatingId(threadId);
    setCreateError(null);

    try {
      /*
       * Starting the follow-up here immediately starts
       * the LangGraph / AI agent flow.
       */
      await api.createFollowUp(threadId);

      /*
       * Move to the thread page where the generated
       * draft will be shown for human review.
       */
      navigate(`/thread/${threadId}`);
    } catch (e) {
      setCreateError(e);
      setCreatingId(null);
    }
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1>My Sent Emails</h1>
          <p className="muted">
            Career-related conversations you sent in the last 5 days.
            Follow up when you are waiting for a response.
          </p>
        </div>

        <button className="btn" onClick={load} disabled={loading}>
          {loading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {emails ? (
        <div className="stats">
          <div className="stat">
            <strong>{emails.length}</strong>
            <span>sent conversations</span>
          </div>

          <div className="stat">
            <strong>{awaitingCount}</strong>
            <span>waiting for reply</span>
          </div>

          <div className="stat">
            <strong>{draftsCount}</strong>
            <span>drafts waiting</span>
          </div>

          <div className="stat">
            <strong>{sentCount}</strong>
            <span>follow-ups sent</span>
          </div>
        </div>
      ) : null}

      <div className="filters">
        <div className="chips">
          {["all", ...CATEGORIES].map((c) => (
            <button
              key={c}
              className={`chip ${category === c ? "active" : ""}`}
              onClick={() => setCategory(c)}
            >
              {c === "all" ? "All" : CATEGORY_LABELS[c]}

              <span className="chip-count">
                {counts[c] ?? 0}
              </span>
            </button>
          ))}
        </div>

        <label className="check">
          <input
            type="checkbox"
            checked={awaitingOnly}
            onChange={(e) => setAwaitingOnly(e.target.checked)}
          />
          Waiting for reply
        </label>
      </div>

      <ErrorNote error={error} onRetry={load} />

      {createError ? (
        <ErrorNote
          error={createError}
          onRetry={() => setCreateError(null)}
        />
      ) : null}

      {loading && !emails ? (
        <Spinner label="Loading your sent emails..." />
      ) : null}

      {emails && visible.length === 0 ? (
        <Empty title="No conversations found">
          {emails.length === 0
            ? "No relevant emails sent in the last 5 days."
            : "No conversations match these filters."}
        </Empty>
      ) : null}

      <ul className="list">
        {visible.map((email) => {
          const canFollowUp =
            email.awaiting_reply &&
            !email.followup_sent &&
            !email.has_followup;

          return (
            <li key={email.thread_id} className="card sent-email-card">
              <div className="sent-email-main">
                <Link
                  to={`/thread/${email.thread_id}`}
                  className="row-item"
                >
                  <div className="row-main">
                    <div className="row-top">
                      <span className="sender">
                        {email.recipient_name ||
                          email.recipient_email ||
                          "Recipient"}
                      </span>

                      <span className="muted small">
                        {formatDate(email.date)}
                      </span>
                    </div>

                    <div className="subject">
                      {email.subject}
                    </div>

                    <div className="snippet muted">
                      {email.snippet}
                    </div>
                  </div>

                  <div className="row-badges">
                    <CategoryBadge category={email.category} />

                    {email.followup_sent ? (
                      <span className="badge status-sent">
                        Follow-up sent
                      </span>
                    ) : email.has_followup ? (
                      <span className="badge status-draft">
                        Draft ready
                      </span>
                    ) : email.awaiting_reply ? (
                      <span className="badge neutral">
                        Waiting for reply
                      </span>
                    ) : (
                      <span className="badge neutral">
                        No follow-up needed
                      </span>
                    )}
                  </div>
                </Link>

                <div className="email-actions">
                  {canFollowUp ? (
                    <button
                      className="btn btn-primary"
                      onClick={(event) =>
                        handleFollowUp(event, email.thread_id)
                      }
                      disabled={creatingId === email.thread_id}
                    >
                      {creatingId === email.thread_id
                        ? "AI drafting..."
                        : "Follow Up"}
                    </button>
                  ) : email.has_followup && !email.followup_sent ? (
                    <Link
                      to={`/thread/${email.thread_id}`}
                      className="btn"
                    >
                      Review Draft
                    </Link>
                  ) : email.followup_sent ? (
                    <Link to="/history" className="btn">
                      View History
                    </Link>
                  ) : null}

                  <Link
                    to={`/thread/${email.thread_id}`}
                    className="btn"
                  >
                    Open
                  </Link>
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </>
  );
}