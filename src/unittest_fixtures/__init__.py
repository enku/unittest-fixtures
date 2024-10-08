"""Fixtures framework"""

# pylint: disable=protected-access
import copy
import importlib
import inspect
import tomllib
import unittest
from contextlib import contextmanager
from functools import cache
from types import ModuleType, SimpleNamespace
from typing import Any, Callable, Iterable, Iterator, TypeAlias

_REQUIREMENTS = {}

Fixtures: TypeAlias = SimpleNamespace
FixtureOptions: TypeAlias = dict[str, Any]
FixtureContext: TypeAlias = Iterator
FixtureFunction: TypeAlias = Callable[[FixtureOptions, Fixtures], Any]
FixtureSpec: TypeAlias = str | FixtureFunction


class TestCase(unittest.TestCase):
    """Fixtures TestCase

    TestCases that use fixtures are not required to inherit from this base class,
    however doing so will make the type checkers happier.
    """

    _options: FixtureOptions
    options: FixtureOptions = {}
    fixtures: Fixtures


BaseTestCase = TestCase  # for backwards compatibility


def requires(
    *requirements: FixtureSpec,
) -> Callable[[type[TestCase]], type[TestCase]]:
    """Decorate the TestCase to include the fixtures given by the FixtureSpec"""

    def decorator(test_case: type[TestCase]) -> type[TestCase]:
        setups = {}
        for requirement in requirements:
            func = load(requirement)
            name = func.__name__.removesuffix("_fixture")
            setups[name] = func
        _REQUIREMENTS[test_case] = setups

        def setup(self: TestCase) -> None:
            super(test_case, self).setUp()

            self.fixtures = getattr(self, "fixtures", None) or Fixtures()
            self._options = get_options(self, test_case)

            setups = _REQUIREMENTS.get(test_case, {})
            add_fixtures(self, setups.values())

            if hasattr(self, "post_setup"):
                self.post_setup()

        setattr(test_case, "setUp", setup)
        return test_case

    return decorator


def depends(*deps: FixtureSpec) -> Callable[[FixtureFunction], FixtureFunction]:
    """Decorate the fixture to require fixtures given by the FixtureSpec"""

    def dec(fn: FixtureFunction) -> FixtureFunction:
        fn._deps = list(deps)  # type: ignore[attr-defined]
        return fn

    return dec


def get_options(test: TestCase, test_case: type[TestCase]) -> FixtureOptions:
    """Return test's new options given the TestCase's options"""
    options = test._options = getattr(test, "_options", {}).copy()
    options.update(getattr(test_case, "options", {}))

    return options


def add_fixtures(test: TestCase, specs: Iterable[FixtureSpec]) -> None:
    """Given the TestCase call the fixture functions given by specs and add them to the
    test's .fixtures attribute
    """
    for func in [load(spec) for spec in specs]:
        name = func.__name__.removesuffix("_fixture")
        if deps := getattr(func, "_deps", []):
            add_fixtures(test, deps)
        if not hasattr(test.fixtures, name):
            setattr(test.fixtures, name, get_result(func, test))


def get_result(func: FixtureFunction, test: TestCase) -> Any:
    """Apply the given fixture func to the given test options and return the result

    If func is a generator function, apply it and add it to the test's cleanup.
    """
    if inspect.isgeneratorfunction(func):
        return test.enterContext(
            contextmanager(func)(test._options, copy.copy(test.fixtures))
        )

    return func(test._options, copy.copy(test.fixtures))


def load(spec: FixtureSpec) -> FixtureFunction:
    """Load and return the FixtureFunction given by FixtureSpec


    If spec is a string, the function is imported from the project's settings, which
    defaults to "tests.fixtures".  Otherwise the given spec is returned.
    """
    fixtures_module = get_fixtures_module()
    func: FixtureFunction = (
        getattr(fixtures_module, spec) if isinstance(spec, str) else spec
    )

    return func


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
