"""Fixtures framework"""

# pylint: disable=protected-access
import importlib
import inspect
import tomllib
import unittest
from contextlib import contextmanager
from copy import copy
from functools import cache, wraps
from types import ModuleType, SimpleNamespace
from typing import Any, Callable, Iterable, Iterator, TypeAlias, TypeVar, cast

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


TestCaseClass: TypeAlias = type[TestCase]

BaseTestCase = TestCase  # for backwards compatibility

_REQUIREMENTS: dict[TestCaseClass, dict[str, FixtureSpec]] = {}


def requires(
    *requirements: FixtureSpec, **named_requirements: FixtureSpec
) -> Callable[[TestCaseClass], TestCaseClass]:
    """Decorate the TestCase to include the fixtures given by the FixtureSpec"""

    def decorator(test_case: TestCaseClass) -> TestCaseClass:
        _REQUIREMENTS[test_case] = {
            funcname(func): func for req in requirements for func in [load(req)]
        }
        for name, req in named_requirements.items():
            _REQUIREMENTS[test_case][name] = load(req)

        def setup(self: TestCase) -> None:
            super(test_case, self).setUp()

            self.fixtures = getattr(self, "fixtures", None) or Fixtures()
            self._options = get_options(self, test_case)

            setups = _REQUIREMENTS.get(test_case, {})
            add_fixtures(self, setups)

            if hasattr(self, "post_setup"):
                self.post_setup()

        setattr(test_case, "setUp", setup)
        return test_case

    return decorator


def depends(
    *deps: FixtureSpec, **named_deps: FixtureSpec
) -> Callable[[FixtureFunction], FixtureFunction]:
    """Decorate the fixture to require fixtures given by the FixtureSpec"""

    def dec(fn: FixtureFunction) -> FixtureFunction:
        fn_deps: dict[str, FixtureSpec] = {funcname(dep): load(dep) for dep in deps}

        for name, dep in named_deps.items():
            fn_deps[name] = load(dep)

        fn._deps = fn_deps  # type: ignore[attr-defined]

        return fn

    return dec


T = TypeVar("T", bound=TestCase)
Param: TypeAlias = list[Any]
Params: TypeAlias = list[Param]
TestFunc: TypeAlias = Callable[..., Any]


def parametrized(lists_of_args: Params) -> Callable[[TestFunc], TestFunc]:
    """Turn TestCase test method into parametrized test"""

    def dec(func: TestFunc) -> TestFunc:
        @wraps(func)
        def wrapper(self: T, *args: Any, **kwargs: Any) -> None:
            for list_of_args in lists_of_args:
                name = ",".join(str(i) for i in list_of_args)
                with self.subTest(name):
                    func(self, *args, *list_of_args, **kwargs)

        return wrapper

    return dec


def get_options(test: TestCase, test_case: TestCaseClass) -> FixtureOptions:
    """Return test's new options given the TestCase's options"""
    options = test._options = getattr(test, "_options", {}).copy()
    options.update(getattr(test_case, "options", {}))

    return options


def add_fixtures(test: TestCase, reqs: dict[str, FixtureSpec]) -> None:
    """Given the TestCase call the fixture functions given by specs and add them to the
    test's .fixtures attribute
    """
    for name, spec in reqs.items():
        func = load(spec)
        if deps := getattr(func, "_deps", {}):
            add_fixtures(test, deps)
        if not hasattr(test.fixtures, name):
            setattr(test.fixtures, name, apply_func(func, test))


def apply_func(func: FixtureFunction, test: TestCase) -> Any:
    """Apply the given fixture func to the given test options and return the result

    If func is a generator function, apply it and add it to the test's cleanup.
    """
    fixtures = copy(test.fixtures)

    if inspect.isgeneratorfunction(func):
        return test.enterContext(contextmanager(func)(test._options, fixtures))

    return func(test._options, fixtures)


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


@cache
def funcname(spec: FixtureSpec) -> str:
    """Return the fixture name of the given function"""
    if isinstance(spec, str):
        return spec

    func_name = spec.__name__

    return func_name.removesuffix("_fixture")
