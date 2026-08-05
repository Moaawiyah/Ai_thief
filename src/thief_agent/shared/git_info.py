"""Resolve the exact source revision placed in Step-0 and result artifacts."""

import subprocess
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def code_revision() -> dict[str, object]:
    """Return the current Git commit and whether uncommitted code is present."""
    root = Path(__file__).resolve().parents[3]
    try:
        head = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "-C", str(root), "status", "--porcelain"],
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            ).stdout.strip()
        )
        return {"commit": head, "dirty": dirty}
    except (OSError, subprocess.SubprocessError):
        return {"commit": "unknown", "dirty": True}
