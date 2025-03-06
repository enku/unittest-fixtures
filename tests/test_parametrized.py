# pylint: disable=missing-docstring
from unittest import TestCase

from unittest_fixtures import parametrized


class ParametrizeTests(TestCase):
    values = {1, 2}

    @parametrized([[1, values], [2, values], [None, values]])
    def test(self, value: int | None, values: set[int]) -> None:
        if value is not None:
            self.assertIn(value, values)
            values.discard(value)
            return
        self.assertEqual(set(), values)
