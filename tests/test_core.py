# pylint: disable=missing-docstring,protected-access
import builtins
import unittest.result
from unittest import TestCase, mock

from unittest_fixtures import (
    _DEPS,
    FixtureContext,
    Fixtures,
    fixture,
    get_fixtures_module,
    given,
    parametrized,
    where,
)

from . import fixtures as fixtures_module


class FixtureTests(TestCase):
    def test_has_deps(self) -> None:
        @fixture()
        def f(_options: None, _fixtures: Fixtures) -> None:
            return

        self.assertEqual({}, _DEPS[f])

    def test_unnamed_deps(self) -> None:
        @fixture()
        def fixture_a(_options: None, _fixtures: Fixtures) -> None:
            return

        @fixture()
        def fixture_b(_options: None, _fixtures: Fixtures) -> None:
            return

        @fixture(fixture_a, fixture_b)
        def fixture_c(_options: None, _fixtures: Fixtures) -> None:
            return

        expected = {"fixture_a": fixture_a, "fixture_b": fixture_b}
        self.assertEqual(expected, _DEPS[fixture_c])

    def test_named_deps(self) -> None:
        @fixture()
        def fixture_a(_options: None, _fixtures: Fixtures) -> None:
            return

        @fixture()
        def fixture_b(_options: None, _fixtures: Fixtures) -> None:
            return

        @fixture(a=fixture_a, b=fixture_b)
        def fixture_c(_options: None, _fixtures: Fixtures) -> None:
            return

        expected = {"a": fixture_a, "b": fixture_b}
        self.assertEqual(expected, _DEPS[fixture_c])


class RequiresTests(TestCase):
    @staticmethod
    @fixture()
    def fixture_a(_options: None, _fixtures: Fixtures) -> str:
        return "a"

    @staticmethod
    @fixture()
    def fixture_b(_options: None, _fixtures: Fixtures) -> str:
        return "b"

    @staticmethod
    @fixture(fixture_a, fixture_b)
    def fixture_c(_options: None, fixtures: Fixtures) -> str:
        return fixtures.fixture_a + fixtures.fixture_b  # type: ignore

    def test_unnamed_deps(self) -> None:
        @given(self.fixture_a)
        class MyTestCase(TestCase):
            def test(self, fixtures: Fixtures) -> None:
                self.assertEqual(Fixtures(fixture_a="a"), fixtures)

        result = MyTestCase("test").run()
        assert_test_result(self, result)

    def test_named_deps(self) -> None:
        @given(a=self.fixture_a, b=self.fixture_b)
        class MyTestCase(TestCase):
            def test(self, fixtures: Fixtures) -> None:
                expected = Fixtures(a="a", b="b")
                self.assertEqual(expected, fixtures)

        result = MyTestCase("test").run()
        assert_test_result(self, result)

    def test_fixture_depending_fixture(self) -> None:
        @given(c=self.fixture_c)
        class MyTestCase(TestCase):
            def test(self, fixtures: Fixtures) -> None:
                expected = Fixtures(fixture_a="a", fixture_b="b", c="ab")
                self.assertEqual(expected, fixtures)

        result = MyTestCase("test").run()
        assert_test_result(self, result)

    def test_setup(self) -> None:
        ran = False

        @given(self.fixture_a)
        class MyTestCase(TestCase):
            def test(self, fixtures: Fixtures) -> None:
                assert hasattr(fixtures, "fixture_a")
                nonlocal ran
                ran = not ran

        result = MyTestCase("test").run()

        assert_test_result(self, result)
        self.assertTrue(ran)

    def test_fixture_generator(self) -> None:
        ran = False

        @fixture()
        def f(_options: None, _fixtures: Fixtures) -> FixtureContext[int]:
            nonlocal ran
            yield 6
            ran = True

        @given(f)
        class MyTestCase(TestCase):
            def test(self, fixtures: Fixtures) -> None:
                self.assertEqual(6, fixtures.f)

        result = MyTestCase("test").run()
        assert_test_result(self, result)

        self.assertTrue(ran)

    def test_with_options(self) -> None:
        @fixture()
        def echo(options: str | None, _fixtures: Fixtures) -> str:
            return options or ""

        @where(echo="Hello World!")
        @given(echo)
        class MyTestCase(TestCase):
            def test(self, fixtures: Fixtures) -> None:
                self.assertEqual("Hello World!", fixtures.echo)

        result = MyTestCase("test").run()
        assert_test_result(self, result)

    def test_inherits_parents_options(self) -> None:
        @fixture()
        def echo(options: str | None, _fixtures: Fixtures) -> str:
            return options or ""

        @given(echo)
        @where(echo="Hello World!")
        class MyBaseTestCase(TestCase):
            pass

        @given(echo)
        class MyTestCase(MyBaseTestCase):
            def test(self, fixtures: Fixtures) -> None:
                self.assertEqual("Hello World!", fixtures.echo)

        result = MyTestCase("test").run()
        assert_test_result(self, result)

    def test_overrides_parents_options(self) -> None:
        @fixture()
        def echo(options: str | None, _fixtures: Fixtures) -> str:
            return options or ""

        @given(echo)
        @where(echo="Hello World!")
        class MyBaseTestCase(TestCase):
            pass

        @given(echo)
        @where(echo="override!")
        class MyTestCase(MyBaseTestCase):
            def test(self, fixtures: Fixtures) -> None:
                self.assertEqual("override!", fixtures.echo)

        result = MyTestCase("test").run()
        assert_test_result(self, result)


class CommonDepsTests(TestCase):
    @staticmethod
    @fixture()
    def fixture_a(_options: None, _fixtures: Fixtures) -> str:
        return "a"

    @staticmethod
    @fixture(fixture_a)
    def fixture_b(_options: None, _fixtures: Fixtures) -> str:
        return "b"

    @staticmethod
    @fixture(fixture_a)
    def fixture_c(_options: None, _fixtures: Fixtures) -> str:
        return "c"

    def test(self) -> None:
        @given(c=self.fixture_c, b=self.fixture_b, z=self.fixture_c)
        class MyTestCase(TestCase):
            def test(self, fixtures: Fixtures) -> None:
                self.assertEqual(Fixtures(fixture_a="a", b="b", c="c", z="c"), fixtures)

        result = MyTestCase("test").run()
        assert_test_result(self, result)


class LoadTests(TestCase):
    def test_by_string(self) -> None:
        get_fixtures_module.cache_clear()

        @fixture("test_a")
        def f(_options: None, fixtures: Fixtures) -> str:
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
        with mock.patch.object(builtins, "open") as mock_open:
            mock_open.side_effect = FileNotFoundError
            module = get_fixtures_module()

        assert module is fixtures_module


class ParametrizeTests(TestCase):
    values = {1, 2}

    @parametrized([[1, values], [2, values], [None, values]])
    def test(self, value: int | None, values: set[int]) -> None:
        if value is not None:
            self.assertIn(value, values)
            values.discard(value)
            return
        self.assertEqual(set(), values)


def assert_test_result(
    self: TestCase, result: unittest.result.TestResult | None
) -> None:
    self.assertIsNotNone(result, "No result given")
    assert result

    if result.failures:
        msg = ""
        for failure in result.failures:
            msg = f"{msg}\n{'\n'.join(str(f) for f in failure)}"
            self.fail(msg)
    if result.errors:
        msg = ""
        for error in result.errors:
            msg = f"{msg}\n{'\n'.join(str(f) for f in error)}"
            self.fail(msg)
