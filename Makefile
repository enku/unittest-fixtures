.SHELL := /bin/bash

name := $(shell pdm show --name)
version := $(shell pdm show --version)
sdist := dist/$(name)-$(version).tar.gz
wheel := dist/$(subst -,_,$(name))-$(version)-py3-none-any.whl
src := $(shell find src -type f -print)
tests := $(shell find tests -type f -print)

PYTHONDONTWRITEBYTECODE=1

export PYTHONDONTWRITEBYTECODE


.coverage: $(src) $(tests)
	pdm run coverage run -m unittest discover tests

test: .coverage
.PHONY: test


coverage-report: .coverage
	pdm run coverage html
	pdm run python -m webbrowser -t file://$(CURDIR)/htmlcov/index.html

build: $(sdist) $(wheel)

wheel: $(wheel)
.PHONY: wheel


sdist: $(sdist)
.PHONY: sdist


$(sdist): $(src)
	pdm build --no-wheel

$(wheel): $(src)
	pdm build --no-sdist

clean: clean-build
	rm -rf .coverage htmlcov .mypy_cache
.PHONY: clean


clean-build:
	rm -rf dist build
.PHONY: clean-build


shell:
	pdm run $(.SHELL) -l
.PHONY: shell


pylint:
	pdm run pylint src tests
.PHONY: pylint


mypy:
	pdm run mypy
.PHONY: mypy


.PHONY: typos
typos:
	typos --format=brief


lint: pylint mypy typos
.PHONY: lint


fmt:
	pdm run python -m isort --line-width=88 src tests
	pdm run python -m black src tests
.PHONY: fmt


.PHONY: update
update:
	pdm update --update-eager
