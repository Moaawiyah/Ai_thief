"""Build the official Hebrew JSON match report from one peer's summary.

Schema follows the assignment's official report language (course book section
8), scoped to a single match; the consensus signature is SHA-256 over the
canonical report body.
"""

import hashlib
import json

from thief_agent.shared.version import CODE_VERSION

__all__ = ["consensus_signature", "build_report"]

_RESULT_HEBREW = {
    "capture": "לכידה",
    "survival": "הישרדות",
    "timeout": "תוצאה_טכנית",
    "tamper_forfeit_opponent": "פסילת_זיוף_של_היריב",
}


def consensus_signature(data: dict) -> str:
    """SHA-256 over canonical (sorted-keys) JSON — key order never matters."""
    canonical = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _step_log(summary: dict) -> list[dict]:
    """Merge received messages into the book's verified step-log shape."""
    return [
        {
            "מספר_צעד": message["step"],
            "טביעת_זמן": message["timestamp"],
            "שולח": message["sender"],
            "רמז_מילולי_שנשלח": message["hint"],
            "גריד_ריח_מצורף": message["smell_grid"],
            "מחסום_שהוצב": message["barrier_placed"],
            "חתימת_מצב": message["commit"],
        }
        for message in summary["history"]
    ]


def build_report(summary: dict, config, terms: dict) -> dict:
    """The official report from MY peer's perspective (audit-verified)."""
    audit = summary["audit"]
    report = {
        "סוג_דוח": "משחק_ליגה_רשמי",
        "גרסת_קוד": CODE_VERSION,
        "תפקיד_מדווח": summary["role"],
        "קבוצה_מדווחת": summary.get("group_name", "unnamed"),
        "מספר_משחקון": summary.get("sub_game_number", 1),
        "זמן_התחלה": summary.get("started_at", ""),
        "משך_משחק_שניות": summary.get("duration_seconds", 0),
        "סך_טוקנים_שנצרכו": summary.get("tokens_total", 0),
        "תוצאה": _RESULT_HEBREW.get(summary["result"], summary["result"]),
        "מנצח": summary["winner"],
        "צעדים_שבוצעו": summary["steps"],
        "הסכם_תפאורה_משא_ומתן": terms,
        "אימות_קריפטוגרפי": {
            "צעדים_מאומתים": audit["own"]["verified_steps"],
            "צעדים_שנכשלו": audit["own"]["failed_steps"],
        },
        "לוג_צעדים_מאומת": _step_log(summary),
        "הצהרות_חתומות_שלי": summary["records"],
        "הסכמה_הדדית": audit["passed"],
    }
    report["חתימת_קונסנזוס_משותפת"] = consensus_signature(report)
    return report
