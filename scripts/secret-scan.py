#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {
    ".git",
    ".next",
    ".pytest_cache",
    ".terraform",
    ".venv",
    "dist",
    "node_modules",
    "out",
    "playwright-report",
    "test-results",
}
SKIP_FILES = {
    "package-lock.json",
    "terraform.tfstate",
    "terraform.tfstate.backup",
}
PATTERNS = {
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "aws_secret_key": re.compile(r"\baws_secret_access_key\s*=\s*['\"]?[A-Za-z0-9/+=]{40}['\"]?", re.IGNORECASE),
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{30,}\b"),
    "slack_token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
}


def iter_files():
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        if path.name in SKIP_FILES:
            continue
        yield path


def main() -> int:
    findings: list[str] = []
    for path in iter_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        rel = path.relative_to(ROOT)
        for label, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                findings.append(f"{rel}:{line}: potential {label}")

    if findings:
        print("Potential secrets found:")
        for finding in findings:
            print(f"  {finding}")
        return 1

    print("Secret scan passed: no high-confidence secrets found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
