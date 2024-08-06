# pylint: disable=missing-docstring
from pathlib import Path
from unittest import mock

import unittest_fixtures as uf
from tests import fixtures, fixtures1


@uf.requires("test_class")
class GetResulTests(uf.BaseTestCase):
    # pylint: disable=protected-access
    def test_when_given_generator_function(self) -> None:
        return_value = object()
        test = self.fixtures.test_class()
        test._options = {}
        test.fixtures = uf.Fixtures(name="test", foo="bar")
        self.assertEqual(len(test._cleanups), 0)

        def func(_options: uf.FixtureOptions, _fixtures: uf.Fixtures) -> object:
            yield return_value

        result = uf.get_result(func, test)

        self.assertEqual(result, return_value)
        self.assertEqual(len(test._cleanups), 1)

    def test_calls_func_with_fixture_and_options(self) -> None:
        return_value = object()
        func = mock.Mock(spec=uf.FixtureFunction, return_value=return_value)
        test = self.fixtures.test_class()
        test._options = {}
        test.fixtures = uf.Fixtures(name="test", foo="bar")

        result = uf.get_result(func, test)
        self.assertEqual(result, return_value)
        func.assert_called_once_with(test._options, test.fixtures)


@uf.requires("cd_to_tmpdir", "clear_cache")
class GetFixturesModuleTests(uf.BaseTestCase):
    def test_defaults_to_tests_fixtures(self) -> None:
        fixtures_module = uf.get_fixtures_module()

        self.assertIs(fixtures_module, fixtures)

    def test_with_speficied_module(self) -> None:
        project_toml_path: Path = self.fixtures.tmpdir / "pyproject.toml"
        project_toml_path.write_text(PYPROJECT_TOML % "tests.fixtures1")

        fixtures_module = uf.get_fixtures_module()

        self.assertIs(fixtures_module, fixtures1)


PYPROJECT_TOML = """\
[tool.unittest-fixtures]
fixtures-module = "%s"
"""
