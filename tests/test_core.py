# pylint: disable=missing-docstring
from pathlib import Path

import unittest_fixtures as uf
from tests import fixtures, fixtures1


@uf.requires("cd_to_tmpdir", "clear_cache")
class GetFixturesModuleTests(uf.BaseTestCase):
    def test_defaults_to_tests_fixtures(self) -> None:
        fixtures_module = uf.get_fixtures_module()

        self.assertIs(fixtures_module, fixtures)

    def test_with_speficied_module(self) -> None:
        project_toml_path: Path = self.fixtures.tmpdir / "pyproject.toml"
        project_toml_path.write_text(PYPROJECT_TOML % "tests.fixtures1")

        fixtures_module = uf.get_fixtures_module()

        self.assertIs(fixtures_module, fixtures1)


PYPROJECT_TOML = """\
[tool.unittest-fixtures]
fixtures-module = "%s"
"""
