import { Link, NavLink } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import { Logo } from "./ui.jsx";

export default function Layout({ children }) {
  const { user, signOut } = useAuth();

  return (
    <div className="app">
      <header className="topbar">
        <Link to="/" className="brand">
          <Logo />
          <span>MailAgent AI</span>
        </Link>

        <nav className="nav">
          <NavLink to="/" end>
            My Sent Emails
          </NavLink>

          <NavLink to="/history">
            History
          </NavLink>
        </nav>

        <div className="user">
          <span className="muted user-email">
            {user?.email}
          </span>

          <button
            className="btn btn-small"
            onClick={signOut}
          >
            Sign out
          </button>
        </div>
      </header>

      <main className="container">
        {children}
      </main>
    </div>
  );
}