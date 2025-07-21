"""unittest type definitions"""

from types import SimpleNamespace
from typing import Any, Callable, Iterator, TypeAlias
from unittest import TestCase


class Fixtures(SimpleNamespace):  # pylint: disable=too-few-public-methods
    '''This is mainly so errors say "Fixtures" instead of "SimpleNamespace"'''


FixtureContext: TypeAlias = Iterator
FixtureFunction: TypeAlias = Callable[[Fixtures], Any]
TestCaseClass: TypeAlias = type[TestCase]
