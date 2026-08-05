"""Series looping over a shared transport (no process restart between sub-games)."""

import queue
import threading

from tests.runtime_support import PoliceDouble, QueueTransport
from tests.test_runtime import config
from thief_agent.sdk.series import run_series


def _run_police_series(cfg, transport, count: int, results: list) -> None:
    for _ in range(count):
        results.append(PoliceDouble(cfg, transport, scenario="survival").run())


def test_run_series_plays_every_sub_game_with_a_shared_transport(tmp_path):
    cfg = config(tmp_path)
    cfg.override("game.num_games", 3)
    incoming, outgoing = queue.Queue(), queue.Queue()
    thief_transport = QueueTransport(incoming, outgoing)
    police_transport = QueueTransport(outgoing, incoming)

    police_results: list[dict] = []
    thread = threading.Thread(
        target=_run_police_series, args=(cfg, police_transport, 3, police_results)
    )
    thread.start()
    series = run_series(cfg, thief_transport)
    thread.join(timeout=10)

    assert [s["result"] for s in series.summaries] == ["survival"] * 3
    assert [s["sub_game_number"] for s in series.summaries] == [1, 2, 3]
    assert series.game_id and series.game_uid
