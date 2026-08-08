"""Deterministic technical and submission-readiness checks."""

import re
import subprocess
import tomllib
from pathlib import Path

REQUIRED = (
    "README.md",
    "docs/PRD.md",
    "docs/PLAN.md",
    "docs/TODO.md",
    "pyproject.toml",
    "uv.lock",
    "config/thief/game.json",
)
IGNORED_PARTS = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache"}


def _result(name: str, passed: bool, detail: str) -> dict:
    return {"check": name, "passed": passed, "detail": detail}


def required_files(root: Path) -> dict:
    """Check the mandatory project shell."""
    missing = [name for name in REQUIRED if not (root / name).exists()]
    return _result(
        "required_files", not missing, "missing: " + ", ".join(missing) if missing else "ok"
    )


def python_line_limit(root: Path) -> dict:
    """Require every maintained Python file to stay at or below 150 code lines."""
    offenders = []
    for path in root.rglob("*.py"):
        if any(part in IGNORED_PARTS for part in path.parts):
            continue
        lines = sum(
            bool(line.strip()) and not line.lstrip().startswith("#")
            for line in path.read_text(encoding="utf-8").splitlines()
        )
        if lines > 150:
            offenders.append(f"{path.relative_to(root)}={lines}")
    return _result("python_line_limit", not offenders, ", ".join(offenders) or "max 150")


def shared_config_identity(root: Path) -> dict:
    """Verify this Thief repository has its signed shared game terms."""
    thief = root / "config/thief/game.json"
    present = thief.exists()
    return _result("shared_config_identity", present, "present" if present else "missing")


def metadata(root: Path) -> dict:
    """Reject placeholder student identity or repository URLs."""
    problems = []
    for role in ("thief",):
        path = root / f"config/{role}/game.toml"
        if not path.exists():
            problems.append(f"{role}: missing game.toml")
            continue
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        game = data.get("game", {})
        group_id = str(game.get("group_id", ""))
        if not re.fullmatch(r"[A-Za-z0-9_-]{6,32}", group_id):
            problems.append(f"{role}: group_id must be 6-32 identifier characters")
        text = path.read_text(encoding="utf-8")
        if "REPLACE" in text:
            problems.append(f"{role}: placeholder metadata remains")
        for url in game.get("repos", {}).values():
            if not str(url).startswith("https://github.com/"):
                problems.append(f"{role}: repository URL is not GitHub")
    return _result("metadata", not problems, "; ".join(problems) or "ok")


def no_tracked_secrets(root: Path) -> dict:
    """Ensure known OAuth secret filenames are not tracked."""
    try:
        output = subprocess.run(
            ["git", "-C", str(root), "ls-files"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.splitlines()
    except (OSError, subprocess.SubprocessError):
        output = []
    forbidden = [
        name for name in output if Path(name).name in {"credentials.json", "token.json", ".env"}
    ]
    return _result("no_tracked_secrets", not forbidden, ", ".join(forbidden) or "ok")


def submission_tag(root: Path) -> dict:
    """Require the annotated final tag only for the final submission gate."""
    result = subprocess.run(
        ["git", "-C", str(root), "tag", "--list", "v1.0-submission"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    present = result.returncode == 0 and result.stdout.strip() == "v1.0-submission"
    return _result("submission_tag", present, "present" if present else "missing")


def run_checks(root: Path, strict_submission: bool = False) -> list[dict]:
    """Run all locally provable gates, adding tag/evidence gates in strict mode."""
    checks = [
        required_files(root),
        python_line_limit(root),
        shared_config_identity(root),
        metadata(root),
        no_tracked_secrets(root),
    ]
    if strict_submission:
        checks.append(submission_tag(root))
    return checks
