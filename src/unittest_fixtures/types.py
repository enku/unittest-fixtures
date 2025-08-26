"""unittest type definitions"""

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Callable, Iterable, Iterator, NamedTuple, TypeAlias
from unittest import TestCase


class Fixtures(SimpleNamespace):  # pylint: disable=too-few-public-methods
    '''This is mainly so errors say "Fixtures" instead of "SimpleNamespace"'''


FixtureContext: TypeAlias = Iterator
FixtureFunction: TypeAlias = Callable[[Fixtures], Any]
TestCaseClass: TypeAlias = type[TestCase]


@dataclass(frozen=True, kw_only=True)
class State:
    """namespace for state variables"""

    requirements: dict[TestCaseClass, dict[str, FixtureFunction]]
    deps: dict[FixtureFunction, dict[str, FixtureFunction]]
    options: dict[TestCaseClass, dict[str, Any]]
    params: dict[TestCaseClass, dict[str, Iterable[Any]]]


class Param(NamedTuple):
    """A parameter to pass to a fixture (in a @where)"""

    func: Callable[[Fixtures], Any]
