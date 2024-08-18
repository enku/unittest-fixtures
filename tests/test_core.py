# pylint: disable=missing-docstring
from pathlib import Path
from unittest import mock

import unittest_fixtures as uf
from tests import fixtures, fixtures1


@uf.requires("cd_to_tmpdir", "clear_cache")
class FunctionalTests(uf.BaseTestCase):
    def test(self) -> None:
        project_toml_path: Path = self.fixtures.tmpdir / "pyproject.toml"
        project_toml_path.write_text(PYPROJECT_TOML % "tests.fixtures1")

        @uf.requires("test1", "test3")
        class TestTest(uf.BaseTestCase):
            options = {"spacer": "@"}

        test_obj = TestTest()
        test_obj.setUp()

        self.assertEqual(test_obj.fixtures.test1, "test1")
        self.assertEqual(test_obj.fixtures.test2, "test2")
        self.assertEqual(test_obj.fixtures.test3, "test2@test3")

    def test_inheritance(self) -> None:
        project_toml_path: Path = self.fixtures.tmpdir / "pyproject.toml"
        project_toml_path.write_text(PYPROJECT_TOML % "tests.fixtures1")

        @uf.requires("test1", "test3")
        class TestTest1(uf.BaseTestCase):
            options = {"spacer": "@"}

        @uf.requires("test3")
        class TestTest2(TestTest1):
            options = {"spacer": "+"}

        test1_obj = TestTest1()
        test1_obj.setUp()

        test2_obj = TestTest2()
        test2_obj.setUp()

        self.assertEqual(test1_obj.fixtures.test1, "test1")
        self.assertEqual(test1_obj.fixtures.test2, "test2")
        self.assertEqual(test1_obj.fixtures.test3, "test2@test3")

        self.assertEqual(test2_obj.fixtures.test1, "test1")
        self.assertEqual(test2_obj.fixtures.test2, "test2")
        self.assertEqual(test2_obj.fixtures.test3, "test2@test3")


@uf.requires("clear_cache")
class LoadsTests(uf.BaseTestCase):
    def test_with_string(self) -> None:
        fixture_function = uf.load("one")

        self.assertIs(fixture_function, fixtures.one)

    def test_with_functon(self) -> None:
        fixture_function = uf.load(fixtures.one)

        self.assertIs(fixture_function, fixtures.one)


@uf.requires("fixture_function")
class DependsTests(uf.BaseTestCase):
    # pylint: disable=protected-access
    def test(self) -> None:
        func: uf.FixtureFunction = self.fixtures.fixture_function
        func = uf.depends("one", "two")(func)

        self.assertEqual(func._deps, ["one", "two"])


@uf.requires("clear_cache", "uf_requirements", "test_class")
class RequiresTests(uf.BaseTestCase):
    # pylint: disable=protected-access
    def test_with_no_requirements(self) -> None:
        test_case = uf.requires()(self.fixtures.test_class)

        self.assertEqual(uf._REQUIREMENTS, {test_case: {}})
        self.assertTrue(hasattr(test_case, "setUp"))

    def test_with_requirements(self) -> None:
        def local_fixture(_o: uf.FixtureOptions, _f: uf.Fixtures) -> str:
            return "test"

        test_case = uf.requires("one", local_fixture)(self.fixtures.test_class)

        self.assertEqual(
            uf._REQUIREMENTS,
            {test_case: {"one": fixtures.one, "local": local_fixture}},
        )
        self.assertTrue(hasattr(test_case, "setUp"))

        inst = test_case()
        inst.setUp()
        self.assertEqual(inst.fixtures, uf.Fixtures(one=1, local="test"))
        self.assertEqual(inst._options, {})


@uf.requires("test_class")
class AddFuncsTests(uf.BaseTestCase):
    def test_without_deps(self) -> None:
        test = self.get_test()
        specs = ["one", "two"]

        uf.add_funcs(test, specs)

        self.assertEqual(test.fixtures, uf.Fixtures(one=1, two=2))

    def test_with_deps(self) -> None:
        test = self.get_test()
        specs = ["three"]  # depends on two

        uf.add_funcs(test, specs)

        self.assertEqual(test.fixtures, uf.Fixtures(two=2, three=3))

    def test_with_fixture_suffix(self) -> None:
        test = self.get_test()
        specs = [fixtures.four_fixture]

        uf.add_funcs(test, specs)

        self.assertEqual(test.fixtures, uf.Fixtures(four=4))

    def get_test(self) -> uf.BaseTestCase:
        """Return initialized test from the fixture"""
        # pylint: disable=protected-access
        test: uf.BaseTestCase = self.fixtures.test_class()

        # .fixtures and ._options are normally set up in .setUp()
        test.fixtures = uf.Fixtures()
        test._options = {}

        return test


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
