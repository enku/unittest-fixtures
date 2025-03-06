# pylint: disable=missing-docstring
from unittest import TestCase
from unittest.result import TestResult

_unittest = True  # pylint: disable=invalid-name


def assert_test_result(self: TestCase, result: TestResult | None) -> None:
    self.assertIsNotNone(result, "No result given")
    assert result

    if result.failures:
        msg = ""
        for failure in result.failures:
            msg = f"{msg}\n{'\n'.join(str(f) for f in failure)}"
            self.fail(msg)
    if result.errors:
        msg = ""
        for error in result.errors:
            msg = f"{msg}\n{'\n'.join(str(f) for f in error)}"
            self.fail(msg)
