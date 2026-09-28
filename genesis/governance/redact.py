"""Redaction-by-construction for governance payloads.

ADR-0008 §4: event and receipt payloads are redacted **before** persistence.
Redaction happens in the writer (see :mod:`genesis.governance.audit`), so a
caller cannot bypass it by passing raw data.

Two guarantees this module provides:

1. **Structural** - any mapping key whose normalized name looks sensitive is
   replaced with ``"[redacted]"``, at any depth.
2. **Bounded** - the serialized result never exceeds ``max_bytes``; oversized
   values are truncated with an explicit marker so truncation is visible
   rather than silent.

The functions are pure and dependency-free so they can be used from the policy
engine, the approval service, and the audit writer without import cycles.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple

__all__ = [
    "REDACTED",
    "TRUNCATED",
    "SENSITIVE_KEY_TOKENS",
    "canonical_json",
    "stable_hash",
    "hash_chain",
    "redact_value",
    "redact_payload",
    "redact_text",
    "is_sensitive_key",
    "iter_secret_leaks",
]

REDACTED = "[redacted]"
TRUNCATED = "[truncated]"

#: Substrings that mark a mapping key as sensitive. Match is on the
#: normalized (lowercased, non-alphanumerics stripped) key name.
SENSITIVE_KEY_TOKENS: Tuple[str, ...] = (
    "password",
    "passwd",
    "passphrase",
    "secret",
    "token",
    "apikey",
    "api_key",
    "accesskey",
    "privatekey",
    "private_key",
    "credential",
    "authorization",
    "authheader",
    "bearer",
    "cookie",
    "sessionid",
    "sessiontoken",
    "refreshtoken",
    "clientsecret",
    "signingkey",
    "webhooksecret",
    "otp",
    "totp",
    "mfa",
    "ssn",
    "socialsecurity",
    "nationalid",
    "passport",
    "creditcard",
    "cardnumber",
    "cvv",
    "cvc",
    "iban",
    "bankaccount",
    "routingnumber",
    "seedphrase",
    "mnemonic",
    "recoverycode",
)

#: Keys that are safe even though they contain a sensitive token. The value of
#: ``token_count`` is a number, not a credential; ``password_policy`` describes
#: a policy, not a secret.
_SENSITIVE_KEY_ALLOWLIST: frozenset = frozenset(
    {
        "tokencount",
        "tokenlimit",
        "tokenbudget",
        "tokensused",
        "maxtokens",
        "passwordpolicy",
        "passwordrules",
        "passwordlength",
        "secretname",
        "secretref",
        "secretid",
    }
)

_KEY_NORMALIZER = re.compile(r"[^a-z0-9]+")

#: Inline credential shapes that must not survive inside free text.
_INLINE_PATTERNS: Tuple[Tuple[re.Pattern, str], ...] = (
    (re.compile(r"\bBearer\s+[A-Za-z0-9\-._~+/]{8,}=*", re.IGNORECASE), "Bearer " + REDACTED),
    (re.compile(r"\bsk-[A-Za-z0-9\-_]{12,}"), REDACTED),
    (re.compile(r"\bsk-ant-[A-Za-z0-9\-_]{12,}"), REDACTED),
    (re.compile(r"\bAIza[0-9A-Za-z\-_]{20,}"), REDACTED),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{16,}"), REDACTED),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}"), REDACTED),
    (re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]*"), REDACTED),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"), REDACTED),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), REDACTED),  # US SSN shape
    (re.compile(r"\b(?:\d[ -]?){13,19}\b"), REDACTED),  # card-like digit run
)

_DEFAULT_MAX_DEPTH = 8
_DEFAULT_STRING_LIMIT = 2048
_DEFAULT_MAX_BYTES = 32_768


def _normalize_key(key: Any) -> str:
    return _KEY_NORMALIZER.sub("", str(key).lower())


def is_sensitive_key(key: Any) -> bool:
    """Return True when a mapping key should have its value redacted."""
    normalized = _normalize_key(key)
    if not normalized:
        return False
    if normalized in _SENSITIVE_KEY_ALLOWLIST:
        return False
    return any(token.replace("_", "") in normalized for token in SENSITIVE_KEY_TOKENS)


def redact_text(text: str, *, max_length: int = _DEFAULT_STRING_LIMIT) -> str:
    """Strip inline credentials from free text and bound its length."""
    result = text
    for pattern, replacement in _INLINE_PATTERNS:
        result = pattern.sub(replacement, result)
    if len(result) > max_length:
        result = result[:max_length] + f" {TRUNCATED}"
    return result


def redact_value(
    value: Any,
    *,
    max_depth: int = _DEFAULT_MAX_DEPTH,
    string_limit: int = _DEFAULT_STRING_LIMIT,
    _depth: int = 0,
) -> Any:
    """Recursively redact a single value into a JSON-safe structure."""
    if _depth >= max_depth:
        return TRUNCATED

    if value is None or isinstance(value, (bool, int)):
        return value

    if isinstance(value, float):
        # JSON cannot represent NaN/Infinity; normalize so hashing is stable.
        if value != value or value in (float("inf"), float("-inf")):
            return None
        return value

    if isinstance(value, str):
        return redact_text(value, max_length=string_limit)

    if isinstance(value, bytes):
        return f"<bytes:{len(value)}>"

    if isinstance(value, Mapping):
        out: Dict[str, Any] = {}
        for key, item in value.items():
            key_str = str(key)
            if is_sensitive_key(key_str):
                out[key_str] = REDACTED
            else:
                out[key_str] = redact_value(
                    item,
                    max_depth=max_depth,
                    string_limit=string_limit,
                    _depth=_depth + 1,
                )
        return out

    if isinstance(value, (list, tuple, set, frozenset)):
        items: Iterable[Any] = sorted(value, key=repr) if isinstance(value, (set, frozenset)) else value
        return [
            redact_value(
                item,
                max_depth=max_depth,
                string_limit=string_limit,
                _depth=_depth + 1,
            )
            for item in items
        ]

    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:  # pragma: no cover - defensive
            return redact_text(repr(value), max_length=string_limit)

    return redact_text(repr(value), max_length=string_limit)


def redact_payload(
    payload: Optional[Mapping[str, Any]] = None,
    *,
    extra: Optional[Mapping[str, Any]] = None,
    max_bytes: int = _DEFAULT_MAX_BYTES,
    string_limit: int = _DEFAULT_STRING_LIMIT,
) -> Dict[str, Any]:
    """Redact a mapping payload and guarantee the result fits ``max_bytes``.

    Shrinking is deterministic: oversized string values are shortened first,
    then whole keys are dropped in reverse-sorted order, so the same input
    always produces the same output (which keeps hash chains stable).
    """
    merged: Dict[str, Any] = {}
    if payload:
        merged.update(dict(payload))
    if extra:
        merged.update(dict(extra))

    redacted = redact_value(merged, string_limit=string_limit)
    if not isinstance(redacted, dict):  # pragma: no cover - defensive
        redacted = {"value": redacted}

    encoded = canonical_json(redacted)
    if len(encoded.encode("utf-8")) <= max_bytes:
        return redacted

    # Pass 1: halve string limits repeatedly.
    limit = string_limit
    while limit > 64:
        limit //= 2
        candidate = redact_value(merged, string_limit=limit)
        if not isinstance(candidate, dict):  # pragma: no cover - defensive
            break
        encoded = canonical_json(candidate)
        if len(encoded.encode("utf-8")) <= max_bytes:
            return candidate
        redacted = candidate

    # Pass 2: drop keys deterministically until it fits.
    working = dict(redacted)
    for key in sorted(working.keys(), reverse=True):
        working.pop(key, None)
        if len(canonical_json(working).encode("utf-8")) <= max_bytes:
            working["_redaction"] = "payload_truncated"
            return working

    return {"_redaction": "payload_dropped"}


def canonical_json(value: Any) -> str:
    """Deterministic JSON used for hashing (sorted keys, no whitespace)."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def stable_hash(value: Any) -> str:
    """SHA-256 of the canonical JSON form of ``value``."""
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def hash_chain(previous_hash: str, body: Any) -> str:
    """SHA-256 over ``previous_hash`` plus the canonical body (integrity chain)."""
    material = f"{previous_hash}\x1f{canonical_json(body)}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def iter_secret_leaks(value: Any) -> Sequence[str]:
    """Return key paths inside ``value`` that still look sensitive.

    Used by tests to assert redaction actually happened rather than trusting
    the implementation.
    """
    leaks: list = []

    def walk(node: Any, path: str) -> None:
        if isinstance(node, Mapping):
            for key, item in node.items():
                child = f"{path}.{key}" if path else str(key)
                if is_sensitive_key(key):
                    leaks.append(child)
                walk(item, child)
        elif isinstance(node, (list, tuple)):
            for index, item in enumerate(node):
                walk(item, f"{path}[{index}]")

    walk(value, "")
    return tuple(leaks)
