"""Thin async Gmail REST client (httpx)."""
import asyncio
from typing import Optional

import httpx

from app.services.gmail_parsing import ParsedThread, parse_thread
from app.services.google_oauth import ReauthRequired

BASE_URL = "https://gmail.googleapis.com/gmail/v1/users/me"


class GmailError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(f"Gmail API error {status}: {detail}")
        self.status = status
        self.detail = detail


class GmailClient:
    def __init__(self, access_token: str, my_email: str):
        self.my_email = my_email
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=20,
        )

    async def __aenter__(self) -> "GmailClient":
        return self

    async def __aexit__(self, *exc) -> None:
        await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        r = await self._client.request(method, path, **kwargs)
        if r.status_code == 401:
            raise ReauthRequired()
        if r.status_code >= 400:
            raise GmailError(r.status_code, r.text[:500])
        return r.json()

    async def list_recent_thread_ids(self, days: int, limit: int, exclude_promotions: bool) -> list[str]:
        query = f"newer_than:{days}d"
        if exclude_promotions:
            query += " -category:promotions -category:social"

        ids: list[str] = []
        page_token: Optional[str] = None
        while len(ids) < limit:
            params: dict = {"q": query, "maxResults": min(100, limit - len(ids))}
            if page_token:
                params["pageToken"] = page_token
            data = await self._request("GET", "/threads", params=params)
            ids.extend(t["id"] for t in data.get("threads", []))
            page_token = data.get("nextPageToken")
            if not page_token:
                break
        return ids[:limit]

    async def get_thread(self, thread_id: str, full: bool) -> ParsedThread:
        if full:
            params = [("format", "full")]
        else:
            params = [("format", "metadata")] + [
                ("metadataHeaders", h) for h in ("Subject", "From", "To", "Cc", "Date", "Reply-To")
            ]
        data = await self._request("GET", f"/threads/{thread_id}", params=params)
        return parse_thread(data, self.my_email, with_body=full)

    async def get_threads_metadata(self, thread_ids: list[str], concurrency: int = 8) -> list[ParsedThread]:
        sem = asyncio.Semaphore(concurrency)

        async def one(tid: str) -> ParsedThread:
            async with sem:
                return await self.get_thread(tid, full=False)

        results = await asyncio.gather(*(one(t) for t in thread_ids), return_exceptions=True)
        threads: list[ParsedThread] = []
        for res in results:
            if isinstance(res, ReauthRequired):
                raise res
            if isinstance(res, ParsedThread) and res.messages:
                threads.append(res)
            # other per-thread failures (e.g. thread deleted mid-scan) are skipped
        return threads

    async def send_raw(self, raw_b64url: str, thread_id: Optional[str]) -> dict:
        payload: dict = {"raw": raw_b64url}
        if thread_id:
            payload["threadId"] = thread_id
        return await self._request("POST", "/messages/send", json=payload)
