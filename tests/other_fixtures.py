# pylint: disable=missing-docstring
import unittest_fixtures as uf

from .fixtures import test_a


@uf.fixture(test_a)
def other(_fixtures: uf.Fixtures) -> str:
    return "other"
