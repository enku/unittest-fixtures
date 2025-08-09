# pylint: disable=missing-docstring,protected-access
from unittest import IsolatedAsyncioTestCase, TestCase

from unittest_fixtures import FixtureContext, Fixtures, fixture, given, where

from . import assert_test_result
from . import fixtures as tf

state = fixture.__self__.state  # type: ignore


class FixtureTests(TestCase):
    def test_has_deps(self) -> None:
        @fixture()
        def f(_fixtures: Fixtures) -> None:
            return

        self.assertEqual({}, state.deps[f])

    def test_unnamed_deps(self) -> None:
        @fixture()
        def fixture_a(_fixtures: Fixtures) -> None:
            return

        @fixture()
        def fixture_b(_fixtures: Fixtures) -> None:
            return

        @fixture(fixture_a, fixture_b)
        def fixture_c(_fixtures: Fixtures) -> None:
            return

        expected = {"fixture_a": fixture_a, "fixture_b": fixture_b}
        self.assertEqual(expected, state.deps[fixture_c])

    def test_named_deps(self) -> None:
        @fixture()
        def fixture_a(_fixtures: Fixtures) -> None:
            return

        @fixture()
        def fixture_b(_fixtures: Fixtures) -> None:
            return

        @fixture(a=fixture_a, b=fixture_b)
        def fixture_c(_fixtures: Fixtures) -> None:
            return

        expected = {"a": fixture_a, "b": fixture_b}
        self.assertEqual(expected, state.deps[fixture_c])


class RequiresTests(TestCase):
    @staticmethod
    @fixture()
    def fixture_a(_fixtures: Fixtures) -> str:
        return "a"

    @staticmethod
    @fixture()
    def fixture_b(_fixtures: Fixtures) -> str:
        return "b"

    @staticmethod
    @fixture(fixture_a, fixture_b)
    def fixture_c(fixtures: Fixtures) -> str:
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
        def f(_fixtures: Fixtures) -> FixtureContext[int]:
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
        def echo(_fixtures: Fixtures, echo: str = "") -> str:
            return echo

        @given(echo)
        @where(echo="Hello World!")
        class MyTestCase(TestCase):
            def test(self, fixtures: Fixtures) -> None:
                self.assertEqual("Hello World!", fixtures.echo)

        result = MyTestCase("test").run()
        assert_test_result(self, result)

    def test_inheritance(self) -> None:
        @given(tf.test_a)
        class Parent(TestCase):
            pass

        @fixture()
        def test_b(_fixtures: Fixtures) -> bool:
            return True

        @given(test_b)
        class Child(Parent):
            def test(self, fixtures: Fixtures) -> None:
                self.assertEqual(fixtures, Fixtures(test_a="test_a", test_b=True))

        result = Child("test").run()
        assert_test_result(self, result)

    def test_inherits_parents_options(self) -> None:
        @fixture()
        def echo(_fixtures: Fixtures, echo: str = "") -> str:
            return echo

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
        def echo(_fixtures: Fixtures, echo: str = "") -> str:
            return echo

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

    def test_stacked_given_decorators(self) -> None:
        @fixture()
        def a(_fixtures: Fixtures) -> None:
            return

        @fixture()
        def b(_fixtures: Fixtures) -> None:
            return

        @given(a)
        @given(b)
        class MyTestCase(TestCase):
            def test(self, fixtures: Fixtures) -> None:
                self.assertTrue(hasattr(fixtures, "a"))
                self.assertTrue(hasattr(fixtures, "b"))

        result = MyTestCase("test").run()
        assert_test_result(self, result)

    def test_options_to_deps_passed_as_kwargs(self) -> None:
        @fixture()
        def echo(
            _fixtures: Fixtures, echo: str = "Hello world", punc: str = "!"
        ) -> str:
            return f"{echo}{punc}"

        @given(echo)
        @where(echo="test", echo__punc="!!!")
        class MyTestCase(TestCase):
            def test(self, fixtures: Fixtures) -> None:
                self.assertEqual("test!!!", fixtures.echo)

        result = MyTestCase("test").run()
        assert_test_result(self, result)


class CommonDepsTests(TestCase):
    @staticmethod
    @fixture()
    def fixture_a(_fixtures: Fixtures) -> str:
        return "a"

    @staticmethod
    @fixture(fixture_a)
    def fixture_b(_fixtures: Fixtures) -> str:
        return "b"

    @staticmethod
    @fixture(fixture_a)
    def fixture_c(_fixtures: Fixtures) -> str:
        return "c"

    def test(self) -> None:
        @given(c=self.fixture_c, b=self.fixture_b, z=self.fixture_c)
        class MyTestCase(TestCase):
            def test(self, fixtures: Fixtures) -> None:
                self.assertEqual(Fixtures(fixture_a="a", b="b", c="c", z="c"), fixtures)

        result = MyTestCase("test").run()
        assert_test_result(self, result)


class AsyncTests(TestCase):
    def test(self) -> None:
        test_ran = False

        @fixture()
        def a(_fixtures: Fixtures) -> str:
            return "a"

        @given(a)
        class MyTestCase(IsolatedAsyncioTestCase):
            async def test(self, fixtures: Fixtures) -> None:
                nonlocal test_ran

                test_ran = True
                self.assertEqual(Fixtures(a="a"), fixtures)

        result = MyTestCase("test").run()
        assert_test_result(self, result)
        self.assertTrue(test_ran)
