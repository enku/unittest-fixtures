# pylint: disable=missing-docstring

import importlib
from unittest import TestCase, mock

from unittest_fixtures import Fixtures, fixture, given
from unittest_fixtures.fixtures import get_fixtures_module

from . import assert_test_result


class LoadTests(TestCase):
    def test_by_string(self) -> None:
        get_fixtures_module.cache_clear()

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


class GetFixturesModuleTests(TestCase):
    def test_with_missing_pyproject_toml(self) -> None:
        fixtures_module = importlib.import_module("tests.fixtures")
        get_fixtures_module.cache_clear()

        with mock.patch("unittest_fixtures.fixtures.open") as mock_open:
            mock_open.side_effect = FileNotFoundError
            module = get_fixtures_module()

        self.assertIs(module, fixtures_module)
        mock_open.assert_called_once_with("pyproject.toml", "rb")
