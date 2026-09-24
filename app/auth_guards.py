# auth_guards.py
# ─────────────────────────────────────────────────────────────────────────────
# Security guards for the authenticated MOBILE API (`/api/mobile/*`).
#
# Every mobile endpoint must:
#   1. Present a valid Firebase ID token  (Authorization: Bearer <idToken>)
#      → proves a real, signed-in Hello Tabeeb user is making the call.
#   2. Present a Firebase App Check token  (X-Firebase-AppCheck: <token>)
#      → proves the call comes from the genuine app binary, not a script.
#      App Check is verified in "monitor" mode by default (logged, not blocked)
#      so it can be rolled out safely. Set APP_CHECK_ENFORCED=true to reject
#      calls that fail / omit attestation once monitoring looks clean.
#   3. Stay within a per-user rate limit.
#
# These guards are the security boundary that replaces the old model where the
# Flutter client held the Brevo key and a Google service-account key directly.
# ─────────────────────────────────────────────────────────────────────────────

import os
import time
import logging
import threading
from functools import wraps

from flask import request, jsonify, g
from firebase_admin import auth as fb_auth

try:
    from firebase_admin import app_check as fb_app_check
except Exception:  # pragma: no cover - very old firebase-admin
    fb_app_check = None

logger = logging.getLogger(__name__)


def _env_flag(name, default=False):
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


# When true, requests that fail (or omit) App Check attestation are rejected.
# Keep false during initial rollout ("monitor mode"), then flip to true.
APP_CHECK_ENFORCED = _env_flag("APP_CHECK_ENFORCED", False)


# ─────────────────────────────────────────────────────────────────────────────
# AUTHENTICATION
# ─────────────────────────────────────────────────────────────────────────────

def _extract_bearer_token():
    header = request.headers.get("Authorization", "") or ""
    if not header.startswith("Bearer "):
        return None
    token = header[len("Bearer "):].strip()
    return token or None


def require_app_auth(f):
    """Verify Firebase ID token (required) + App Check token (monitor/enforced).

    On success, populates:
      g.uid                 -> Firebase user id
      g.user_email          -> user's email (may be None)
      g.email_verified      -> bool
      g.app_check_verified  -> bool
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        id_token = _extract_bearer_token()
        if not id_token:
            return jsonify(success=False, message="Authentication required."), 401

        try:
            decoded = fb_auth.verify_id_token(id_token)
        except Exception as exc:
            logger.warning("Rejected request: invalid Firebase ID token (%s)", exc)
            return jsonify(success=False, message="Invalid or expired session."), 401

        g.uid = decoded.get("uid")
        g.user_email = decoded.get("email")
        g.email_verified = bool(decoded.get("email_verified", False))

        # ── App Check (attestation that this is the real app) ────────────────
        g.app_check_verified = False
        appcheck_token = request.headers.get("X-Firebase-AppCheck", "") or ""
        if appcheck_token and fb_app_check is not None:
            try:
                fb_app_check.verify_token(appcheck_token)
                g.app_check_verified = True
            except Exception as exc:
                logger.warning(
                    "App Check verification FAILED for uid=%s: %s", g.uid, exc
                )
                if APP_CHECK_ENFORCED:
                    return jsonify(success=False, message="App attestation failed."), 401
        else:
            if APP_CHECK_ENFORCED:
                logger.warning("App Check token missing for uid=%s (enforced)", g.uid)
                return jsonify(success=False, message="App attestation required."), 401
            if appcheck_token and fb_app_check is None:
                logger.warning("App Check token received but firebase_admin.app_check unavailable.")

        return f(*args, **kwargs)

    return wrapper


def require_verified_email(f):
    """Optional stricter guard: also require a verified email address.

    Apply on top of @require_app_auth for flows that must only run for
    email-verified accounts.
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        if not getattr(g, "email_verified", False):
            return jsonify(success=False, message="Email not verified."), 403
        return f(*args, **kwargs)

    return wrapper


# ─────────────────────────────────────────────────────────────────────────────
# RATE LIMITING  (in-memory fixed window)
#
# NOTE: state lives in-process. The CapRover Dockerfile runs a single gunicorn
# worker, so this is effectively a global limiter. If you scale to multiple
# workers/instances, move this to a shared store (e.g. Redis or Firestore).
# ─────────────────────────────────────────────────────────────────────────────

_buckets = {}
_buckets_lock = threading.Lock()
_last_sweep = [0.0]


def _client_ip():
    fwd = request.headers.get("X-Forwarded-For", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.remote_addr or "unknown"


def _sweep(now, window_seconds):
    # Occasionally drop expired buckets so memory does not grow unbounded.
    if now - _last_sweep[0] < 60:
        return
    _last_sweep[0] = now
    stale = [k for k, v in _buckets.items() if now - v["start"] >= max(window_seconds, 3600)]
    for k in stale:
        _buckets.pop(k, None)


def rate_limit(max_calls, window_seconds):
    """Limit a route to `max_calls` per `window_seconds` per user (or IP)."""

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            identity = getattr(g, "uid", None) or _client_ip()
            key = f"{identity}:{request.endpoint}"
            now = time.time()

            with _buckets_lock:
                _sweep(now, window_seconds)
                bucket = _buckets.get(key)
                if bucket is None or now - bucket["start"] >= window_seconds:
                    _buckets[key] = {"start": now, "count": 1}
                else:
                    bucket["count"] += 1
                    if bucket["count"] > max_calls:
                        retry_after = int(window_seconds - (now - bucket["start"])) + 1
                        logger.warning(
                            "Rate limit hit for %s on %s", identity, request.endpoint
                        )
                        resp = jsonify(
                            success=False,
                            message="Too many requests. Please try again in a moment.",
                        )
                        resp.status_code = 429
                        resp.headers["Retry-After"] = str(max(retry_after, 1))
                        return resp

            return f(*args, **kwargs)

        return wrapper

    return decorator
