# pylint: disable=missing-docstring

from unittest import TestCase

from unittest_fixtures import FixtureContext, Fixtures
from unittest_fixtures.fixtures import UnittestFixtures, fixture_name, opts_for_name

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
