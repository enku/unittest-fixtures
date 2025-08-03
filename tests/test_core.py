# pylint: disable=missing-docstring,protected-access
from unittest import TestCase

from unittest_fixtures import FixtureContext, Fixtures
from unittest_fixtures.fixtures import UnittestFixtures

from . import assert_test_result
from . import fixtures as tf


class FixtureTests(TestCase):
    def test_has_deps(self) -> None:
        uf = UnittestFixtures()

        @uf.fixture()
        def f(_fixtures: Fixtures) -> None:
            return

        self.assertEqual({}, uf.state.deps[f])

    def test_unnamed_deps(self) -> None:
        uf = UnittestFixtures()

        @uf.fixture()
        def fixture_a(_fixtures: Fixtures) -> None:
            return

        @uf.fixture()
        def fixture_b(_fixtures: Fixtures) -> None:
            return

        @uf.fixture(fixture_a, fixture_b)
        def fixture_c(_fixtures: Fixtures) -> None:
            return

        expected = {"fixture_a": fixture_a, "fixture_b": fixture_b}
        self.assertEqual(expected, uf.state.deps[fixture_c])

    def test_named_deps(self) -> None:
        uf = UnittestFixtures()

        @uf.fixture()
        def fixture_a(_fixtures: Fixtures) -> None:
            return

        @uf.fixture()
        def fixture_b(_fixtures: Fixtures) -> None:
            return

        @uf.fixture(a=fixture_a, b=fixture_b)
        def fixture_c(_fixtures: Fixtures) -> None:
            return

        expected = {"a": fixture_a, "b": fixture_b}
        self.assertEqual(expected, uf.state.deps[fixture_c])


