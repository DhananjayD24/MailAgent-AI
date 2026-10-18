import { useEffect, useState } from "react";
import * as api from "../api.js";
import { CATEGORY_LABELS } from "../utils.js";
import { ErrorNote } from "./ui.jsx";

const EMAIL_RE = /^\S+@\S+\.\S+$/;

/**
 * The human-in-the-loop step. The backend agent has already drafted a reply and is paused;
 * nothing is sent until the user explicitly approves here.
 */
export default function FollowUpReview({ followup, onResolved }) {
  const [to, setTo] = useState(followup.to_email);
  const [subject, setSubject] = useState(followup.subject);
  const [body, setBody] = useState(followup.body);
  const [busy, setBusy] = useState(null); // "approve" | "regenerate" | "reject" | null
  const [error, setError] = useState(null);
  const [confirming, setConfirming] = useState(false);
  const [showRegen, setShowRegen] = useState(false);
  const [instructions, setInstructions] = useState(followup.instructions ?? "");

  // A regenerated draft from the server replaces whatever is in the editor.
  useEffect(() => {
    setTo(followup.to_email);
    setSubject(followup.subject);
    setBody(followup.body);
  }, [followup.id, followup.body, followup.regeneration_count, followup.to_email, followup.subject]);

  const dirty = to !== followup.to_email || subject !== followup.subject || body !== followup.body;
  const valid = body.trim() && subject.trim() && EMAIL_RE.test(to.trim());

  async function run(action, payload = {}) {
    setBusy(action);
    setError(null);
    try {
      const updated = await api.reviewFollowUp(followup.id, { action, ...payload });
      setConfirming(false);
      setShowRegen(false);
      onResolved(updated);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(null);
    }
  }

  const approve = () => run("approve", { to_email: to.trim(), subject: subject.trim(), body });
  const regenerate = () => run("regenerate", { instructions: instructions.trim() || undefined });
  const reject = () => run("reject");

  const disabled = busy !== null;

  return (
    <section className="card review">
      <div className="review-head">
        <h2>Review follow-up</h2>
        <span className="badge status-draft">Awaiting your approval</span>
      </div>
      <p className="muted small">
        The agent drafted this
        {followup.category ? ` (${CATEGORY_LABELS[followup.category] ?? followup.category})` : ""} and is paused. Edit it
        freely. Nothing is sent until you approve.
        {followup.regeneration_count > 0 ? ` Regenerated ${followup.regeneration_count}x.` : ""}
      </p>

      <label className="field">
        <span>To</span>
        <input type="email" value={to} onChange={(e) => setTo(e.target.value)} disabled={disabled} />
      </label>
      <label className="field">
        <span>Subject</span>
        <input type="text" value={subject} onChange={(e) => setSubject(e.target.value)} disabled={disabled} />
      </label>
      <label className="field">
        <span>Message</span>
        <textarea rows={11} value={body} onChange={(e) => setBody(e.target.value)} disabled={disabled} />
      </label>

      {showRegen ? (
        <div className="regen">
          <label className="field">
            <span>Guidance for the new draft (optional)</span>
            <input
              type="text"
              placeholder="e.g. shorter and more casual"
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              disabled={disabled}
              maxLength={1000}
            />
          </label>
          {dirty ? <p className="small warn">Generating a new draft replaces your current edits.</p> : null}
          <div className="row">
            <button className="btn" onClick={() => setShowRegen(false)} disabled={disabled}>
              Cancel
            </button>
            <button className="btn btn-primary" onClick={regenerate} disabled={disabled}>
              {busy === "regenerate" ? "Writing..." : "Generate new draft"}
            </button>
          </div>
        </div>
      ) : null}

      <ErrorNote error={error} />

      {confirming ? (
        <div className="confirm">
          <p>
            <strong>Send this email from your Gmail to {to.trim()}?</strong> This can't be undone.
          </p>
          <div className="row">
            <button className="btn" onClick={() => setConfirming(false)} disabled={disabled}>
              Cancel
            </button>
            <button className="btn btn-primary" onClick={approve} disabled={disabled || !valid}>
              {busy === "approve" ? "Sending..." : "Yes, send now"}
            </button>
          </div>
        </div>
      ) : (
        <div className="actions">
          <button className="btn btn-danger-ghost" onClick={reject} disabled={disabled}>
            {busy === "reject" ? "Discarding..." : "Discard"}
          </button>
          <div className="row">
            <button className="btn" onClick={() => setShowRegen((s) => !s)} disabled={disabled}>
              Regenerate
            </button>
            <button className="btn btn-primary" onClick={() => setConfirming(true)} disabled={disabled || !valid}>
              Approve and send
            </button>
          </div>
        </div>
      )}
      {!valid && !confirming ? (
        <p className="small muted">Add a valid recipient, subject and message to enable sending.</p>
      ) : null}
    </section>
  );
}
