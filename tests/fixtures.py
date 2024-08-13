# pylint: disable=missing-docstring
import os
import tempfile
from pathlib import Path
from unittest import mock

import unittest_fixtures as uf


def tmpdir(_: uf.FixtureOptions, _fixtures: uf.Fixtures) -> uf.FixtureContext[Path]:
    with tempfile.TemporaryDirectory() as tempdir:
        yield Path(tempdir)


@uf.depends(tmpdir)
def cd_to_tmpdir(
    _: uf.FixtureOptions, fixtures: uf.Fixtures
) -> uf.FixtureContext[None]:
    origdir = os.getcwd()
    os.chdir(fixtures.tmpdir)
    yield

    os.chdir(origdir)


def clear_cache(_options: uf.FixtureOptions, _fixtures: uf.Fixtures) -> None:
    uf.get_fixtures_module.cache_clear()


def test_class(
    _options: uf.FixtureOptions, _fixtures: uf.Fixtures
) -> type[uf.BaseTestCase]:
    class Test(uf.BaseTestCase):
        pass

    return Test


def one(_options: uf.FixtureOptions, _fixtures: uf.Fixtures) -> int:
    return 1


def two(_options: uf.FixtureOptions, _fixtures: uf.Fixtures) -> int:
    return 2


@uf.depends(two)
def three(_options: uf.FixtureOptions, _fixtures: uf.Fixtures) -> int:
    return 3


def four_fixture(_options: uf.FixtureOptions, _fixtures: uf.Fixtures) -> int:
    return 4


def uf_requirements(
    _options: uf.FixtureOptions, _fixtures: uf.Fixtures
) -> uf.FixtureContext[dict]:
    """Patches the unittest_fixtures._REQUIREMENTS dict"""
    with mock.patch.dict(uf._REQUIREMENTS, {}, clear=True):
        yield uf._REQUIREMENTS
