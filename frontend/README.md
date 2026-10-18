# MailAgent AI — Frontend

React + Vite UI for the MailAgent AI backend (FastAPI + LangGraph).

## Run

```bash
cp .env.example .env     # VITE_API_URL=http://localhost:8000
npm install
npm run dev              # http://localhost:3000
```

Start the backend first (see its README). The dev server is pinned to **port 3000** because the backend's
`FRONTEND_URL` (CORS + post-login redirect) defaults to `http://localhost:3000`. If you change the port, update
`FRONTEND_URL` in the backend `.env` too.

## Screens

| Route | What it does |
|---|---|
| `/login` | "Continue with Google" -> navigates to the backend's `/auth/login`. Shows `?auth_error=` messages. |
| `/` | Inbox: career-related threads from the last 5 days, category chips, "waiting on a reply" filter, status badges. |
| `/thread/:id` | Full conversation + **Create Follow-up**. The agent drafts and pauses; you review it in the panel. |
| `/history` | All follow-ups (awaiting review / sent / discarded). Pending drafts can be reopened. |

### The human-in-the-loop panel
After **Create Follow-up** the backend's LangGraph agent drafts a reply and pauses. The review panel lets you:
- edit recipient, subject and message,
- **Regenerate** (optionally with guidance like "shorter and more casual"),
- **Discard**, or
- **Approve and send**, which asks for a second confirmation before anything is sent.

## How it talks to the backend
- Auth is an httpOnly cookie set by the backend, so every request uses `credentials: "include"` (`src/api.js`).
- Frontend and backend must be the same *site* (both `localhost`, or `app.x.com` + `api.x.com`) for the cookie to be sent.
- Any `401` clears the local session and sends you to `/login`.
- Error codes from the API are mapped to readable messages in `src/utils.js`.

## Structure
```
src/
  api.js            fetch client + endpoint functions
  auth.jsx          auth context (GET /auth/me, sign out)
  App.jsx           routes + protected layout
  components/       Layout, FollowUpReview (the approval step), small UI pieces
  pages/            Login, Dashboard, Thread, History
  styles.css        plain CSS with light/dark themes
```

## Notes
- Plain JavaScript (JSX) to keep setup minimal; converting to TypeScript is straightforward.
- Email bodies are rendered as plain text (never as HTML), so message content can't inject markup.
- Not yet built/tested in a browser: run `npm install && npm run build` first and report any errors.
