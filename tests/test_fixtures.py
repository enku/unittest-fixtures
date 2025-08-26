# pylint: disable=missing-docstring

import inspect
from typing import Any
from unittest import IsolatedAsyncioTestCase, TestCase

from unittest_fixtures import FixtureContext, Fixtures, Param
from unittest_fixtures.fixtures import (
    UnittestFixtures,
    coroutine,
    fixture_name,
    opts_for_name,
)

from . import assert_test_result
from .fixtures import test_a


class LoadFixtureTests(TestCase):
    def test(self) -> None:
        uf = UnittestFixtures()

        @uf.fixture(test_a)
        def f(fixtures: Fixtures) -> str:
            self.assertEqual(fixtures, Fixtures(test_a="test_a"))
            return "fixture"

        @uf.given(f)
        class MyTestCase(TestCase):
            def test(self, fixtures: Fixtures) -> None:
                self.assertEqual(fixtures, Fixtures(test_a="test_a", f="fixture"))

        result = MyTestCase("test").run()
        assert_test_result(self, result)


class GivenTests(TestCase):
    def test(self) -> None:
        uf = UnittestFixtures()
        state = uf.state

        @uf.fixture()
        def a(_: Fixtures) -> str:
            return "a"

        @uf.fixture()
        def b(_: Fixtures) -> str:
            return "b"

        @uf.fixture(a, d=b)
        def c(_: Fixtures) -> str:
            return "c"

        @uf.given(c, g=b)
        class T(TestCase):
            def setUp(self) -> None:
                pass

            def test(self, fixtures: Fixtures) -> None:
                pass

        self.assertEqual({"c": c, "g": b}, state.requirements[T])
        self.assertEqual({a: {}, b: {}, c: {"a": a, "d": b}}, state.deps)
        self.assertTrue(hasattr(T.test, "__unittest_fixtures_wrapped__"))


class FixtureTests(TestCase):
    def test(self) -> None:
        uf = UnittestFixtures()
        state = uf.state

        @uf.fixture()
        def a(_: Fixtures) -> None:
            pass

        @uf.fixture()
        def b(_: Fixtures) -> None:
            pass

        @uf.fixture(a, d=b)
        def c(_: Fixtures) -> None:
            pass

        self.assertEqual({}, state.deps[a])
        self.assertEqual({}, state.deps[b])
        self.assertEqual({"a": a, "d": b}, state.deps[c])


class WhereTests(TestCase):
    def test(self) -> None:
        uf = UnittestFixtures()
        state = uf.state

        @uf.where(a="a", b="b", c="c")
        class T(TestCase):
            pass

        self.assertEqual({"a": "a", "b": "b", "c": "c"}, state.options[T])

    def test_fixture_depends_on_other_fixture_value(self) -> None:
        uf = UnittestFixtures()

        @uf.fixture()
        def a(_: Fixtures, a: str = "a") -> str:
            return a

        @uf.fixture()
        def b(_: Fixtures, b: str = "b") -> str:
            return b

        @uf.given(a, b)
        @uf.where(a="b", b=Param(lambda fixtures: fixtures.a + "b"))
        class T(TestCase):
            def test(self, fixtures: Fixtures) -> None:
                self.assertEqual(fixtures.a, "b")
                self.assertEqual(fixtures.b, "bb")

        result = T("test").run()
        assert_test_result(self, result)


class ParamsTests(TestCase):
    def test(self) -> None:
        uf = UnittestFixtures()
        state = uf.state

        @uf.params(letters=("a", "b", "c"), numbers=("1", "2", "3"))
        class T(TestCase):
            def test(self, fixtures: Fixtures) -> None:
                pass

        self.assertEqual(
            state.params[T], {"letters": ("a", "b", "c"), "numbers": ("1", "2", "3")}
        )


class AncestorRequirementsTests(TestCase):
    def test(self) -> None:
        uf = UnittestFixtures()

        class A(TestCase):
            pass

        @uf.fixture()
        def a(_: Fixtures) -> None:
            pass

        uf.state.requirements[A] = {"a": a}

        class B(A):
            pass

        @uf.fixture()
        def b(_: Fixtures) -> None:
            pass

        uf.state.requirements[B] = {"b": b}

        class C(B):
            pass

        @uf.fixture()
        def c(_: Fixtures) -> None:
            pass

        uf.state.requirements[C] = {"c": c}

        reqs = uf.ancestor_requirements(C)

        self.assertEqual({"a": a, "b": b, "c": c}, reqs)


