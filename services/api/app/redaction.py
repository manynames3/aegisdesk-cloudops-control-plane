from __future__ import annotations

import re

from .models import RedactionFinding, RedactionResult


PATTERNS: list[tuple[str, str, re.Pattern[str]]] = [
    ("email", "[REDACTED_EMAIL]", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)),
    ("ssn", "[REDACTED_SSN]", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    (
        "api_key",
        "[REDACTED_API_KEY]",
        re.compile(r"\b(?:sk|pk|ghp|gho|AKIA)[A-Za-z0-9_\-]{8,}\b"),
    ),
    (
        "credential",
        "[REDACTED_CREDENTIAL]",
        re.compile(r"\b(?:password|passwd|pwd|token|secret|api_key)\s*[:=]\s*[^\s,;]+", re.I),
    ),
]


def inspect_and_redact(text: str) -> RedactionResult:
    redacted = text
    findings: list[RedactionFinding] = []

    for kind, replacement, pattern in PATTERNS:
        matches = list(pattern.finditer(redacted))
        if not matches:
            continue

        for index, _match in enumerate(matches, start=1):
            findings.append(
                RedactionFinding(
                    kind=kind,  # type: ignore[arg-type]
                    label=f"{kind}_{index}",
                    replacement=replacement,
                )
            )
        redacted = pattern.sub(replacement, redacted)

    pii_detected = any(f.kind in {"email", "ssn"} for f in findings)
    secrets_detected = any(f.kind in {"api_key", "credential"} for f in findings)

    return RedactionResult(
        pii_detected=pii_detected,
        secrets_detected=secrets_detected,
        redacted_text=redacted,
        findings=findings,
    )

