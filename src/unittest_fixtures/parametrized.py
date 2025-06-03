"""Parametrized subTest helper"""

from functools import wraps
from typing import Any, Callable, TypeAlias, TypeVar
from unittest import TestCase

Param: TypeAlias = list[Any]
Params: TypeAlias = list[Param]
T = TypeVar("T", bound=TestCase)
TestFunc: TypeAlias = Callable[..., Any]


def parametrized(lists_of_args: Params) -> Callable[[TestFunc], TestFunc]:
    """Turn TestCase test method into parametrized test"""

    def decorator(func: TestFunc) -> TestFunc:
        @wraps(func)
        def wrapper(self: T, *args: Any, **kwargs: Any) -> None:
            for list_of_args in lists_of_args:
                name = ",".join(str(i) for i in list_of_args)
                with self.subTest(name):
                    func(self, *args, *list_of_args, **kwargs)

        return wrapper

    return decorator