class AddFixturesTests(TestCase):
    def test(self) -> None:
        uf = UnittestFixtures()

        class Tests(TestCase):
            pass

        @uf.fixture()
        def fixture_a(_: Fixtures) -> int:
            return 6

        test_case = Tests()
        reqs = {"a": fixture_a}
        fixtures = uf.add_fixtures(test_case, reqs, Fixtures())

        self.assertEqual(Fixtures(a=6), fixtures)

    def test_with_deps(self) -> None:
        uf = UnittestFixtures()

        class Tests(TestCase):
            pass

        @uf.fixture()
        def fixture_a(_: Fixtures) -> int:
            return 6

        @uf.fixture(a=fixture_a)
        def fixture_b(_: Fixtures) -> int:
            return 7

        test_case = Tests()
        reqs = {"b": fixture_b}
        fixtures = uf.add_fixtures(test_case, reqs, Fixtures())

        self.assertEqual(Fixtures(b=7, a=6), fixtures)

    def test_already_has_dep(self) -> None:
        uf = UnittestFixtures()

        class Tests(TestCase):
            pass

        @uf.fixture()
        def fixture_a(_: Fixtures) -> int:
            return 6

        @uf.fixture(a=fixture_a)
        def fixture_b(_: Fixtures) -> int:
            return 7

        test_case = Tests()
        reqs = {"b": fixture_b}
        fixtures = uf.add_fixtures(test_case, reqs, Fixtures(a=5))

        self.assertEqual(Fixtures(b=7, a=5), fixtures)


class ApplyFuncTests(TestCase):
    def test_with_options(self) -> None:
        uf = UnittestFixtures()

        @uf.fixture()
        def my_fixture(_: Fixtures, my: int = 6) -> int:
            return my

        class Tests(TestCase):
            pass

        t = Tests()
        uf.state.options[Tests] = {"my": 7}

        result = uf.apply_func(my_fixture, "my", t, Fixtures())

        self.assertEqual(7, result)

    def test_generator_function(self) -> None:
        uf = UnittestFixtures()
        in_context = True

        @uf.fixture()
        def my_fixture(_: Fixtures) -> FixtureContext[None]:
            nonlocal in_context

            in_context = True
            yield
            in_context = False

        class Tests(TestCase):
            pass

        t = Tests()
        uf.apply_func(my_fixture, "my", t, Fixtures())

        self.assertTrue(in_context)

        t.doCleanups()
        self.assertFalse(in_context)


