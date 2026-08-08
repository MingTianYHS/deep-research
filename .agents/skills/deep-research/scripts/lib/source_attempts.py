from __future__ import annotations

import hashlib
import json
import re
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .io_utils import utc_now

ERROR_MARKERS = re.compile(r"(?is)<title>\s*(?:401|403|404)[^<]*</title>|\b401\s*:\s*unauthorized\b|\b403\s*:\s*forbidden\b|\b404\s*:\s*not found\b|\bcrawl_livecrawl_timeout\b")
BLOCK_PAGE_MARKERS = re.compile(r"(?is)<title>\s*(?:just a moment|sign in|log in|access denied|page not found|verify (?:you are )?human)[^<]*</title>|enable javascript and cookies to continue|checking your browser|please sign in to continue|captcha|the page you requested does not exist")
TRACKING = {"fbclid", "gclid", "ref", "mc_cid", "mc_eid"}


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    if parts.scheme not in {"http", "https"} or not parts.netloc: raise ValueError(f"invalid URL: {url}")
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k.lower() not in TRACKING and not k.lower().startswith(("utm_", "ga_"))]
    path = re.sub(r"/{2,}", "/", parts.path or "/")
    if path != "/": path = path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(sorted(query)), ""))


def assess_response(http_status: int | None, content: str) -> dict[str, Any]:
    body = content or ""
    if http_status is not None and http_status >= 400: return {"status": "unavailable", "reason": f"http_{http_status}", "eligible_for_evidence": False}
    if ERROR_MARKERS.search(body): return {"status": "unavailable", "reason": "error_page_content", "eligible_for_evidence": False}
    if BLOCK_PAGE_MARKERS.search(body): return {"status": "unavailable", "reason": "access_or_soft_error_page", "eligible_for_evidence": False}
    if not body.strip(): return {"status": "unavailable", "reason": "empty_content", "eligible_for_evidence": False}
    return {"status": "accepted", "reason": None, "eligible_for_evidence": True, "content_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest()}


def load_attempts(path: Path) -> list[dict[str, Any]]:
    if not path.exists(): return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def may_attempt(path: Path, url: str, max_attempts: int = 2) -> dict[str, Any]:
    normalized = normalize_url(url); attempts = [item for item in load_attempts(path) if item.get("normalized_url") == normalized]
    accepted = next((item for item in reversed(attempts) if item.get("status") == "accepted"), None)
    if accepted: return {"allowed": False, "reason": "already_accepted", "reuse": accepted}
    if len(attempts) >= max_attempts: return {"allowed": False, "reason": "attempt_limit", "attempts": len(attempts)}
    return {"allowed": True, "reason": None, "attempts": len(attempts)}


def build_attempt(url: str, tool: str, http_status: int | None, content: str, *, source_version: str | None = None, access_mode: str = "public_static", query_id: str | None = None, discovery_method: str = "known_url", discovered_via_source_attempt_id: str | None = None) -> dict[str, Any]:
    assessment = assess_response(http_status, content)
    return {"id": f"src-{uuid.uuid4().hex[:12]}", "url": url, "normalized_url": normalize_url(url), "tool": tool, "access_mode": access_mode, "http_status": http_status, "source_version": source_version, "query_id": query_id, "discovery_method": discovery_method, "discovered_via_source_attempt_id": discovered_via_source_attempt_id, "attempted_at": utc_now(), **assessment}


def append_attempt(path: Path, attempt: dict[str, Any]) -> dict[str, Any]:
    existing = load_attempts(path); attempt = dict(attempt); attempt.setdefault("attempted_at", utc_now()); content_hash = attempt.get("content_sha256")
    if content_hash:
        duplicate = next((item for item in existing if item.get("content_sha256") == content_hash and item.get("normalized_url") != attempt.get("normalized_url")), None)
        attempt = {**attempt, "independent_origin": not bool(duplicate)}
        if duplicate: attempt["duplicate_content_of"] = duplicate.get("normalized_url")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle: handle.write(json.dumps(attempt, ensure_ascii=False, sort_keys=True) + "\n")
    return attempt
