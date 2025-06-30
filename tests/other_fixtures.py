# pylint: disable=missing-docstring
import unittest_fixtures as uf


@uf.fixture()
def other(_fixtures: uf.Fixtures) -> str:
    return "other"
