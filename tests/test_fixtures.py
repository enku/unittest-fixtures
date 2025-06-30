# pylint: disable=missing-docstring

from unittest import TestCase

from unittest_fixtures import Fixtures, fixture, given, load

from . import assert_test_result

load("tests.fixtures")


class LoadFixtureTests(TestCase):
    def test_by_string(self) -> None:
        @fixture("test_a")
        def f(fixtures: Fixtures) -> str:
            self.assertEqual(fixtures, Fixtures(test_a="test_a"))
            return "fixture"

        @given(f)
        class MyTestCase(TestCase):
            def test(self, fixtures: Fixtures) -> None:
                self.assertEqual(fixtures, Fixtures(test_a="test_a", f="fixture"))

        result = MyTestCase("test").run()
        assert_test_result(self, result)
