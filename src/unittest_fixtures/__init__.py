"""Fixtures framework"""

import importlib
import inspect
import tomllib
from contextlib import contextmanager
from copy import copy
from functools import cache, partial, wraps
from types import ModuleType, SimpleNamespace
from typing import Any, Callable, Iterable, Iterator, Protocol, TypeAlias, TypeVar, cast
from unittest import TestCase

Fixtures: TypeAlias = SimpleNamespace
FixtureContext: TypeAlias = Iterator
FixtureFunction: TypeAlias = Callable[[Any, Fixtures], Any]
FixtureSpec: TypeAlias = str | FixtureFunction


TestCaseClass: TypeAlias = type[TestCase]
_REQUIREMENTS: dict[TestCaseClass, dict[str, FixtureSpec]] = {}
_DEPS: dict[FixtureFunction, dict[str, FixtureSpec]] = {}
_OPTIONS: dict[TestCaseClass, dict[str, Any]] = {}
_FIXTURES: dict[TestCase, Fixtures] = {}


def given(
    *requirements: FixtureSpec, **named_requirements: FixtureSpec
) -> Callable[[TestCaseClass], TestCaseClass]:
    """Decorate the TestCase to include the fixtures given by the FixtureSpec"""

    def decorator(test_case: TestCaseClass) -> TestCaseClass:
        _REQUIREMENTS[test_case] = {
            funcname(func): func for req in requirements for func in [req]
        }
        for name, req in named_requirements.items():
            _REQUIREMENTS[test_case][name] = req

        for name, method in test_case.__dict__.items():
            if callable(method) and (name == "test" or name.startswith("test")):
                setattr(test_case, name, make_wrapper(method))

        original_setup = getattr(test_case, "setUp", lambda *args, **kwargs: None)

        def setup(self: TestCase, *args: Any, **kwargs: Any) -> None:
            _FIXTURES[self] = Fixtures()
            setups = _REQUIREMENTS.get(test_case, {})
            add_fixtures(self, setups)

            original_setup(self, *args, **kwargs)
            self.addCleanup(lambda: _FIXTURES.pop(self, None))

        setattr(test_case, "setUp", setup)
        return test_case

    return decorator


class TestMethodWithFixturesKwarg(Protocol):  # pylint: disable=too-few-public-methods
    """Test methods that take a fixtures kwarg"""

    def __call__(self, _self: TestCase, *, fixtures: Fixtures) -> Any: ...


def make_wrapper(method: TestMethodWithFixturesKwarg) -> Callable[[TestCase], Any]:
    """Wrap the given method so that the fixtures kwarg is passed"""

    @wraps(method)
    def wrapper(self: TestCase) -> Any:
        return method(self, fixtures=_FIXTURES[self])

    return wrapper


def fixture(
    *deps: FixtureSpec, **named_deps: FixtureSpec
) -> Callable[[FixtureFunction], FixtureFunction]:
    """Declare fixture requiring fixtures given by the FixtureSpec"""

    def dec(fn: FixtureFunction) -> FixtureFunction:
        fn_deps: dict[str, FixtureSpec] = {funcname(dep): dep for dep in deps}

        for name, dep in named_deps.items():
            fn_deps[name] = dep

        _DEPS[fn] = fn_deps

        return fn

    return dec


def where(**kwargs: Any) -> Callable[[TestCaseClass], TestCaseClass]:
    """Provide the given options to the given fixtures"""

    def decorator(test_case: TestCaseClass) -> TestCaseClass:
        test_case_options = _OPTIONS.setdefault(test_case, {})
        test_case_options.update(kwargs)
        return test_case

    return decorator


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


def apply_func(func: FixtureFunction, name: str, test: TestCase) -> Any:
    """Apply the given fixture func to the given test options and return the result

    If func is a generator function, apply it and add it to the test's cleanup.
    """
    fixtures = copy(_FIXTURES[test])
    cls = type(test)
    test_opts = {
        k: v for cls in (*cls.mro(), cls) for k, v in _OPTIONS.get(cls, {}).items()
    }
    opts = test_opts.get(name)

    if inspect.isgeneratorfunction(func):
        return test.enterContext(contextmanager(func)(opts, fixtures))

    return func(opts, fixtures)


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
