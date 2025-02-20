# pylint: disable=missing-docstring,protected-access
import builtins
from unittest import mock

import unittest_fixtures as uf

from . import fixtures as fixtures_module


class DependsTests(uf.TestCase):
    def test_has_deps(self) -> None:
        @uf.depends()
        def fixture(_options: uf.FixtureOptions, _fixtures: uf.Fixtures) -> None:
            return

        self.assertEqual({}, uf._DEPS[fixture])

    def test_unnamed_deps(self) -> None:
        @uf.depends()
        def fixture_a(_options: uf.FixtureOptions, _fixtures: uf.Fixtures) -> None:
            return

        @uf.depends()
        def fixture_b(_options: uf.FixtureOptions, _fixtures: uf.Fixtures) -> None:
            return

        @uf.depends(fixture_a, fixture_b)
        def fixture_c(_options: uf.FixtureOptions, _fixtures: uf.Fixtures) -> None:
            return

        expected = {"fixture_a": fixture_a, "fixture_b": fixture_b}
        self.assertEqual(expected, uf._DEPS[fixture_c])

    def test_named_deps(self) -> None:
        @uf.depends()
        def fixture_a(_options: uf.FixtureOptions, _fixtures: uf.Fixtures) -> None:
            return

        @uf.depends()
        def fixture_b(_options: uf.FixtureOptions, _fixtures: uf.Fixtures) -> None:
            return

        @uf.depends(a=fixture_a, b=fixture_b)
        def fixture_c(_options: uf.FixtureOptions, _fixtures: uf.Fixtures) -> None:
            return

        expected = {"a": fixture_a, "b": fixture_b}
        self.assertEqual(expected, uf._DEPS[fixture_c])


class RequiresTests(uf.TestCase):
    @staticmethod
    @uf.depends()
    def fixture_a(_options: uf.FixtureOptions, _fixtures: uf.Fixtures) -> str:
        return "a"

    @staticmethod
    @uf.depends()
    def fixture_b(_options: uf.FixtureOptions, _fixtures: uf.Fixtures) -> str:
        return "b"

    @staticmethod
    @uf.depends(fixture_a, fixture_b)
    def fixture_c(_options: uf.FixtureOptions, fixtures: uf.Fixtures) -> str:
        return fixtures.fixture_a + fixtures.fixture_b  # type: ignore

    def test_unnamed_deps(self) -> None:
        @uf.requires(self.fixture_a)
        class MyTestCase(uf.TestCase):
            pass

        tc = MyTestCase()
        tc.setUp()

        self.assertEqual(uf.Fixtures(fixture_a="a"), tc.fixtures)

    def test_named_deps(self) -> None:
        @uf.requires(a=self.fixture_a, b=self.fixture_b)
        class MyTestCase(uf.TestCase):
            pass

        tc = MyTestCase()
        tc.setUp()

        expected = uf.Fixtures(a="a", b="b")
        self.assertEqual(expected, tc.fixtures)

    def test_fixture_depending_fixture(self) -> None:
        @uf.requires(c=self.fixture_c)
        class MyTestCase(uf.TestCase):
            pass

        tc = MyTestCase()
        tc.setUp()

        expected = uf.Fixtures(fixture_a="a", fixture_b="b", c="ab")
        self.assertEqual(expected, tc.fixtures)

    def test_post_setup(self) -> None:
        ran = False

        @uf.requires(self.fixture_a)
        class MyTestCase(uf.TestCase):
            def post_setup(self) -> None:
                nonlocal ran
                ran = not ran

        tc = MyTestCase()
        tc.setUp()

        self.assertTrue(ran)

    def test_fixture_generator(self) -> None:
        ran = False

        @uf.depends()
        def fixture(
            _options: uf.FixtureOptions, _fixtures: uf.Fixtures
        ) -> uf.FixtureContext[int]:
            nonlocal ran
            yield 6
            ran = True

        @uf.requires(fixture)
        class MyTestCase(uf.TestCase):
            def test(self) -> None:
                self.assertEqual(6, self.fixtures.fixture)

        tc = MyTestCase()
        tc.setUp()
        tc.test()
        tc.doCleanups()

        self.assertTrue(ran)

    def test_with_options(self) -> None:
        @uf.depends()
        def fixture(options: uf.FixtureOptions, _fixtures: uf.Fixtures) -> str:
            return str(options.get("echo", ""))

        @uf.requires(fixture)
        class MyTestCase(uf.TestCase):
            options = {"echo": "Hello World!"}

            def post_setup(self) -> None:
                self.assertEqual("Hello World!", self.fixtures.fixture)

        tc = MyTestCase()
        tc.setUp()


class CommonDepsTests(uf.TestCase):
    @staticmethod
    @uf.depends()
    def fixture_a(_options: uf.FixtureOptions, _fixtures: uf.Fixtures) -> str:
        return "a"

    @staticmethod
    @uf.depends(fixture_a)
    def fixture_b(_options: uf.FixtureOptions, _fixtures: uf.Fixtures) -> str:
        return "b"

    @staticmethod
    @uf.depends(fixture_a)
    def fixture_c(_options: uf.FixtureOptions, _fixtures: uf.Fixtures) -> str:
        return "c"

    def test(self) -> None:
        @uf.requires(c=self.fixture_c, b=self.fixture_b, z=self.fixture_c)
        class MyTestCase(uf.TestCase):
            def post_setup(self) -> None:
                self.assertEqual(
                    uf.Fixtures(fixture_a="a", b="b", c="c", z="c"), self.fixtures
                )

        tc = MyTestCase()
        tc.setUp()


class LoadTests(uf.TestCase):
    def test_by_string(self) -> None:
        uf.get_fixtures_module.cache_clear()

        @uf.depends("test_a")
        def fixture(_options: uf.FixtureOptions, fixtures: uf.Fixtures) -> str:
            self.assertEqual(fixtures, uf.Fixtures(test_a="test_a"))
            return "fixture"

        @uf.requires(fixture)
        class MyTestCase(uf.TestCase):
            def post_setup(self) -> None:
                self.assertEqual(
                    self.fixtures, uf.Fixtures(test_a="test_a", fixture="fixture")
                )

        tc = MyTestCase()
        tc.setUp()


class GetFixturesModuleTests(uf.TestCase):
    def test_with_missing_pyproject_toml(self) -> None:
        with mock.patch.object(builtins, "open") as mock_open:
            mock_open.side_effect = FileNotFoundError
            module = uf.get_fixtures_module()

        assert module is fixtures_module


class ParametrizeTests(uf.TestCase):
    values = {1, 2}

    @uf.parametrized([[1, values], [2, values], [None, values]])
    def test(self, value: int | None, values: set[int]) -> None:
        if value is not None:
            self.assertIn(value, values)
            values.discard(value)
            return
        self.assertEqual(set(), values)
