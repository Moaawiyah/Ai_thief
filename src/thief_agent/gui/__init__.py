"""Tk live and replay views for the Thief peer."""

import os
import sys
from pathlib import Path


def point_tk_at_the_base_interpreter() -> None:
    """Help virtualenv Python find the system Tcl/Tk runtime when needed."""
    base = Path(sys.base_prefix)
    for variable, directory in (("TCL_LIBRARY", "tcl8.6"), ("TK_LIBRARY", "tk8.6")):
        candidate = base / "tcl" / directory
        if variable not in os.environ and candidate.is_dir():
            os.environ[variable] = str(candidate)


point_tk_at_the_base_interpreter()
