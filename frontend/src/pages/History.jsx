import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import * as api from "../api.js";
import {
  Empty,
  ErrorNote,
  Spinner,
  StatusBadge,
} from "../components/ui.jsx";
import { CATEGORY_LABELS, formatFull } from "../utils.js";

const FILTERS = [
  ["", "All"],
  ["draft", "Awaiting Review"],
  ["sent", "Sent"],
  ["rejected", "Discarded"],
];

export default function History() {
  const [status, setStatus] = useState("");
  const [items, setItems] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [openId, setOpenId] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      setItems(
        await api.listFollowUps({
          status: status || undefined,
        })
      );
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }, [status]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Follow-up History</h1>

          <p className="muted">
            Follow-ups generated, reviewed, and sent by the AI agent.
          </p>
        </div>

        <button
          className="btn"
          onClick={load}
          disabled={loading}
        >
          {loading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      <div className="chips">
        {FILTERS.map(([value, label]) => (
          <button
            key={value}
            className={`chip ${
              status === value ? "active" : ""
            }`}
            onClick={() => setStatus(value)}
          >
            {label}
          </button>
        ))}
      </div>

      <ErrorNote error={error} onRetry={load} />

      {loading && !items ? (
        <Spinner label="Loading follow-up history..." />
      ) : null}

      {items && items.length === 0 ? (
        <Empty title="No follow-ups yet">
          Go to My Sent Emails and choose a conversation to
          create an AI-generated follow-up.
        </Empty>
      ) : null}

      <ul className="list">
        {(items ?? []).map((followUp) => (
          <li
            key={followUp.id}
            className="card history-item"
          >
            <button
              className="history-head"
              onClick={() =>
                setOpenId(
                  openId === followUp.id
                    ? null
                    : followUp.id
                )
              }
            >
              <div className="row-main">
                <div className="row-top">
                  <span className="sender">
                    To {followUp.to_email}
                  </span>

                  <span className="muted small">
                    {formatFull(
                      followUp.sent_at ??
                        followUp.created_at
                    )}
                  </span>
                </div>

                <div className="subject">
                  {followUp.subject}
                </div>
              </div>

              <div className="row-badges">
                {followUp.category ? (
                  <span className="badge neutral">
                    {CATEGORY_LABELS[
                      followUp.category
                    ] ?? followUp.category}
                  </span>
                ) : null}

                <StatusBadge status={followUp.status} />
              </div>
            </button>

            {openId === followUp.id ? (
              <div className="history-body">
                <pre className="message-body">
                  {followUp.body}
                </pre>

                {followUp.status === "draft" ? (
                  <Link
                    to={`/thread/${followUp.thread_id}`}
                    className="btn btn-primary"
                  >
                    Continue Review
                  </Link>
                ) : null}

                {followUp.status === "sent" ? (
                  <div className="muted small">
                    This follow-up was successfully sent.
                  </div>
                ) : null}
              </div>
            ) : null}
          </li>
        ))}
      </ul>
    </>
  );
}