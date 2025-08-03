"""Fixtures framework"""

from unittest_fixtures.fixtures import UnittestFixtures
from unittest_fixtures.parametrized import parametrized
from unittest_fixtures.types import (
    FixtureContext,
    FixtureFunction,
    Fixtures,
    TestCaseClass,
)

__all__ = (
    "FixtureContext",
    "FixtureFunction",
    "Fixtures",
    "TestCaseClass",
    "fixture",
    "given",
    "parametrized",
    "where",
)


# UnitestFixtures "singleton". We only expose a few choice methods.
_uf = UnittestFixtures()
fixture = _uf.fixture
given = _uf.given
where = _uf.where

del _uf
