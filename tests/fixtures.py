# pylint: disable=missing-docstring
import os
import tempfile
from pathlib import Path

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