class RequiresTests(TestCase):
    uf = UnittestFixtures()

    @staticmethod
    @uf.fixture()
    def fixture_a(_fixtures: Fixtures) -> str:
        return "a"

    @staticmethod
    @uf.fixture()
    def fixture_b(_fixtures: Fixtures) -> str:
        return "b"

    @staticmethod
    @uf.fixture(fixture_a, fixture_b)
    def fixture_c(fixtures: Fixtures) -> str:
        return fixtures.fixture_a + fixtures.fixture_b  # type: ignore

    def test_unnamed_deps(self) -> None:
        @self.uf.given(self.fixture_a)
        class MyTestCase(TestCase):
            def test(self, fixtures: Fixtures) -> None:
                self.assertEqual(Fixtures(fixture_a="a"), fixtures)

        result = MyTestCase("test").run()
        assert_test_result(self, result)

    def test_named_deps(self) -> None:
        @self.uf.given(a=self.fixture_a, b=self.fixture_b)
        class MyTestCase(TestCase):
            def test(self, fixtures: Fixtures) -> None:
                expected = Fixtures(a="a", b="b")
                self.assertEqual(expected, fixtures)

        result = MyTestCase("test").run()
        assert_test_result(self, result)

    def test_fixture_depending_fixture(self) -> None:
        @self.uf.given(c=self.fixture_c)
        class MyTestCase(TestCase):
            def test(self, fixtures: Fixtures) -> None:
                expected = Fixtures(fixture_a="a", fixture_b="b", c="ab")
                self.assertEqual(expected, fixtures)

        result = MyTestCase("test").run()
        assert_test_result(self, result)

    def test_setup(self) -> None:
        ran = False

        @self.uf.given(self.fixture_a)
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

        @self.uf.fixture()
        def f(_fixtures: Fixtures) -> FixtureContext[int]:
            nonlocal ran
            yield 6
            ran = True

        @self.uf.given(f)
        class MyTestCase(TestCase):
            def test(self, fixtures: Fixtures) -> None:
                self.assertEqual(6, fixtures.f)

        result = MyTestCase("test").run()
        assert_test_result(self, result)

        self.assertTrue(ran)

    def test_with_options(self) -> None:
        @self.uf.fixture()
        def echo(_fixtures: Fixtures, echo: str = "") -> str:
            return echo

        @self.uf.given(echo)
        @self.uf.where(echo="Hello World!")
        class MyTestCase(TestCase):
            def test(self, fixtures: Fixtures) -> None:
                self.assertEqual("Hello World!", fixtures.echo)

        result = MyTestCase("test").run()
        assert_test_result(self, result)

    def test_inheritance(self) -> None:
        @self.uf.given(tf.test_a)
        class Parent(TestCase):
            pass

        @self.uf.fixture()
        def test_b(_fixtures: Fixtures) -> bool:
            return True

        @self.uf.given(test_b)
        class Child(Parent):
            def test(self, fixtures: Fixtures) -> None:
                self.assertEqual(fixtures, Fixtures(test_a="test_a", test_b=True))

        result = Child("test").run()
        assert_test_result(self, result)

    def test_inherits_parents_options(self) -> None:
        @self.uf.fixture()
        def echo(_fixtures: Fixtures, echo: str = "") -> str:
            return echo

        @self.uf.given(echo)
        @self.uf.where(echo="Hello World!")
        class MyBaseTestCase(TestCase):
            pass

        @self.uf.given(echo)
        class MyTestCase(MyBaseTestCase):
            def test(self, fixtures: Fixtures) -> None:
                self.assertEqual("Hello World!", fixtures.echo)

        result = MyTestCase("test").run()
        assert_test_result(self, result)

    def test_overrides_parents_options(self) -> None:
        @self.uf.fixture()
        def echo(_fixtures: Fixtures, echo: str = "") -> str:
            return echo

        @self.uf.given(echo)
        @self.uf.where(echo="Hello World!")
        class MyBaseTestCase(TestCase):
            pass

        @self.uf.given(echo)
        @self.uf.where(echo="override!")
        class MyTestCase(MyBaseTestCase):
            def test(self, fixtures: Fixtures) -> None:
                self.assertEqual("override!", fixtures.echo)

        result = MyTestCase("test").run()
        assert_test_result(self, result)

    def test_stacked_given_decorators(self) -> None:
        @self.uf.fixture()
        def a(_fixtures: Fixtures) -> None:
            return

        @self.uf.fixture()
        def b(_fixtures: Fixtures) -> None:
            return

        @self.uf.given(a)
        @self.uf.given(b)
        class MyTestCase(TestCase):
            def test(self, fixtures: Fixtures) -> None:
                self.assertTrue(hasattr(fixtures, "a"))
                self.assertTrue(hasattr(fixtures, "b"))

        result = MyTestCase("test").run()
        assert_test_result(self, result)

    def test_options_to_deps_passed_as_kwargs(self) -> None:
        @self.uf.fixture()
        def echo(
            _fixtures: Fixtures, echo: str = "Hello world", punc: str = "!"
        ) -> str:
            return f"{echo}{punc}"

        @self.uf.given(echo)
        @self.uf.where(echo="test", echo__punc="!!!")
        class MyTestCase(TestCase):
            def test(self, fixtures: Fixtures) -> None:
                self.assertEqual("test!!!", fixtures.echo)

        result = MyTestCase("test").run()
        assert_test_result(self, result)


class CommonDepsTests(TestCase):
    uf = UnittestFixtures()

    @staticmethod
    @uf.fixture()
    def fixture_a(_fixtures: Fixtures) -> str:
        return "a"

    @staticmethod
    @uf.fixture(fixture_a)
    def fixture_b(_fixtures: Fixtures) -> str:
        return "b"

    @staticmethod
    @uf.fixture(fixture_a)
    def fixture_c(_fixtures: Fixtures) -> str:
        return "c"

    def test(self) -> None:
        @self.uf.given(c=self.fixture_c, b=self.fixture_b, z=self.fixture_c)
        class MyTestCase(TestCase):
            def test(self, fixtures: Fixtures) -> None:
                self.assertEqual(Fixtures(fixture_a="a", b="b", c="c", z="c"), fixtures)

        result = MyTestCase("test").run()
        assert_test_result(self, result)
