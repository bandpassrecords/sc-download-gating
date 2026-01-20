from __future__ import annotations

import base64
import hashlib
import re
import secrets
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlencode

from django.conf import settings

try:
    import requests
except Exception:  # pragma: no cover
    requests = None


# Official OAuth 2.1 authorization endpoint (see docs)
# https://developers.soundcloud.com/docs/api/guide
SOUNDCLOUD_AUTHORIZE_URL = "https://secure.soundcloud.com/authorize"
SOUNDCLOUD_TOKEN_URL = "https://secure.soundcloud.com/oauth/token"
SOUNDCLOUD_API_BASE = "https://api.soundcloud.com"


def is_configured() -> bool:
    return bool(getattr(settings, "SOUNDCLOUD_CLIENT_ID", "")) and bool(
        getattr(settings, "SOUNDCLOUD_CLIENT_SECRET", "")
    )


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def generate_pkce_pair() -> Tuple[str, str]:
    """
    PKCE S256.
    - code_verifier: 43-128 chars
    - code_challenge: BASE64URL-ENCODE(SHA256(code_verifier))
    """
    verifier = secrets.token_urlsafe(64)
    verifier = verifier[:128]
    challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge


def build_authorize_url(*, client_id: str, redirect_uri: str, state: str, code_challenge: str) -> str:
    scope = getattr(settings, "SOUNDCLOUD_OAUTH_SCOPE", "*")
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    # SoundCloud docs are inconsistent about required scopes; keep configurable.
    if scope:
        params["scope"] = scope
    return f"{SOUNDCLOUD_AUTHORIZE_URL}?{urlencode(params)}"


_TRACK_ID_RE = re.compile(r"(\d+)$")


def _extract_track_id(track_identifier: str) -> str:
    """
    SoundCloud endpoints under /tracks/{id}/... generally expect the numeric track id.
    We sometimes store URNs like "soundcloud:tracks:123456".
    """
    ident = (track_identifier or "").strip()
    m = _TRACK_ID_RE.search(ident)
    return m.group(1) if m else ident


def _extract_user_id(user_identifier: str) -> str:
    """
    Extract numeric user id from URN like "soundcloud:users:123456".
    Falls back to the input if no numeric suffix exists.
    """
    ident = (user_identifier or "").strip()
    m = _TRACK_ID_RE.search(ident)
    return m.group(1) if m else ident


@dataclass(frozen=True)
class TokenResponse:
    access_token: str
    refresh_token: str
    expires_in: int
    scope: str
    token_type: str


