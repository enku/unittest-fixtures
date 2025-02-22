# pylint: disable=missing-docstring
import unittest_fixtures as uf


@uf.fixture()
def test_a(_fixtures: uf.Fixtures) -> str:
    return "test_a"
