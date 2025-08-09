"""Creating and Using Fixtures"""

import inspect
from contextlib import contextmanager
from copy import copy
from functools import cache, wraps
from typing import Any, Callable, Protocol
from unittest import TestCase

from unittest_fixtures.types import FixtureFunction, Fixtures, State, TestCaseClass


class TestMethodWithFixturesKwarg(Protocol):  # pylint: disable=too-few-public-methods
    """Test methods that take a fixtures kwarg"""

    def __call__(
        self, _self: TestCase, *, fixtures: Fixtures
    ) -> Any: ...  # pragma: no cover


class UnittestFixtures:
    """Container for TestCases' fixtures"""

    def __init__(self) -> None:
        self.state = State(requirements={}, deps={}, options={}, fixtures={})

    def given(
        self, *requirements: FixtureFunction, **named_requirements: FixtureFunction
    ) -> Callable[[TestCaseClass], TestCaseClass]:
        """Decorate the TestCase to include the fixtures given by the FixtureFunction"""

        def decorator(test_class: TestCaseClass) -> TestCaseClass:
            self.state.requirements[test_class] = (
                {}
                | self.ancestor_requirements(test_class)
                | {fixture_name(f): f for req in requirements for f in [req]}
                | named_requirements
            )

            for name, method in test_class.__dict__.items():
                if callable(method) and (name == "test" or name.startswith("test")):
                    if not hasattr(method, "__unittest_fixtures_wrapped__"):
                        setattr(test_class, name, self.make_wrapper(method))

            original_setup = getattr(test_class, "setUp", lambda *args, **kwargs: None)

            def unittest_fixtures_setup(
                test_case: TestCase, *args: Any, **kwargs: Any
            ) -> None:
                self.state.fixtures[test_case] = Fixtures()
                setups = self.state.requirements.get(test_class, {})
                self.add_fixtures(test_case, setups)

                if original_setup.__name__ != "unittest_fixtures_setup":
                    original_setup(self, *args, **kwargs)

                test_case.addCleanup(lambda: self.state.fixtures.pop(test_case, None))

            setattr(test_class, "setUp", unittest_fixtures_setup)
            return test_class

        return decorator

    def fixture(
        self, *deps: FixtureFunction, **named_deps: FixtureFunction
    ) -> Callable[[FixtureFunction], FixtureFunction]:
        """Declare fixture requiring fixtures given by the FixtureFunction"""

        def decorator(fn: FixtureFunction) -> FixtureFunction:
            self.state.deps[fn] = {fixture_name(dep): dep for dep in deps} | named_deps

            return fn

        return decorator

    def where(self, **kwargs: Any) -> Callable[[TestCaseClass], TestCaseClass]:
        """Provide the given options to the given fixtures"""

        def decorator(test_class: TestCaseClass) -> TestCaseClass:
            test_class_options = self.state.options.setdefault(test_class, {})
            test_class_options.update(kwargs)
            return test_class

        return decorator

    def ancestor_requirements(
        self, test_class: TestCaseClass
    ) -> dict[str, FixtureFunction]:
        """Gather the requirements of the test_class's ancestors"""
        reqs = {}
        for ancestor in reversed(test_class.mro()):
            reqs.update(self.state.requirements.get(ancestor, {}))
        return reqs

    def add_fixtures(
        self, test_case: TestCase, reqs: dict[str, FixtureFunction]
    ) -> None:
        """Given the TestCase call the fixture functions given by specs and add them to the
        _FIXTURES table
        """
        fixtures = self.state.fixtures[test_case]
        for name, func in reqs.items():
            if deps := self.state.deps.get(func, {}):
                self.add_fixtures(test_case, deps)
            if not hasattr(fixtures, name):
                setattr(fixtures, name, self.apply_func(func, test_case))

    def apply_func(self, func: FixtureFunction, test_case: TestCase) -> Any:
        """Apply the given fixture func to the given test options and return the result

        If func is a generator function, apply it and add it to the test's cleanup.
        """
        fixtures = copy(self.state.fixtures[test_case])
        test_class = type(test_case)
        test_opts = {
            k: v
            for test_class in (*reversed(test_class.mro()), test_class)
            for k, v in self.state.options.get(test_class, {}).items()
        }
        opts = opts_for_name(fixture_name(func), test_opts)

        if inspect.isgeneratorfunction(func):
            return test_case.enterContext(contextmanager(func)(fixtures, **opts))

        return func(fixtures, **opts)

    def make_wrapper(
        self, method: TestMethodWithFixturesKwarg
    ) -> Callable[[TestCase], Any]:
        """Wrap the given method so that the fixtures kwarg is passed"""

        @wraps(method)
        def wrapper(test_case: TestCase) -> Any:
            return method(test_case, fixtures=self.state.fixtures[test_case])

        wrapper.__unittest_fixtures_wrapped__ = method  # type: ignore
        return coroutine(wrapper) if inspect.iscoroutinefunction(method) else wrapper


@cache
def fixture_name(fixture_function: FixtureFunction) -> str:
    """Return the fixture name of the given function"""
    func_name = fixture_function.__name__

    if name := func_name.removesuffix("_fixture"):
        return name
    return func_name


def opts_for_name(name: str, options: dict[str, Any]) -> dict[str, Any]:
    """Return dict of options for the fixture with the given name"""
    return {
        fixture_option_name or fixture_name: value
        for key, value in options.items()
        for fixture_name, _, fixture_option_name in [key.partition("__")]
        if fixture_name == name
    }


def coroutine(method: Callable[[TestCase], Any]) -> Callable[[TestCase], Any]:
    """Convert the sync method created by make_wrapper into an async method"""

    @wraps(method)
    async def wrapper(test_case: TestCase) -> Any:
        return await method(test_case)

    return wrapper
