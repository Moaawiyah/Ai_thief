import thief_agent
from thief_agent import domain, infra, peer, shared


def test_package_importable():
    assert thief_agent is not None
    assert thief_agent.PEER_ROLE == "thief"


def test_subpackages_importable():
    assert domain is not None
    assert infra is not None
    assert peer is not None
    assert shared is not None