class MakeWrapperTests(TestCase):
    def test(self) -> None:
        uf = UnittestFixtures()
        state = uf.state

        class T(TestCase):
            @uf.make_wrapper  # type: ignore
            def test(self, *, fixtures: Fixtures) -> None:
                self.assertEqual(fixtures, Fixtures(a=1, b=2, c=3))

        state.requirements[T] = {"a": lambda _: 1, "b": lambda _: 2, "c": lambda _: 3}
        t = T("test")
        result = t.run()
        assert_test_result(self, result)

    def test_coroutine(self) -> None:
        uf = UnittestFixtures()
        state = uf.state

        class T(IsolatedAsyncioTestCase):
            @uf.make_wrapper  # type: ignore
            async def test(self, *, fixtures: Fixtures) -> None:
                self.assertEqual(fixtures, Fixtures(a=1, b=2, c=3))

        state.requirements[T] = {"a": lambda _: 1, "b": lambda _: 2, "c": lambda _: 3}
        t = T("test")
        result = t.run()
        assert_test_result(self, result)

    def test_with_custom_kwarg(self) -> None:
        uf = UnittestFixtures()
        state = uf.state

        class T(TestCase):
            unittest_fixtures_kwarg = "fx"

            @uf.make_wrapper  # type: ignore
            def test(self, *, fx: Fixtures) -> None:
                self.assertEqual(fx, Fixtures(a=1, b=2, c=3))

        state.requirements[T] = {"a": lambda _: 1, "b": lambda _: 2, "c": lambda _: 3}
        t = T("test")
        result = t.run()
        assert_test_result(self, result)

    def test_with_params(self) -> None:
        uf = UnittestFixtures()
        state = uf.state
        combinations: list[Fixtures] = []

        class T(TestCase):
            @uf.make_wrapper  # type: ignore
            def test(self, *, fixtures: Fixtures) -> None:
                combinations.append(fixtures)
                self.assertEqual(fixtures.a, 1)
                self.assertEqual(fixtures.number**2, fixtures.square)

        state.requirements[T] = {"a": lambda _: 1}
        state.params[T] = {"number": (1, 2, 3), "square": (1, 4, 9)}

        t = T("test")
        result = t.run()
        assert_test_result(self, result)
        self.assertEqual(
            combinations,
            [
                Fixtures(number=1, square=1, a=1),
                Fixtures(number=2, square=4, a=1),
                Fixtures(number=3, square=9, a=1),
            ],
        )

    def test_with_params_and_options_param(self) -> None:
        uf = UnittestFixtures()
        state = uf.state
        combinations: list[Fixtures] = []

        @uf.fixture()
        def a(_: Fixtures, a: Any = "foo") -> Any:
            return a

        class T(TestCase):
            @uf.make_wrapper  # type: ignore
            def test(self, *, fixtures: Fixtures) -> None:
                combinations.append(fixtures)
                self.assertEqual(fixtures.a, fixtures.value)

        state.requirements[T] = {"a": a}
        state.options[T] = {"a": Param(lambda fixtures: fixtures.value)}
        state.params[T] = {"value": (1, 2, 3)}

        t = T("test")
        result = t.run()
        assert_test_result(self, result)
        self.assertEqual(
            combinations,
            [Fixtures(value=1, a=1), Fixtures(value=2, a=2), Fixtures(value=3, a=3)],
        )

    def test_with_combine(self) -> None:
        uf = UnittestFixtures()
        state = uf.state
        combinations = []

        @uf.fixture()
        def s(_: Fixtures, s: int = 0) -> int:
            return s

        class T(TestCase):
            @uf.make_wrapper  # type: ignore
            def test(self, *, fixtures: Fixtures) -> None:
                self.assertEqual(fixtures.x + fixtures.y, fixtures.sum)
                combinations.append(fixtures)

        state.requirements[T] = {"sum": s}
        state.combine[T] = {"x": [1, 2, 3], "y": [1, 2, 3]}
        state.options[T] = {"sum__s": Param(lambda fixtures: fixtures.y + fixtures.x)}

        t = T("test")
        result = t.run()
        assert_test_result(self, result)
        expected = [
            Fixtures(x=1, y=1, sum=2),
            Fixtures(x=1, y=2, sum=3),
            Fixtures(x=1, y=3, sum=4),
            Fixtures(x=2, y=1, sum=3),
            Fixtures(x=2, y=2, sum=4),
            Fixtures(x=2, y=3, sum=5),
            Fixtures(x=3, y=1, sum=4),
            Fixtures(x=3, y=2, sum=5),
            Fixtures(x=3, y=3, sum=6),
        ]
        self.assertEqual(combinations, expected)


class FixtureNameTests(TestCase):
    def setUp(self) -> None:
        super().setUp()

        fixture_name.cache_clear()

    def test_simple_name(self) -> None:
        def test() -> None:
            pass

        self.assertEqual("test", fixture_name(test))

    def test_underscore_fixture_suffix(self) -> None:
        def test_fixture() -> None:
            pass

        self.assertEqual("test", fixture_name(test_fixture))

    def test_name_is_underscore_fixture(self) -> None:
        def _fixture() -> None:
            pass

        self.assertEqual("_fixture", fixture_name(_fixture))


class OptsForNameTests(TestCase):
    def test_when_opt_is_name(self) -> None:
        options = {"name": 1}

        self.assertEqual({"name": 1}, opts_for_name("name", options))

    def test_single_opt(self) -> None:
        options = {"name__foo": 1}

        self.assertEqual({"foo": 1}, opts_for_name("name", options))

    def test_multi_opt(self) -> None:
        options = {"name__foo": 1, "name__bar": 2, "name_baz": 3}

        self.assertEqual({"foo": 1, "bar": 2}, opts_for_name("name", options))

    def test_opt_is_name_plus_other(self) -> None:
        options = {"name": 1, "name__bar": 2}

        self.assertEqual({"name": 1, "bar": 2}, opts_for_name("name", options))

    def test_none(self) -> None:
        options = {"name__foo": 1, "name__bar": 2, "name_baz": 3}

        self.assertEqual({}, opts_for_name("test", options))


class CoroutineTests(IsolatedAsyncioTestCase):
    def test(self) -> None:
        class MyTestCase(TestCase):
            def test(self) -> None:
                pass

        method = coroutine(MyTestCase.test)  # type: ignore

        self.assertTrue(inspect.iscoroutinefunction(method))
