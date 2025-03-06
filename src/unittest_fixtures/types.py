"""unittest type definitions"""

from types import SimpleNamespace
from typing import Any, Callable, Iterator, TypeAlias
from unittest import TestCase

Fixtures: TypeAlias = SimpleNamespace
FixtureContext: TypeAlias = Iterator
FixtureFunction: TypeAlias = Callable[[Fixtures], Any]
FixtureSpec: TypeAlias = str | FixtureFunction
TestCaseClass: TypeAlias = type[TestCase]
