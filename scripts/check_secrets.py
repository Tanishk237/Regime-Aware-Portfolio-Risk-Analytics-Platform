#!/usr/bin/env python3
"""Reject credential-shaped values in tracked repository files."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


TOKEN_PATTERNS = {
    "NVIDIA API key": re.compile(r"nvapi-[A-Za-z0-9_-]{20,}"),
    "OpenAI API key": re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    "GitHub token": re.compile(
        r"(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"
    ),
    "AWS access key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "Google API key": re.compile(r"AIza[0-9A-Za-z_-]{30,}"),
    "private key": re.compile(
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
    ),
}
DATABASE_URL_PATTERN = re.compile(
    r"postgres(?:ql)?(?:\+psycopg)?://"
    r"(?P<username>[^\s:/?#]+):(?P<password>[^\s@/]+)@"
    r"(?P<host>[^\s/:?#]+\.(?:neon\.tech|supabase\.co|amazonaws\.com))"
)
ENVIRONMENT_REFERENCE_PATTERN = re.compile(r"\$\{[A-Z][A-Z0-9_]*\}")


def scan_text(text: str) -> list[tuple[int, str]]:
    """Return one-based line numbers and credential types found in text."""
    findings: list[tuple[int, str]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for credential_type, pattern in TOKEN_PATTERNS.items():
            if pattern.search(line):
                findings.append((line_number, credential_type))

        for match in DATABASE_URL_PATTERN.finditer(line):
            password = match.group("password")
            if not ENVIRONMENT_REFERENCE_PATTERN.fullmatch(password):
                findings.append((line_number, "cloud database credential"))

    return findings


def tracked_files(repository: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repository,
        check=True,
        capture_output=True,
    )
    return [repository / path for path in result.stdout.decode().split("\0") if path]


def main() -> int:
    repository = Path(__file__).resolve().parent.parent
    findings: list[str] = []

    for path in tracked_files(repository):
        try:
            contents = path.read_bytes()
        except OSError as exc:
            print(f"Could not read tracked file {path}: {exc}", file=sys.stderr)
            return 2

        if b"\0" in contents:
            continue

        relative_path = path.relative_to(repository)
        for line_number, credential_type in scan_text(
            contents.decode("utf-8", errors="replace")
        ):
            findings.append(f"{relative_path}:{line_number}: {credential_type}")

    if findings:
        print("Potential credentials found in tracked files:", file=sys.stderr)
        for finding in findings:
            print(f"  {finding}", file=sys.stderr)
        return 1

    print("No credential-shaped values found in tracked files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
