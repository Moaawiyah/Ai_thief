# CODEX.md

## Project Overview

This is a university final project implementing a distributed
**Police vs. Thief (Cops-and-Robbers) game over a Peer-to-Peer network**.

The system consists of two independent agents:

- Police
- Thief

Each agent runs as an independent process and communicates directly with the
other peer.

**This repository is the THIEF agent only.** The Police agent is maintained in
the separate repository:

https://github.com/Moaawiyah/police-agent

The specification requires the two agents to live in separate repositories and
run as completely separate processes. Sharing memory, importing a shared
module that holds live state, or reading shared variables between the two
sides disqualifies the solution even if the game technically works.

Consequences for work in this repo:

- do not add Police agent logic here;
- do not add a `config/police/` directory here;
- the Thief owns its private true state and evaluates its own survival,
  capture claims, barrier capture, and confinement conditions;
- Police barriers may be recorded only as inbound observations;
- the Police is never an in-process object at runtime; for testing, use a
  deterministic test double under `tests/`.

The project includes several major areas:

- deterministic board and game rules;
- Thief movement and observed Police barriers;
- capture and scoring rules;
- peer-to-peer communication using FastMCP;
- commit-reveal and verification mechanisms;
- partial observability;
- scent information;
- Bayesian belief maps;
- Thief strategy;
- optional LLM/template-based language interaction;
- GUI / heatmap visualization;
- game logging and replay;
- reporting and interoperability with the Police peer.

The game engine and authoritative movement/rules must be implemented
deterministically in Python.

Strategy must remain separated from game rules.

The project should be developed incrementally:

1. Project setup
2. Core game/domain rules
3. Local playable simulation
4. P2P/FastMCP communication
5. Commit-reveal/security
6. Scent and belief system
7. Thief strategy
8. GUI, replay and reporting
9. Final integration and interoperability testing

Do not implement the entire project at once.

For each development step:

- understand the requirement;
- inspect existing code;
- implement a small coherent feature;
- test it;
- verify existing functionality still works;
- then continue to the next feature.

---

## Repository Boundary

The Thief-specific package is `src/thief_agent/`.

Keep these files compatible with the Police repository:

- `config/thief/game.json`;
- `src/thief_agent/constants.py`;
- `src/thief_agent/domain/`;
- tests that protect deterministic wire-facing behavior.

Keep these files Thief-specific:

- `config/thief/game.toml.example`;
- the `thief_agent` entrypoint;
- Thief strategy, orchestration, networking, reporting, and their tests.

When a compatibility file changes, port the same change to the Police
repository and run both repositories' test suites.

---

## Official Specification

The official project specification is the source of truth.

When implementing a feature, always distinguish between:

1. what the specification requires;
2. what the reference repository does;
3. our own design or strategy decisions.

If the specification and reference implementation differ, follow the official
specification.

Do not invent important game or protocol rules when the specification is
unclear. Identify the ambiguity first.

The product requirements for this repository are recorded in [`PRD.md`](PRD.md).

---

## Reference Implementation

Use the following repository as an educational/reference implementation:

https://github.com/rmisegal/Game-P2P-Cop-Chase

You may inspect it to understand:

- project structure;
- architecture;
- board and game representation;
- FastMCP communication;
- peer orchestration;
- configuration;
- commit-reveal implementation;
- logging and replay;
- scent and belief representation;
- strategy interfaces;
- GUI organization;
- testing approaches.

The repository is a reference, not automatically the required design. Do not
blindly copy its implementation.

Before reusing or adapting an idea from it:

1. understand what the code does;
2. determine why it exists;
3. compare it with the official specification;
4. decide whether it fits this Thief architecture;
5. implement or adapt it cleanly.

Do not assume the reference Police or Thief strategy is the strategy we should
submit. Thief strategy is an area we may design and improve ourselves.

---

## Development Guidelines

Use:

- Python;
- `uv` for project and dependency management;
- `pytest` for testing;
- `pytest-cov` for coverage;
- Ruff for linting and formatting.

Project requirements include:

- minimum 85% test coverage;
- zero Ruff violations;
- maximum 150 lines of code per Python source or test file;
- SDK  architecture;
- no hardcoded secrets;
- meaningful tests for new functionality.
- ensure OOP structure.
Keep game/domain logic independent from networking, GUI, and LLM code.

Do not use an LLM as the authoritative game-rule or movement engine.

Do not expose the Thief's private true state to the Police unless the
specification explicitly allows that information to be communicated.

---

## Working Rule

When given a task, work only on that task.

Before modifying an existing subsystem:

1. inspect the relevant implementation;
2. inspect its tests;
3. understand the current execution flow;
4. compare it with the specification and `PRD.md`;
5. make the smallest necessary change.

Do not automatically implement future parts of the project.

The goal is to build the Thief peer step-by-step so that every completed stage
is understandable, testable, secure, and interoperable with the Police peer.
