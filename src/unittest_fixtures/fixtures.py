"""Creating and Using Fixtures"""

import importlib
import inspect
import tomllib
from contextlib import contextmanager
from copy import copy
from functools import cache, wraps
from types import ModuleType
from typing import Any, Callable, Protocol, cast
from unittest import TestCase

from unittest_fixtures.types import (
    FixtureFunction,
    Fixtures,
    FixtureSpec,
    TestCaseClass,
)

_REQUIREMENTS: dict[TestCaseClass, dict[str, FixtureSpec]] = {}
_DEPS: dict[FixtureFunction, dict[str, FixtureSpec]] = {}
_OPTIONS: dict[TestCaseClass, dict[str, Any]] = {}
_FIXTURES: dict[TestCase, Fixtures] = {}


class TestMethodWithFixturesKwarg(Protocol):  # pylint: disable=too-few-public-methods
    """Test methods that take a fixtures kwarg"""

    def __call__(
        self, _self: TestCase, *, fixtures: Fixtures
    ) -> Any: ...  # pragma: no cover


def given(
    *requirements: FixtureSpec, **named_requirements: FixtureSpec
) -> Callable[[TestCaseClass], TestCaseClass]:
    """Decorate the TestCase to include the fixtures given by the FixtureSpec"""

    def decorator(test_case: TestCaseClass) -> TestCaseClass:
        _REQUIREMENTS[test_case] = (
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
            _FIXTURES[self] = Fixtures()
            setups = _REQUIREMENTS.get(test_case, {})
            add_fixtures(self, setups)

            if original_setup.__name__ != "unittest_fixtures_setup":
                original_setup(self, *args, **kwargs)

            self.addCleanup(lambda: _FIXTURES.pop(self, None))

        setattr(test_case, "setUp", unittest_fixtures_setup)
        return test_case

    return decorator


def fixture(
    *deps: FixtureSpec, **named_deps: FixtureSpec
) -> Callable[[FixtureFunction], FixtureFunction]:
    """Declare fixture requiring fixtures given by the FixtureSpec"""

    def dec(fn: FixtureFunction) -> FixtureFunction:
        _DEPS[fn] = {funcname(dep): dep for dep in deps} | named_deps

        return fn

    return dec


def where(**kwargs: Any) -> Callable[[TestCaseClass], TestCaseClass]:
    """Provide the given options to the given fixtures"""

    def decorator(test_case: TestCaseClass) -> TestCaseClass:
        test_case_options = _OPTIONS.setdefault(test_case, {})
        test_case_options.update(kwargs)
        return test_case

    return decorator


def make_wrapper(method: TestMethodWithFixturesKwarg) -> Callable[[TestCase], Any]:
    """Wrap the given method so that the fixtures kwarg is passed"""

    @wraps(method)
    def wrapper(self: TestCase) -> Any:
        return method(self, fixtures=_FIXTURES[self])

    wrapper.__unittest_fixtures_wrapped__ = method  # type: ignore
    return wrapper


def add_fixtures(test: TestCase, reqs: dict[str, FixtureSpec]) -> None:
    """Given the TestCase call the fixture functions given by specs and add them to the
    _FIXTURES table
    """
    fixtures = _FIXTURES[test]
    for name, spec in reqs.items():
        func = load(spec)
        if deps := _DEPS.get(func, {}):
            add_fixtures(test, deps)
        if not hasattr(fixtures, name):
            setattr(fixtures, name, apply_func(func, name, test))


def ancestor_requirements(test_case: TestCaseClass) -> dict[str, FixtureSpec]:
    """Gather the requirements of the test_case's ancestors"""
    reqs = {}
    for ancestor in reversed(test_case.mro()):
        reqs.update(_REQUIREMENTS.get(ancestor, {}))
    return reqs


def apply_func(func: FixtureFunction, name: str, test: TestCase) -> Any:
    """Apply the given fixture func to the given test options and return the result

    If func is a generator function, apply it and add it to the test's cleanup.
    """
    fixtures = copy(_FIXTURES[test])
    test_case = type(test)
    test_opts = {
        k: v
        for test_case in (*reversed(test_case.mro()), test_case)
        for k, v in _OPTIONS.get(test_case, {}).items()
    }
    opts = opts_for_name(name, test_opts)

    if inspect.isgeneratorfunction(func):
        return test.enterContext(contextmanager(func)(fixtures, **opts))

    return func(fixtures, **opts)


def load(spec: FixtureSpec) -> FixtureFunction:
    """Load and return the FixtureFunction given by FixtureSpec

    If spec is a string, the function is imported from the project's settings, which
    defaults to "tests.fixtures".  Otherwise the given spec is returned.
    """
    if not isinstance(spec, str):
        return spec

    fixtures_module = get_fixtures_module()
    return cast(FixtureFunction, getattr(fixtures_module, spec))


@cache
def funcname(spec: FixtureSpec) -> str:
    """Return the fixture name of the given function"""
    if isinstance(spec, str):
        return spec

    func_name = spec.__name__

    return func_name.removesuffix("_fixture")


@cache
def get_fixtures_module() -> ModuleType:
    """Load the fixtures module

    Given the path of the fixtures module in pyproject.toml, load and return the module.
    If no path is given in pyproject.toml then the path defaults to "tests.fixtures"
    """
    module_path = "tests.fixtures"
    try:
        with open("pyproject.toml", "rb") as pyproject_toml:
            project = tomllib.load(pyproject_toml)
    except FileNotFoundError:
        pass
    else:
        settings = project.get("tool", {}).get("unittest-fixtures", {})
        module_path = settings.get("fixtures-module", module_path)

    return importlib.import_module(module_path)


def opts_for_name(name: str, options: dict[str, Any]) -> dict[str, Any]:
    """Return dict of options for the fixture with the given name"""
    return {
        fixture_option_name or fixture_name: value
        for key, value in options.items()
        for fixture_name, _, fixture_option_name in [key.partition("__")]
        if fixture_name == name
    }
