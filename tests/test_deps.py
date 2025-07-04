# pylint: disable=missing-docstring
from unittest import TestCase

from unittest_fixtures import Fixtures, given

from .other_fixtures import other


@given(other)
class FixtureDependencyTests(TestCase):
    def test(self, fixtures: Fixtures) -> None:
        pass
