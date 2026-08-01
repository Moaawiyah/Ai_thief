import police_thief
from police_thief import domain, infra, peer, shared
from police_thief.constants import Role


def test_package_importable():
    assert police_thief is not None
    assert police_thief.ROLE is Role.THIEF


def test_subpackages_importable():
    assert domain is not None
    assert infra is not None
    assert peer is not None
    assert shared is not None
