"""Global version tracking for code and config."""

from pathlib import Path

CODE_VERSION = "1.0.0"
BOOK_VERSION = "3.0.0"  # shared assignment guidelines-book version this peer targets
SUPPORTED_CONFIG_VERSIONS = ["1.10"]
SUPPORTED_SHARED_SCHEMA_VERSIONS = ["1.3"]

# Short suffix shown in the GUI title bar.
COPYRIGHT_TITLE = "Thief Agent"

# Shown in Help -> About.
LICENSE_NOTICE = (
    "Thief Agent - a companion peer implementation for the Police/Thief "
    "pursuit-game assignment.\n\n"
    "See the repository's own LICENSE (if any) and the shared assignment "
    "guidelines book for applicable terms."
)

# The bundled guidelines PDF, if present (repo_root/docs/police_thief_p2p.pdf).
GUIDELINES_PDF = Path(__file__).resolve().parents[3] / "docs" / "police_thief_p2p.pdf"
