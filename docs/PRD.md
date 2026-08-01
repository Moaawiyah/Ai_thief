# Thief Agent Product Requirements

## 1. Product

The Thief Agent is one independent peer in the Police-vs-Thief game. It runs
as its own process, exposes a peer interface, makes legal Thief moves, and
proves the outcome of a sub-game from its authoritative private state.

The Police peer is maintained separately at:

https://github.com/Moaawiyah/police-agent

The official project specification remains the source of truth. This document
defines the ownership and acceptance boundary for this repository and records
the requirements needed for the final deliverable, including chapter 9.4.1.

## 2. Goals

- Implement a deterministic, testable Thief peer.
- Keep the Thief peer interoperable with the separate Police repository.
- Never expose the Thief's private true state except where the protocol allows.
- Keep strategy, networking, reporting, and game rules as separate layers.
- Produce verifiable logs and final reporting artifacts for an audited match.

## 3. Non-goals

- Implementing Police strategy or Police-owned barrier placement here.
- Maintaining a second copy of the Police peer's private configuration.
- Making an LLM authoritative for movement, legality, capture, or scoring.
- Introducing a central referee or game server.

## 4. Repository ownership

Thief-owned components:

- `src/thief_agent/` and its Thief-specific entrypoint;
- `config/thief/game.toml.example` and local Thief configuration;
- Thief strategy, peer orchestration, networking, reporting, and tests.

Compatibility components:

- `config/thief/game.json`, the Thief copy of the agreed game rules;
- deterministic board geometry, Thief actions, and wire-facing outcome values;
- tests that protect behavior shared across both peers.

Changes to compatibility components must be ported to the Police repository and
verified against both peers.

## 5. Functional requirements

### FR-1 — Identity and configuration

The installed package and executable must identify themselves as the Thief
peer. Configuration must select the Thief port, the Police opponent endpoint,
the Thief repository URL, and the shared game-rules copy.

### FR-2 — Legal actions

The Thief may move one orthogonal cell or hold. Diagonal movement, off-board
movement, movement through an observed barrier, and malformed actions must be
rejected without mutating authoritative state.

### FR-3 — Private state

The Thief must own its current position, visited cells, step count, and action
log. Police barriers may be recorded as observations; Police barrier quotas
and placement decisions must not exist in Thief-owned state.

### FR-4 — Terminal conditions

The Thief must evaluate survival, hard step timeout, capture claims, direct
barrier capture, and confinement capture from its own state.

### FR-5 — Peer protocol

The Thief peer must communicate directly with the Police peer over the agreed
peer protocol, validate inbound messages, enforce timeouts, and reject replayed
or malformed messages.

### FR-6 — Security and auditability

Moves and outcome claims must support the specified commit-reveal, signature,
nonce, and verification workflow. Logs must be sufficient to replay and audit
a completed sub-game without trusting an LLM or an external referee.

### FR-7 — Reporting

The final implementation must emit the result, replay/audit data, and the
required report or draft email described by the official specification's
chapter 9.4.1. Credentials must remain local and must never be committed.

## 6. Quality requirements

- Use Python with `uv`, pytest, pytest-cov, and Ruff.
- Keep deterministic domain code independent from FastMCP, GUI, email, and LLM
  integrations.
- Maintain at least 85% test coverage and zero Ruff violations.
- Keep source modules below the project limit of 150 lines where practical.
- Do not discard unrelated user changes or rewrite Git history.

## 7. Acceptance criteria

The Thief repository is ready for integration when:

- `uv run pytest` passes with at least 85% coverage;
- `uv run ruff check .` passes;
- `uv run thief-agent` starts the Thief entrypoint;
- the package contains no Police-owned barrier-placement implementation;
- a local Thief simulation can be tested against a deterministic test double;
- an interoperability test passes against `Moaawiyah/police-agent`;
- the chapter 9.4.1 report and audit artifacts are generated and reviewable.
