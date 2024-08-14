"""Dummy fixtures module for tests"""

# pylint: disable=missing-docstring

import unittest_fixtures as uf


def test1(_options: uf.FixtureOptions, _fixtures: uf.Fixtures) -> str:
    return "test1"


def test2(_options: uf.FixtureOptions, _fixtures: uf.Fixtures) -> str:
    return "test2"


@uf.depends(test2)
def test3(options: uf.FixtureOptions, fixtures: uf.Fixtures) -> str:
    spacer: str = options.get("spacer", " ")
    prefix: str = fixtures.test2
    return prefix + spacer + "test3"
