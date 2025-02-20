# pylint: disable=missing-docstring,protected-access
import builtins
from unittest import mock

from unittest_fixtures import (
    _DEPS,
    FixtureContext,
    Fixtures,
    TestCase,
    fixture,
    get_fixtures_module,
    given,
    parametrized,
    where,
)

from . import fixtures as fixtures_module


class DependsTests(TestCase):
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
            pass

        tc = MyTestCase()
        tc.setUp()

        self.assertEqual(Fixtures(fixture_a="a"), tc.fixtures)

    def test_named_deps(self) -> None:
        @given(a=self.fixture_a, b=self.fixture_b)
        class MyTestCase(TestCase):
            pass

        tc = MyTestCase()
        tc.setUp()

        expected = Fixtures(a="a", b="b")
        self.assertEqual(expected, tc.fixtures)

    def test_fixture_depending_fixture(self) -> None:
        @given(c=self.fixture_c)
        class MyTestCase(TestCase):
            pass

        tc = MyTestCase()
        tc.setUp()

        expected = Fixtures(fixture_a="a", fixture_b="b", c="ab")
        self.assertEqual(expected, tc.fixtures)

    def test_setup(self) -> None:
        ran = False

        @given(self.fixture_a)
        class MyTestCase(TestCase):
            def setUp(self) -> None:
                nonlocal ran
                ran = not ran

        tc = MyTestCase()
        tc.setUp()

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
            def test(self) -> None:
                self.assertEqual(6, self.fixtures.f)

        tc = MyTestCase()
        tc.setUp()
        tc.test()
        tc.doCleanups()

        self.assertTrue(ran)

    def test_with_options(self) -> None:
        @fixture()
        def echo(options: str | None, _fixtures: Fixtures) -> str:
            return options or ""

        @where(echo="Hello World!")
        @given(echo)
        class MyTestCase(TestCase):

            def setUp(self) -> None:
                self.assertEqual("Hello World!", self.fixtures.echo)

        tc = MyTestCase()
        tc.setUp()

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
            def setUp(self) -> None:
                self.assertEqual("Hello World!", self.fixtures.echo)

        tc = MyTestCase()
        tc.setUp()

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
            def setUp(self) -> None:
                self.assertEqual("override!", self.fixtures.echo)

        tc = MyTestCase()
        tc.setUp()


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
            def setUp(self) -> None:
                self.assertEqual(
                    Fixtures(fixture_a="a", b="b", c="c", z="c"), self.fixtures
                )

        tc = MyTestCase()
        tc.setUp()


class LoadTests(TestCase):
    def test_by_string(self) -> None:
        get_fixtures_module.cache_clear()

        @fixture("test_a")
        def f(_options: None, fixtures: Fixtures) -> str:
            self.assertEqual(fixtures, Fixtures(test_a="test_a"))
            return "fixture"

        @given(f)
        class MyTestCase(TestCase):
            def setUp(self) -> None:
                self.assertEqual(self.fixtures, Fixtures(test_a="test_a", f="fixture"))

        tc = MyTestCase()
        tc.setUp()


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
