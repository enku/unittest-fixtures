# pylint: disable=missing-docstring
import unittest_fixtures as uf


@uf.depends()
def test_a(_options: uf.FixtureOptions, _fixtures: uf.Fixtures) -> str:
    return "test_a"
