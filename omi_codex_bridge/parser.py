from __future__ import annotations

import hashlib
import re


CODEX_NAME = r"(?:codex|kodex|kodeks)"

TRIGGER_PATTERNS = [
    rf"\bhey\s+omi\s+{CODEX_NAME}\b",
    rf"\bomi\s+{CODEX_NAME}\b",
    rf"\b(?:ask|tell|get|have)\s+{CODEX_NAME}\s+(?:to|please)\b",
    rf"\b{CODEX_NAME}\s+(?:please|pls)\b",
    rf"\b{CODEX_NAME}\b(?=\s+(?:start|build|fix|implement|run|test|create|add|write|check|continue|improve|refactor|review|debug|install|set\s+up|prepare|open|connect|otw[oó]rz|otworzy[lł])\b)",
    rf"\b(?:hej\s+)?omi\s+(?:to\s+)?(?:jest\s+)?(?:do\s+)?(?:ciebie|{CODEX_NAME})\b",
    rf"\b(?:to\s+)?(?:jest\s+)?do\s+(?:ciebie|{CODEX_NAME}a|{CODEX_NAME}u)\b",
    rf"\b(?:powiedz|zapytaj|popro[sś]|daj\s+zna[ćc])\s+(?:{CODEX_NAME}|{CODEX_NAME}owi|{CODEX_NAME}a|{CODEX_NAME}u|ciebie)\s+(?:[żz]eby|aby|by|to)?\b",
    rf"\b{CODEX_NAME}\b(?=\s+(?:prosz[ęe]|zr[oó]b|napraw|dodaj|stw[oó]rz|utw[oó]rz|uruchom|sprawd[źz]|przetestuj|kontynuuj|popraw|ogarnij|ustaw|zainstaluj|pod[łl][aą]cz|po[łl][aą]cz|przygotuj)\b)",
    r"\b(?:hej\s+)?omi\s+(?:to\s+)?(?:jest\s+)?do\s+ciebie\b",
]

LEADING_FILLER_PATTERN = re.compile(
    r"^(?:please|pls|prosz[ęe]|to|[żz]eby|aby|by|no|teraz|mi|dla\s+mnie|dla\s+nas)\b[\s,.:;-]*",
    flags=re.IGNORECASE,
)


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
    while True:
        stripped = LEADING_FILLER_PATTERN.sub("", prompt, count=1).strip()
        if stripped == prompt:
            break
        prompt = stripped
    if len(prompt) < 6:
        return None
    return prompt


def dedupe_key(uid: str, session_id: str, prompt: str) -> str:
    payload = f"{uid}|{session_id}|{prompt.strip().lower()}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
