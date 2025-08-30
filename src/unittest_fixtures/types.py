"""unittest type definitions"""

from dataclasses import dataclass, field
from functools import partial
from types import SimpleNamespace
from typing import Any, Callable, Iterable, Iterator, NamedTuple, TypeAlias
from unittest import TestCase

dict_field = partial(field, default_factory=dict)


class Fixtures(SimpleNamespace):  # pylint: disable=too-few-public-methods
    '''This is mainly so errors say "Fixtures" instead of "SimpleNamespace"'''


FixtureContext: TypeAlias = Iterator
FixtureFunction: TypeAlias = Callable[[Fixtures], Any]
TestCaseClass: TypeAlias = type[TestCase]


@dataclass(frozen=True, kw_only=True)
class State:
    """namespace for state variables"""

    requirements: dict[TestCaseClass, dict[str, FixtureFunction]] = dict_field()
    deps: dict[FixtureFunction, dict[str, FixtureFunction]] = dict_field()
    options: dict[TestCaseClass, dict[str, Any]] = dict_field()
    params: dict[TestCaseClass, dict[str, Iterable[Any]]] = dict_field()
    combine: dict[TestCaseClass, dict[str, Iterable[Any]]] = dict_field()


class Param(NamedTuple):
    """A parameter to pass to a fixture (in a @where)"""

    func: Callable[[Fixtures], Any]

    def __call__(self, fixtures: Fixtures) -> Any:
        return self.func(fixtures)
