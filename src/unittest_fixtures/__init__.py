"""Fixtures framework"""

# pylint: disable=protected-access
import copy
import importlib
import inspect
import tomllib
from contextlib import contextmanager
from functools import cache
from types import ModuleType, SimpleNamespace
from typing import Any, Callable, Iterable, Iterator, TypeAlias
from unittest import TestCase

_REQUIREMENTS = {}

Fixtures: TypeAlias = SimpleNamespace
FixtureOptions: TypeAlias = dict[str, Any]
FixtureContext: TypeAlias = Iterator
FixtureFunction: TypeAlias = Callable[[FixtureOptions, Fixtures], Any]
FixtureSpec: TypeAlias = str | FixtureFunction


class BaseTestCase(TestCase):
    _options: FixtureOptions
    options: FixtureOptions = {}
    fixtures: Fixtures


def load(spec: FixtureSpec) -> FixtureFunction:
    fixtures_module = get_fixtures_module()
    func: FixtureFunction = (
        getattr(fixtures_module, spec) if isinstance(spec, str) else spec
    )

    return func


def depends(*deps: FixtureSpec) -> Callable[[FixtureFunction], FixtureFunction]:
    def dec(fn: FixtureFunction) -> FixtureFunction:
        fn._deps = list(deps)  # type: ignore[attr-defined]
        return fn

    return dec


def requires(
    *requirements: FixtureSpec,
) -> Callable[[type[BaseTestCase]], type[BaseTestCase]]:
    def decorator(test_case: type[BaseTestCase]) -> type[BaseTestCase]:
        setups = {}
        for requirement in requirements:
            func = load(requirement)
            name = func.__name__.removesuffix("_fixture")
            setups[name] = func
        _REQUIREMENTS[test_case] = setups

        def setup(self: BaseTestCase) -> None:
            super(test_case, self).setUp()

            setups = _REQUIREMENTS.get(test_case, {})
            add_funcs(self, setups.values())

        setattr(test_case, "setUp", setup)
        return test_case

    return decorator


def add_funcs(test: BaseTestCase, specs: Iterable[FixtureSpec]) -> None:
    test.fixtures = getattr(test, "fixtures", None) or Fixtures()
    test._options = getattr(test, "_options", {})
    test._options.update(getattr(type(test), "options", {}))

    for func in [load(spec) for spec in specs]:
        name = func.__name__.removesuffix("_fixture")
        if deps := getattr(func, "_deps", []):
            add_funcs(test, deps)
        if not hasattr(test.fixtures, name):
            setattr(test.fixtures, name, get_result(func, test))


def get_result(func: FixtureFunction, test: BaseTestCase) -> Any:
    if inspect.isgeneratorfunction(func):
        return test.enterContext(
            contextmanager(func)(test._options, copy.copy(test.fixtures))
        )

    return func(test._options, copy.copy(test.fixtures))


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
