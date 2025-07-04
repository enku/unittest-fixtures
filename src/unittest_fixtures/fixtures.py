"""Creating and Using Fixtures"""

import inspect
from contextlib import contextmanager
from copy import copy
from dataclasses import dataclass
from functools import cache, wraps
from typing import Any, Callable, Protocol
from unittest import TestCase

from unittest_fixtures.types import FixtureFunction, Fixtures, TestCaseClass


# namespace for state variables
@dataclass(frozen=True, kw_only=True)
class _State:
    requirements: dict[TestCaseClass, dict[str, FixtureFunction]]
    deps: dict[FixtureFunction, dict[str, FixtureFunction]]
    options: dict[TestCaseClass, dict[str, Any]]
    fixtures: dict[TestCase, Fixtures]


_state = _State(requirements={}, deps={}, options={}, fixtures={})
del _State


class TestMethodWithFixturesKwarg(Protocol):  # pylint: disable=too-few-public-methods
    """Test methods that take a fixtures kwarg"""

    def __call__(
        self, _self: TestCase, *, fixtures: Fixtures
    ) -> Any: ...  # pragma: no cover


def given(
    *requirements: FixtureFunction, **named_requirements: FixtureFunction
) -> Callable[[TestCaseClass], TestCaseClass]:
    """Decorate the TestCase to include the fixtures given by the FixtureFunction"""

    def decorator(test_case: TestCaseClass) -> TestCaseClass:
        _state.requirements[test_case] = (
            {}
            | ancestor_requirements(test_case)
            | {funcname(f): f for req in requirements for f in [req]}
            | named_requirements
        )

        for name, method in test_case.__dict__.items():
            if callable(method) and (name == "test" or name.startswith("test")):
                if not hasattr(method, "__unittest_fixtures_wrapped__"):
                    setattr(test_case, name, make_wrapper(method))

        original_setup = getattr(test_case, "setUp", lambda *args, **kwargs: None)

        def unittest_fixtures_setup(self: TestCase, *args: Any, **kwargs: Any) -> None:
            _state.fixtures[self] = Fixtures()
            setups = _state.requirements.get(test_case, {})
            add_fixtures(self, setups)

            if original_setup.__name__ != "unittest_fixtures_setup":
                original_setup(self, *args, **kwargs)

            self.addCleanup(lambda: _state.fixtures.pop(self, None))

        setattr(test_case, "setUp", unittest_fixtures_setup)
        return test_case

    return decorator


def fixture(
    *deps: FixtureFunction, **named_deps: FixtureFunction
) -> Callable[[FixtureFunction], FixtureFunction]:
    """Declare fixture requiring fixtures given by the FixtureFunction"""

    def decorator(fn: FixtureFunction) -> FixtureFunction:
        _state.deps[fn] = {funcname(dep): dep for dep in deps} | named_deps

        return fn

    return decorator


def where(**kwargs: Any) -> Callable[[TestCaseClass], TestCaseClass]:
    """Provide the given options to the given fixtures"""

    def decorator(test_case: TestCaseClass) -> TestCaseClass:
        test_case_options = _state.options.setdefault(test_case, {})
        test_case_options.update(kwargs)
        return test_case

    return decorator


def make_wrapper(method: TestMethodWithFixturesKwarg) -> Callable[[TestCase], Any]:
    """Wrap the given method so that the fixtures kwarg is passed"""

    @wraps(method)
    def wrapper(self: TestCase) -> Any:
        return method(self, fixtures=_state.fixtures[self])

    wrapper.__unittest_fixtures_wrapped__ = method  # type: ignore
    return wrapper


def add_fixtures(test: TestCase, reqs: dict[str, FixtureFunction]) -> None:
    """Given the TestCase call the fixture functions given by specs and add them to the
    _FIXTURES table
    """
    fixtures = _state.fixtures[test]
    for name, func in reqs.items():
        if deps := _state.deps.get(func, {}):
            add_fixtures(test, deps)
        if not hasattr(fixtures, name):
            setattr(fixtures, name, apply_func(func, name, test))


def ancestor_requirements(test_case: TestCaseClass) -> dict[str, FixtureFunction]:
    """Gather the requirements of the test_case's ancestors"""
    reqs = {}
    for ancestor in reversed(test_case.mro()):
        reqs.update(_state.requirements.get(ancestor, {}))
    return reqs


def apply_func(func: FixtureFunction, name: str, test: TestCase) -> Any:
    """Apply the given fixture func to the given test options and return the result

    If func is a generator function, apply it and add it to the test's cleanup.
    """
    fixtures = copy(_state.fixtures[test])
    test_case = type(test)
    test_opts = {
        k: v
        for test_case in (*reversed(test_case.mro()), test_case)
        for k, v in _state.options.get(test_case, {}).items()
    }
    opts = opts_for_name(name, test_opts)

    if inspect.isgeneratorfunction(func):
        return test.enterContext(contextmanager(func)(fixtures, **opts))

    return func(fixtures, **opts)


@cache
def funcname(fixture_function: FixtureFunction) -> str:
    """Return the fixture name of the given function"""
    func_name = fixture_function.__name__

    return func_name.removesuffix("_fixture")


def opts_for_name(name: str, options: dict[str, Any]) -> dict[str, Any]:
    """Return dict of options for the fixture with the given name"""
    return {
        fixture_option_name or fixture_name: value
        for key, value in options.items()
        for fixture_name, _, fixture_option_name in [key.partition("__")]
        if fixture_name == name
    }
