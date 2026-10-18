// Thin client for the MailAgent AI backend. Auth is an httpOnly cookie set by the backend,
// so every request must be sent with credentials.
const BASE = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(status, detail) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

let onUnauthorized = null;
export function setUnauthorizedHandler(fn) {
  onUnauthorized = fn;
}

async function request(path, { method = "GET", body } = {}) {
  let res;
  try {
    res = await fetch(BASE + path, {
      method,
      credentials: "include",
      headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, "network_error");
  }

  if (res.status === 204) return null;

  let data = null;
  try {
    data = await res.json();
  } catch {
    /* non-JSON body */
  }

  if (!res.ok) {
    const detail = typeof data?.detail === "string" ? data.detail : "request_failed";
    if (res.status === 401 && onUnauthorized) onUnauthorized();
    throw new ApiError(res.status, detail);
  }
  return data;
}

export const loginUrl = `${BASE}/auth/login`;

export const getMe = () => request("/auth/me");
export const logout = () => request("/auth/logout", { method: "POST" });

export const listEmails = () => request("/emails");
export const getThread = (threadId) => request(`/emails/${encodeURIComponent(threadId)}`);

export const createFollowUp = (threadId, instructions) =>
  request("/followups", { method: "POST", body: { thread_id: threadId, instructions } });

// payload: { action: "approve" | "regenerate" | "reject", subject?, to_email?, body?, instructions? }
export const reviewFollowUp = (id, payload) =>
  request(`/followups/${id}/review`, { method: "POST", body: payload });

export const listFollowUps = ({ threadId, status } = {}) => {
  const qs = new URLSearchParams();
  if (threadId) qs.set("thread_id", threadId);
  if (status) qs.set("status", status);
  const q = qs.toString();
  return request(`/followups${q ? `?${q}` : ""}`);
};
