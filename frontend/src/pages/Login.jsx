import { useSearchParams } from "react-router-dom";
import { loginUrl } from "../api.js";
import { Logo } from "../components/ui.jsx";

const AUTH_ERRORS = {
  access_denied: "Sign-in was cancelled. Please try again.",
  missing_gmail_permissions: "MailAgent AI needs permission to read and send Gmail. Please allow both when asked.",
  no_refresh_token: "Google didn't grant offline access. Please try again and accept all permissions.",
};

export default function Login() {
  const [params] = useSearchParams();
  const code = params.get("auth_error");

  return (
    <div className="login">
      <div className="login-card card">
        <div className="login-brand">
          <Logo size={44} />
          <h1>MailAgent AI</h1>
        </div>
        <p className="tagline">
          Never forget a follow-up. MailAgent AI finds your internship, referral and recruiter threads, drafts a
          personalized reply, and sends it only after you approve.
        </p>

        {code ? (
          <div className="note note-error" role="alert">
            {AUTH_ERRORS[code] ?? "Sign-in failed. Please try again."}
          </div>
        ) : null}

        <a className="btn btn-primary btn-block" href={loginUrl}>
          Continue with Google
        </a>

        <ul className="trust">
          <li>Scans only the last 5 days of email</li>
          <li>Reads and sends through your Gmail, with your permission</li>
          <li>Nothing is sent without your explicit approval</li>
        </ul>
      </div>
    </div>
  );
}
