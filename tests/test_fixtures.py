# pylint: disable=missing-docstring

import inspect
from unittest import IsolatedAsyncioTestCase, TestCase

from unittest_fixtures import FixtureContext, Fixtures
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

        t = T()
        self.assertEqual(t.setUp.__name__, "unittest_fixtures_setup")

        t.setUp()
        self.assertEqual({t: Fixtures(a="a", d="b", c="c", g="b")}, state.fixtures)

        t.doCleanups()
        self.assertEqual({}, state.fixtures)


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
        uf.state.fixtures[test_case] = Fixtures()
        reqs = {"a": fixture_a}
        uf.add_fixtures(test_case, reqs)

        self.assertEqual(Fixtures(a=6), uf.state.fixtures[test_case])

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
        uf.state.fixtures[test_case] = Fixtures()
        reqs = {"b": fixture_b}
        uf.add_fixtures(test_case, reqs)

        self.assertEqual(Fixtures(b=7, a=6), uf.state.fixtures[test_case])

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
        uf.state.fixtures[test_case] = Fixtures(a=5)
        reqs = {"b": fixture_b}
        uf.add_fixtures(test_case, reqs)

        self.assertEqual(Fixtures(b=7, a=5), uf.state.fixtures[test_case])


class ApplyFuncTests(TestCase):
    def test_with_options(self) -> None:
        uf = UnittestFixtures()

        @uf.fixture()
        def my_fixture(_: Fixtures, my: int = 6) -> int:
            return my

        class Tests(TestCase):
            pass

        t = Tests()
        uf.state.fixtures[t] = Fixtures()
        uf.state.options[Tests] = {"my": 7}

        result = uf.apply_func(my_fixture, t)

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
        uf.state.fixtures[t] = Fixtures()

        uf.apply_func(my_fixture, t)

        self.assertTrue(in_context)

        t.doCleanups()
        self.assertFalse(in_context)


class MakeWrapperTests(IsolatedAsyncioTestCase):
    def test(self) -> None:
        uf = UnittestFixtures()
        state = uf.state

        class T(TestCase):
            @uf.make_wrapper  # type: ignore
            def test(self, *, fixtures: Fixtures) -> Fixtures:
                return fixtures

        t = T()
        state.fixtures[t] = Fixtures(a=1, b=2, c=3)
        self.assertEqual(state.fixtures[t], t.test())  # pylint: disable=missing-kwoa

    async def test_coroutine(self) -> None:
        uf = UnittestFixtures()
        state = uf.state

        class T(TestCase):
            @uf.make_wrapper  # type: ignore
            async def test(self, *, fixtures: Fixtures) -> Fixtures:
                return fixtures

        t = T()
        state.fixtures[t] = Fixtures(a=1, b=2, c=3)
        self.assertEqual(
            state.fixtures[t], await t.test()  # pylint: disable=missing-kwoa
        )


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
