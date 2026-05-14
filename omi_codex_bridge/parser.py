from __future__ import annotations

import hashlib
import re


TRIGGER_PATTERNS = [
    r"\bhey omi codex\b",
    r"\bomi codex\b",
    r"\bask codex to\b",
    r"\btell codex to\b",
    r"\bhave codex\b",
    r"\bget codex to\b",
    r"\bcodex please\b",
    r"\bcodex start\b",
    r"\bcodex build\b",
    r"\bcodex fix\b",
    r"\bcodex implement\b",
    r"\bcodex run\b",
    r"\bcodex test\b",
    r"\bcodex create\b",
]


def extract_codex_prompt(text: str) -> str | None:
    normalized = " ".join(text.replace("\n", " ").split())
    lowered = normalized.lower()
    best: tuple[int, re.Match[str]] | None = None
    for pattern in TRIGGER_PATTERNS:
        match = re.search(pattern, lowered, flags=re.IGNORECASE)
        if match and (best is None or match.start() < best[0]):
            best = (match.start(), match)
    if best is None:
        return None

    prompt = normalized[best[1].end() :].strip().lstrip(" .,:;-")
    if len(prompt) < 6:
        return None
    return prompt


def dedupe_key(uid: str, session_id: str, prompt: str) -> str:
    payload = f"{uid}|{session_id}|{prompt.strip().lower()}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