def exchange_code_for_token(*, code: str, redirect_uri: str, code_verifier: str) -> TokenResponse:
    if requests is None:  # pragma: no cover
        raise RuntimeError("Missing dependency: requests. Add 'requests' to requirements.txt.")

    payload = {
        "grant_type": "authorization_code",
        "client_id": settings.SOUNDCLOUD_CLIENT_ID,
        "client_secret": settings.SOUNDCLOUD_CLIENT_SECRET,
        "redirect_uri": redirect_uri,
        "code": code,
        "code_verifier": code_verifier,
    }
    resp = requests.post(SOUNDCLOUD_TOKEN_URL, data=payload, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    return TokenResponse(
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token", ""),
        expires_in=int(data.get("expires_in") or 0),
        scope=data.get("scope", ""),
        token_type=data.get("token_type", ""),
    )


def api_get(path: str, *, access_token: Optional[str] = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if requests is None:  # pragma: no cover
        raise RuntimeError("Missing dependency: requests. Add 'requests' to requirements.txt.")

    url = f"{SOUNDCLOUD_API_BASE}{path}"
    def _do_get(auth_header: Optional[str]) -> requests.Response:
        headers = {}
        if auth_header:
            headers["Authorization"] = auth_header
        return requests.get(url, headers=headers, params=params or {}, timeout=20)

    auth_variants = []
    if access_token:
        # Docs show both "OAuth" and "Bearer" in different sections; try OAuth first, then Bearer.
        auth_variants = [f"OAuth {access_token}", f"Bearer {access_token}"]
    else:
        auth_variants = [None]

    last_resp: Optional[requests.Response] = None
    for auth in auth_variants:
        resp = _do_get(auth)
        last_resp = resp
        # If unauthorized and we have another variant, retry.
        if resp.status_code == 401 and auth != auth_variants[-1]:
            continue
        resp.raise_for_status()
        return resp.json()

    # Shouldn't happen, but keep mypy happy.
    assert last_resp is not None
    last_resp.raise_for_status()
    return last_resp.json()


def api_post(
    path: str,
    *,
    access_token: str,
    params: Optional[Dict[str, Any]] = None,
    json: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if requests is None:  # pragma: no cover
        raise RuntimeError("Missing dependency: requests. Add 'requests' to requirements.txt.")

    url = f"{SOUNDCLOUD_API_BASE}{path}"

    def _do_post(auth_header: Optional[str]) -> requests.Response:
        headers = {}
        if auth_header:
            headers["Authorization"] = auth_header
        return requests.post(url, headers=headers, params=params or {}, json=json, data=data, timeout=20)

    # Docs show both "OAuth" and "Bearer" in different sections; try OAuth first, then Bearer.
    auth_variants = [f"OAuth {access_token}", f"Bearer {access_token}"]

    last_resp: Optional[requests.Response] = None
    for auth in auth_variants:
        resp = _do_post(auth)
        last_resp = resp
        if resp.status_code == 401 and auth != auth_variants[-1]:
            continue
        resp.raise_for_status()
        if not resp.content:
            return {}
        try:
            return resp.json()
        except Exception:
            return {}

    assert last_resp is not None
    last_resp.raise_for_status()
    return {}


def api_put(
    path: str,
    *,
    access_token: str,
    params: Optional[Dict[str, Any]] = None,
    json: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if requests is None:  # pragma: no cover
        raise RuntimeError("Missing dependency: requests. Add 'requests' to requirements.txt.")

    url = f"{SOUNDCLOUD_API_BASE}{path}"

    def _do_put(auth_header: Optional[str]) -> requests.Response:
        headers = {}
        if auth_header:
            headers["Authorization"] = auth_header
        return requests.put(url, headers=headers, params=params or {}, json=json, data=data, timeout=20)

    # Docs show both "OAuth" and "Bearer" in different sections; try OAuth first, then Bearer.
    auth_variants = [f"OAuth {access_token}", f"Bearer {access_token}"]

    last_resp: Optional[requests.Response] = None
    for auth in auth_variants:
        resp = _do_put(auth)
        last_resp = resp
        if resp.status_code == 401 and auth != auth_variants[-1]:
            continue
        resp.raise_for_status()
        if not resp.content:
            return {}
        try:
            return resp.json()
        except Exception:
            return {}

    assert last_resp is not None
    last_resp.raise_for_status()
    return {}


def resolve_track_from_url(*, track_url: str, access_token: Optional[str] = None) -> Dict[str, Any]:
    """
    Resolve a public SoundCloud URL to a track object.
    Requires either an OAuth token or a configured client_id (public resolve).
    """
    params: Dict[str, Any] = {"url": track_url}
    if not access_token:
        # public resolve can accept client_id query param
        client_id = getattr(settings, "SOUNDCLOUD_CLIENT_ID", "")
        if client_id:
            params["client_id"] = client_id
    return api_get("/resolve", access_token=access_token, params=params)


def resolve_track_urn_from_url(*, track_url: str, access_token: Optional[str] = None) -> str:
    """
    Resolve a public SoundCloud URL to a track identifier (URN preferred).
    Requires either an OAuth token or a configured client_id (public resolve).
    """
    data = resolve_track_from_url(track_url=track_url, access_token=access_token)
    urn = data.get("urn") or ""
    if urn:
        return urn
    # Fallback: older APIs used numeric "id"
    track_id = data.get("id")
    if track_id is not None:
        return f"soundcloud:tracks:{track_id}"
    return ""


def resolve_user_from_url(*, profile_url: str, access_token: Optional[str] = None) -> Dict[str, Any]:
    """
    Resolve a public SoundCloud profile URL to a user object.
    Requires either an OAuth token or a configured client_id (public resolve).
    """
    params: Dict[str, Any] = {"url": profile_url}
    if not access_token:
        client_id = getattr(settings, "SOUNDCLOUD_CLIENT_ID", "")
        if client_id:
            params["client_id"] = client_id
    return api_get("/resolve", access_token=access_token, params=params)


def get_me(*, access_token: str) -> Dict[str, Any]:
    return api_get("/me", access_token=access_token)


def user_liked_track(*, access_token: str, track_urn: str, max_pages: int = 10) -> bool:
    """
    Check if the authenticated user has liked the given track.
    Strategy: iterate /me/likes/tracks pages and look for matching urn.
    """
    params: Dict[str, Any] = {"limit": 200, "linked_partitioning": "true"}
    data = api_get("/me/likes/tracks", access_token=access_token, params=params)
    pages = 0
    while True:
        pages += 1
        collection = data.get("collection") or []
        for item in collection:
            # Items may be "like" objects or track objects depending on API shape
            track = item.get("track") if isinstance(item, dict) and "track" in item else item
            if isinstance(track, dict) and track.get("urn") == track_urn:
                return True
        if pages >= max_pages:
            return False
        next_href = data.get("next_href")
        if not next_href:
            return False
        # next_href is a full URL; requests can follow it directly
        if requests is None:  # pragma: no cover
            return False
        # Use OAuth header as primary variant for pagination requests.
        resp = requests.get(next_href, headers={"Authorization": f"OAuth {access_token}"}, timeout=20)
        if resp.status_code == 401:
            resp = requests.get(next_href, headers={"Authorization": f"Bearer {access_token}"}, timeout=20)
        resp.raise_for_status()
        data = resp.json()


def like_track(*, access_token: str, track_identifier: str) -> Dict[str, Any]:
    """
    Like a track on behalf of the authenticated user.
    """
    track_id = _extract_track_id(track_identifier)
    return api_post(f"/likes/tracks/{track_id}", access_token=access_token)


def post_comment(
    *,
    access_token: str,
    track_identifier: str,
    body: str,
    timestamp_ms: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Post a comment on a track on behalf of the authenticated user.
    """
    track_id = _extract_track_id(track_identifier)
    payload: Dict[str, Any] = {"comment": {"body": body}}
    if timestamp_ms is not None:
        payload["comment"]["timestamp"] = int(timestamp_ms)
    return api_post(f"/tracks/{track_id}/comments", access_token=access_token, json=payload)


def follow_user(*, access_token: str, user_identifier: str) -> Dict[str, Any]:
    """
    Follow a user on behalf of the authenticated user.
    Docs use: PUT /me/followings/{user_id}
    """
    user_id = _extract_user_id(user_identifier)
    return api_put(f"/me/followings/{user_id}", access_token=access_token)


def user_follows_user(
    *,
    access_token: str,
    target_user_urn: str,
    max_pages: int = 5,
) -> bool:
    """
    Check if the authenticated user follows target user by scanning /me/followings.
    SoundCloud does not provide a direct "contains" endpoint.
    """
    params: Dict[str, Any] = {"limit": 200, "linked_partitioning": "true"}
    data = api_get("/me/followings", access_token=access_token, params=params)
    pages = 0
    while True:
        pages += 1
        for u in data.get("collection") or []:
            if isinstance(u, dict) and (u.get("urn") == target_user_urn):
                return True
        if pages >= max_pages:
            return False
        next_href = data.get("next_href")
        if not next_href:
            return False
        if requests is None:  # pragma: no cover
            return False
        # next_href is a full URL; fetch it with OAuth header
        resp = requests.get(next_href, headers={"Authorization": f"OAuth {access_token}"}, timeout=20)
        if resp.status_code == 401:
            resp = requests.get(next_href, headers={"Authorization": f"Bearer {access_token}"}, timeout=20)
        resp.raise_for_status()
        data = resp.json()


def get_followings_urns(*, access_token: str, max_pages: int = 5) -> set[str]:
    """
    Fetch a (bounded) set of URNs the authenticated user follows.
    Useful to check multiple follow targets efficiently with one traversal.
    """
    params: Dict[str, Any] = {"limit": 200, "linked_partitioning": "true"}
    data = api_get("/me/followings", access_token=access_token, params=params)
    pages = 0
    out: set[str] = set()
    while True:
        pages += 1
        for u in data.get("collection") or []:
            if isinstance(u, dict):
                urn = (u.get("urn") or "").strip()
                if urn:
                    out.add(urn)
        if pages >= max_pages:
            return out
        next_href = data.get("next_href")
        if not next_href:
            return out
        if requests is None:  # pragma: no cover
            return out
        resp = requests.get(next_href, headers={"Authorization": f"OAuth {access_token}"}, timeout=20)
        if resp.status_code == 401:
            resp = requests.get(next_href, headers={"Authorization": f"Bearer {access_token}"}, timeout=20)
        resp.raise_for_status()
        data = resp.json()


def user_commented_on_track(
    *,
    access_token: Optional[str],
    track_identifier: str,
    user_urn: str,
    max_pages: int = 10,
) -> bool:
    """
    Check if a user has commented on the track by scanning track comments.
    Uses public comments if possible; if access_token is provided, uses it.
    """
    params: Dict[str, Any] = {"limit": 200, "linked_partitioning": "true"}
    if not access_token:
        client_id = getattr(settings, "SOUNDCLOUD_CLIENT_ID", "")
        if client_id:
            params["client_id"] = client_id
    track_id = _extract_track_id(track_identifier)
    data = api_get(f"/tracks/{track_id}/comments", access_token=access_token, params=params)
    pages = 0
    while True:
        pages += 1
        for c in data.get("collection") or []:
            user = c.get("user") or {}
            if user.get("urn") == user_urn:
                return True
        if pages >= max_pages:
            return False
        next_href = data.get("next_href")
        if not next_href:
            return False
        if requests is None:  # pragma: no cover
            return False
        headers = {"Authorization": f"OAuth {access_token}"} if access_token else {}
        resp = requests.get(next_href, headers=headers, timeout=20)
        if resp.status_code == 401 and access_token:
            resp = requests.get(next_href, headers={"Authorization": f"Bearer {access_token}"}, timeout=20)
        resp.raise_for_status()
        data = resp.json()

