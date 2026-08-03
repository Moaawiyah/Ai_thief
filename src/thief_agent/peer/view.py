"""Immutable live snapshots consumed by the GUI."""


def snapshot(runtime) -> dict:
    state = runtime.state
    return {
        "role": "thief",
        "step": state.step_number,
        "position": state.position,
        "visited": frozenset(state.visited),
        "barriers": frozenset(state.barriers),
        "belief": belief_matrix(runtime.belief, state.board.size),
    }


def belief_matrix(belief, board_size: int) -> list[list[float]]:
    as_matrix = getattr(belief, "as_matrix", None)
    if as_matrix is None:
        flat = 1.0 / (board_size * board_size)
        return [[flat] * board_size for _ in range(board_size)]
    return as_matrix()
