import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import * as api from "../api.js";
import FollowUpReview from "../components/FollowUpReview.jsx";
import { CategoryBadge, ErrorNote, Spinner } from "../components/ui.jsx";
import { formatFull, senderLabel } from "../utils.js";

export default function Thread() {
  const { threadId } = useParams();
  const navigate = useNavigate();

  const [thread, setThread] = useState(null);
  const [draft, setDraft] = useState(null);
  const [sent, setSent] = useState(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [instructions, setInstructions] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setSent(null);

    try {
      const [threadData, drafts] = await Promise.all([
        api.getThread(threadId),
        api.listFollowUps({
          threadId,
          status: "draft",
        }),
      ]);

      setThread(threadData);
      setDraft(drafts[0] ?? null);
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }, [threadId]);

  useEffect(() => {
    load();
  }, [load]);

  async function createFollowUp() {
    setCreating(true);
    setCreateError(null);

    try {
      const followUp = await api.createFollowUp(
        threadId,
        instructions.trim() || undefined
      );

      setDraft(followUp);
    } catch (e) {
      setCreateError(e);
    } finally {
      setCreating(false);
    }
  }

  function handleResolved(updated) {
    if (updated.status === "sent") {
      /*
       * Follow-up was successfully sent.
       * Move the user directly to History.
       */
      navigate("/history");
      return;
    }

    if (updated.status === "rejected") {
      setDraft(null);
      return;
    }

    setDraft(updated);
  }

  return (
    <>
      <Link to="/" className="back">
        &larr; Back to My Sent Emails
      </Link>

      {loading ? (
        <Spinner label="Loading conversation..." />
      ) : null}

      <ErrorNote error={error} onRetry={load} />

      {thread ? (
        <div className="thread-grid">
          <section>
            <div className="page-head">
              <div>
                <h1 className="thread-title">
                  {thread.subject}
                </h1>

                <CategoryBadge category={thread.category} />
              </div>
            </div>

            <ul className="messages">
              {thread.messages.map((message) => (
                <li
                  key={message.id}
                  className={`message card ${
                    message.is_from_me ? "mine" : ""
                  }`}
                >
                  <div className="message-head">
                    <strong>
                      {message.is_from_me
                        ? "You"
                        : senderLabel(
                            message.sender_name,
                            message.sender_email
                          )}
                    </strong>

                    <span className="muted small">
                      {formatFull(message.date)}
                    </span>
                  </div>

                  <pre className="message-body">
                    {message.body}
                  </pre>
                </li>
              ))}
            </ul>
          </section>

          <aside className="agent-panel">
            {draft ? (
              <FollowUpReview
                followup={draft}
                onResolved={handleResolved}
              />
            ) : (
              <section className="card">
                <div className="agent-heading">
                  <h2>AI Follow-up Agent</h2>
                  <span className="badge neutral">
                    Human approval required
                  </span>
                </div>

                <p className="muted small">
                  The agent will read this entire conversation and
                  create a personalized follow-up email. Nothing will
                  be sent until you review and approve the draft.
                </p>

                <label className="field">
                  <span>Additional guidance (optional)</span>

                  <input
                    type="text"
                    placeholder="e.g. ask about next steps, keep it brief"
                    value={instructions}
                    onChange={(e) =>
                      setInstructions(e.target.value)
                    }
                    disabled={creating}
                    maxLength={1000}
                  />
                </label>

                <ErrorNote error={createError} />

                <button
                  className="btn btn-primary btn-block"
                  onClick={createFollowUp}
                  disabled={creating}
                >
                  {creating
                    ? "AI is drafting..."
                    : "Generate Follow-up"}
                </button>

                {creating ? (
                  <Spinner label="Reading conversation and generating draft..." />
                ) : null}
              </section>
            )}
          </aside>
        </div>
      ) : null}
    </>
  );
}