export const CATEGORIES = [
  "interview",
  "referral_request",
  "recruiter",
  "internship_application",
  "job_opportunity",
];

export const CATEGORY_LABELS = {
  interview: "Interview",
  referral_request: "Referral",
  recruiter: "Recruiter",
  internship_application: "Internship",
  job_opportunity: "Job",
};

const MESSAGES = {
  network_error: "Can't reach the MailAgent AI server. Is the backend running?",
  not_authenticated: "You're signed out. Please sign in again.",
  reauth_required: "Your Google session expired. Please sign in again.",
  gmail_error: "Gmail returned an error. Please try again in a moment.",
  google_auth_error: "Google sign-in had a problem. Please try again.",
  llm_error: "The AI couldn't write a draft right now. Please try again.",
  no_reply_recipient_found: "Couldn't work out who to reply to in this thread.",
  thread_empty: "This thread has no messages.",
  followup_not_found: "That follow-up no longer exists.",
  followup_already_resolved: "This follow-up was already handled.",
  no_pending_review: "This follow-up isn't waiting for review any more.",
  invalid_email_headers: "The recipient or subject has invalid characters.",
  request_failed: "Something went wrong. Please check your input and try again.",
};

export function errorMessage(err) {
  return MESSAGES[err?.detail] ?? MESSAGES.request_failed;
}

export function formatDate(iso) {
  const d = new Date(iso);
  const now = new Date();
  const sameDay = d.toDateString() === now.toDateString();
  if (sameDay) return d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  const sameYear = d.getFullYear() === now.getFullYear();
  return d.toLocaleDateString([], sameYear ? { month: "short", day: "numeric" } : { year: "numeric", month: "short", day: "numeric" });
}

export function formatFull(iso) {
  return new Date(iso).toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
}

export function senderLabel(name, email) {
  return name?.trim() || email || "Unknown sender";
}
