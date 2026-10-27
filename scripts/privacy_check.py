"""Heuristic publication check for candidate Git files; not a full secret scanner."""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GitHub token": re.compile(r"\b(?:gh[opusr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    "AWS access key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "OpenAI key": re.compile(r"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{24,}\b"),
}


def check() -> list[str]:
    names = (
        subprocess.check_output(
            ["git", "ls-files", "-c", "-o", "--exclude-standard", "-z"], cwd=ROOT
        )
        .decode()
        .split("\x00")
    )
    findings = []
    checked = 0
    for name in sorted(set(names) - {""}):
        path = ROOT / name
        if not path.is_file():
            continue  # Deleted tracked files will be removed by the checkpoint.
        checked += 1
        if (
            path.suffix.lower() in {".db", ".sqlite", ".sqlite3", ".key", ".pem", ".p12", ".log"}
            or path.name == ".env"
            or re.search(r"\.(?:db|sqlite3?)-(?:wal|shm)$", name)
            or any(
                part in {".venv", "venv", "backups", "uploads"}
                for part in path.relative_to(ROOT).parts
            )
        ):
            findings.append(f"Private/generated file candidate: {name}")
        if path.suffix.lower() == ".png":
            continue
        try:
            content = path.read_text(encoding="utf-8-sig")
        except UnicodeError:
            findings.append(f"Unreviewed binary candidate: {name}")
            continue
        for label, pattern in PATTERNS.items():
            if pattern.search(content):
                findings.append(f"Possible {label} in {name}")
    print(f"Reviewed {checked} candidate files; {len(findings)} heuristic findings.")
    return findings


def main() -> int:
    findings = check()
    for finding in findings:
        print(finding)  # Never print matched secret values.
    return bool(findings)


if __name__ == "__main__":
    raise SystemExit(main())
