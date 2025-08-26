"""Fixtures framework"""

from unittest_fixtures.fixtures import UnittestFixtures
from unittest_fixtures.parametrized import parametrized
from unittest_fixtures.types import (
    FixtureContext,
    FixtureFunction,
    Fixtures,
    Param,
    TestCaseClass,
)

__all__ = (
    "FixtureContext",
    "FixtureFunction",
    "Fixtures",
    "Param",
    "TestCaseClass",
    "combine",
    "fixture",
    "given",
    "parametrized",
    "params",
    "where",
)


# UnitestFixtures "singleton". We only expose a few choice methods.
_uf = UnittestFixtures()
combine = _uf.combine
fixture = _uf.fixture
given = _uf.given
params = _uf.params
where = _uf.where

del _uf
