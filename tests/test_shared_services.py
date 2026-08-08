"""Coverage for configuration, readiness, rate limiting, and API guards."""

from dataclasses import dataclass

import pytest

from thief_agent.exceptions import ConfigError, ProviderError, RateLimitError
from thief_agent.peer.sealing import validate_agreement, validate_config
from thief_agent.shared.agreement import validate_shared_config
from thief_agent.shared.config import ConfigManager
from thief_agent.shared.gatekeeper import ApiGatekeeper
from thief_agent.shared.rate_limiter import RateLimiter
from thief_agent.shared.readiness import (
    metadata,
    no_tracked_secrets,
    python_line_limit,
    required_files,
    run_checks,
    shared_config_identity,
)


@dataclass
class Clock:
    now: float = 0

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.now += 60


class ServiceConfig:
    def __init__(self, **service):
        base = {
            "requests_per_minute": 100,
            "concurrent_max": 2,
            "retry_after_seconds": 0,
            "max_retries": 1,
            "daily_quota": 100,
            "circuit_breaker_failures": 3,
            "circuit_breaker_cooldown_seconds": 60,
        }
        base.update(service)
        self.rate_limits = {"services": {"test": base}, "queue": {
            "max_depth": 2, "drain_interval_seconds": 1, "timeout_seconds": 2
        }}

    def service_limits(self, name):
        return self.rate_limits["services"].get(name, {})


def test_rate_limiter_grants_and_times_out_queued_callers():
    clock = Clock()
    limits = {"requests_per_minute": 1}
    queue = {"max_depth": 1, "drain_interval_seconds": 1, "timeout_seconds": 2}
    limiter = RateLimiter(limits, queue, clock)
    limiter.acquire()
    limiter.acquire()
    assert limiter.queue_depth == 0

    full = RateLimiter(limits, {**queue, "max_depth": 0}, Clock())
    full.acquire()
    with pytest.raises(RateLimitError, match="queue full"):
        full.acquire()


def test_gatekeeper_retries_provider_failures_and_reports_usage(monkeypatch):
    monkeypatch.setattr("thief_agent.shared.gatekeeper.time.sleep", lambda _: None)
    gate = ApiGatekeeper(ServiceConfig(), "test")
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) == 1:
            raise ProviderError("temporary")
        return "ok"

    assert gate.execute(flaky) == "ok"
    assert len(calls) == 2
    assert gate.get_queue_status()["failures_total"] == 1


def test_gatekeeper_enforces_quota_and_opens_circuit():
    quota = ApiGatekeeper(ServiceConfig(daily_quota=0), "test")
    with pytest.raises(RateLimitError, match="daily quota"):
        quota.execute(lambda: None)

    circuit = ApiGatekeeper(ServiceConfig(max_retries=0, circuit_breaker_failures=1), "test")
    with pytest.raises(ProviderError):
        circuit.execute(lambda: (_ for _ in ()).throw(ProviderError("down")))
    with pytest.raises(RateLimitError, match="circuit"):
        circuit.execute(lambda: None)


def test_thief_config_and_readiness_gates_pass_on_repository_root():
    config = ConfigManager("config/thief")
    validate_config(config)
    validate_agreement(config)
    validate_shared_config(config.shared)
    root = config.directory.parent.parent
    assert required_files(root)["passed"]
    assert shared_config_identity(root)["passed"]
    assert metadata(root)["passed"]
    assert no_tracked_secrets(root)["passed"]
    assert python_line_limit(root)["passed"]
    assert all(item["passed"] for item in run_checks(root))


def test_invalid_opponent_url_is_rejected_before_startup():
    config = ConfigManager("config/thief")
    config.override("network.opponent_url", "ftp://not-an-mcp-server")
    with pytest.raises(ConfigError, match="http:// or https://"):
        validate_agreement(config)
