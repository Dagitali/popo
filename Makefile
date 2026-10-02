# Makefile
# popo
#
# Copyright © 2026 Dagitali LLC. All rights reserved.
#
# Facilitates automation for local development environments.
#
# Responsibilities
# - Automate common local setup, quality, testing, and packaging workflows.
# - Provide stable, discoverable entry points shared by contributors and CI.
#
# Maintainer Notes
# - Keep common target names consistent when their behavior is equivalent.
# - Keep project-specific commands and variables clearly labeled so reusable
#   conventions can be extracted without coupling projects.
# - Prefer overridable variables for paths, interpreters, and outputs.
# - Honor active environments, otherwise prefer the managed environment.
#   Never implicitly install dependencies.
# - Preserve the default check gate and combined lint/format validation.
# - Distribution tests build temporary artifacts unless explicitly given a
#   path.
# - No target publishes packages, deploys resources, or deletes build output.
# - Environment setup is explicit; never replace an existing environment.
#
# References
# - GNU Make documentation:
#   https://www.gnu.org/software/make/manual/make.html
# - GNU Make conventions:
#   https://www.gnu.org/prep/standards/html_node/Makefile-Conventions.html
#
# Common Flows
# $ make help
# $ make dev PY=python3.13
# $ make show-venv
# $ make check
# $ make test
# $ make docs-markdown
# $ make check-release

# SECTION: VARIABLES

### Make ###

.DEFAULT_GOAL := check
HELP_TARGET_WIDTH ?= 22

### Project ###

PROJECT_TOOLS_MODULE ?= popo
TESTS_DIR ?= tests
RELEASE_VERSION ?=

### Python ###

# PY bootstraps the managed environment; PYTHON remains the check interpreter.
PY ?= python3
MINIMUM_PYTHON_VERSION ?= 3.13
MAXIMUM_PYTHON_VERSION ?= 3.15
VENV_DIR ?= .venv
ifeq ($(OS),Windows_NT)
VENV_BIN := $(VENV_DIR)/Scripts
VENV_PYTHON := $(VENV_BIN)/python.exe
else
VENV_BIN := $(VENV_DIR)/bin
VENV_PYTHON := $(VENV_BIN)/python
endif

# Explicit overrides win; CI can use PATH when no local environment exists.
ifneq ($(strip $(VIRTUAL_ENV)),)
PYTHON ?= python3
else ifneq ($(shell test -x "$(VENV_PYTHON)" && echo yes),)
PYTHON ?= "$(VENV_PYTHON)"
else
PYTHON ?= python3
endif
MYPY ?= $(PYTHON) -m mypy
PRE_COMMIT ?= $(PYTHON) -m pre_commit
PYTEST ?= $(PYTHON) -m pytest
RUFF ?= $(PYTHON) -m ruff
PYTHON_BUILD ?= $(PYTHON) -m build
TWINE ?= $(PYTHON) -m twine
PYTHON_FORMAT_PATHS ?= .
PYTHON_LINT_PATHS ?= $(PYTHON_FORMAT_PATHS)
PYTHON_DIST_DIR ?= dist
HOOK_INSTALL_ARGS ?=

# Local checks use this checkout, even when an editable-install hook is unavailable.
# Distribution installation tests explicitly remove this source-path override.
export PYTHONPATH := $(CURDIR)/src$(if $(PYTHONPATH),$(if $(filter Windows_NT,$(OS)),;,:)$(PYTHONPATH))

### Installation ###

PIP_INSTALL_FLAGS ?= --disable-pip-version-check
RUNTIME_INSTALL_ARGS ?= -e "$(CURDIR)"
DEV_INSTALL_ARGS ?= -e "$(CURDIR)[dev]"

### Packaging (Python) ###

DIST_BUILD_COMMAND ?= $(PYTHON_BUILD) --outdir "$(PYTHON_DIST_DIR)"
DIST_CHECK_COMMAND ?= $(TWINE) check "$(PYTHON_DIST_DIR)"/*

### Testing ###

TEST_ARGS ?=
UNIT_TEST_PATH ?= $(TESTS_DIR)/unit
UNIT_TEST_ARGS ?= $(TEST_ARGS) "$(UNIT_TEST_PATH)"
INTEGRATION_TEST_PATH ?= $(TESTS_DIR)/integration
INTEGRATION_TEST_ARGS ?= $(TEST_ARGS) "$(INTEGRATION_TEST_PATH)"
DISTRIBUTION_TEST_PATH ?= $(TESTS_DIR)/meta/test_m_package_artifacts.py
DISTRIBUTION_TEST_ARGS ?= $(TEST_ARGS) "$(DISTRIBUTION_TEST_PATH)"
INSTALLATION_TEST_PATH ?= $(TESTS_DIR)/e2e/test_e_distribution_installation.py
INSTALLATION_TEST_ARGS ?= $(TEST_ARGS) "$(INSTALLATION_TEST_PATH)"

# !SECTION

# SECTION: PHONY TARGETS

##@ Utilities

.PHONY: help hooks
help: ## Show this help
	@awk 'BEGIN {FS=":.*##"; printf "Usage: make <TARGET>\n"} \
	/^[a-zA-Z0-9_-]+:.*##/ {printf "  %-*s %s\n", $(HELP_TARGET_WIDTH), $$1, $$2} \
	/^##@/ {printf "\n%s\n", substr($$0, 5)}' $(MAKEFILE_LIST)

hooks: ## Install pre-commit hooks in the active environment
	$(PRE_COMMIT) install $(HOOK_INSTALL_ARGS)

.PHONY: check-python-runtime venv install dev setup show-venv

check-python-runtime: ## Require a supported bootstrap Python version
	@$(PY) -c 'import sys; minimum=tuple(map(int, "$(MINIMUM_PYTHON_VERSION)".split("."))); maximum=tuple(map(int, "$(MAXIMUM_PYTHON_VERSION)".split("."))); raise SystemExit(0 if minimum <= sys.version_info[:2] < maximum else "Python >=$(MINIMUM_PYTHON_VERSION),<$(MAXIMUM_PYTHON_VERSION) is required")'

venv: check-python-runtime ## Create or reuse a matching environment without replacing it
	@test -n "$(strip $(VENV_DIR))" && test "$(abspath $(VENV_DIR))" != "$(CURDIR)" && test "$(abspath $(VENV_DIR))" != / || \
		(echo "VENV_DIR must name a dedicated environment directory" >&2; exit 2)
	@if [ -e "$(VENV_DIR)" ] || [ -L "$(VENV_DIR)" ]; then \
		if [ -L "$(VENV_DIR)" ] || [ ! -f "$(VENV_DIR)/pyvenv.cfg" ] || [ ! -x "$(VENV_PYTHON)" ]; then \
			echo "Existing VENV_DIR is not a usable virtual environment; choose another directory" >&2; exit 2; \
		fi; \
		current="$$("$(VENV_PYTHON)" -c 'import sys; assert sys.prefix != sys.base_prefix; print("%s.%s" % sys.version_info[:2])')" || exit 2; \
		requested="$$($(PY) -c 'import sys; print("%s.%s" % sys.version_info[:2])')" || exit 2; \
		if [ "$$current" != "$$requested" ]; then \
			echo "Existing environment uses Python $$current; requested $$requested. Choose a matching PY or another VENV_DIR; nothing was replaced." >&2; exit 2; \
		fi; \
		echo "Using existing environment: $(VENV_DIR)"; \
	else \
		$(PY) -m venv "$(VENV_DIR)"; \
	fi

install: venv ## Install runtime dependencies in the managed environment
	"$(VENV_PYTHON)" -m pip install $(PIP_INSTALL_FLAGS) $(RUNTIME_INSTALL_ARGS)

dev: venv ## Install development dependencies in the managed environment
	"$(VENV_PYTHON)" -m pip install $(PIP_INSTALL_FLAGS) $(DEV_INSTALL_ARGS)

setup: dev ## Install the development environment (compatibility alias)

show-venv: ## Print managed-environment and interpreter locations
	@printf '%s\n' 'VENV_DIR = $(VENV_DIR)' 'VENV_BIN = $(VENV_BIN)' \
		'PY = $(PY)' 'VENV_PYTHON = $(VENV_PYTHON)' 'PYTHON = $(PYTHON)'

##@ Quality

.PHONY: check check-pre-push self-check fix fmt format format-check lint typecheck
.PHONY: dependency-policy github-actions-pins python-policy release-changelog

check: lint typecheck test self-check ## Run the default local quality gate

check-pre-push: check ## Run the local pre-push checks

self-check: ## Run all configured repository-policy checks
	$(PYTHON) -m $(PROJECT_TOOLS_MODULE) check-all

fix: ## Apply safe Ruff fixes to Python code
	$(RUFF) check --fix $(PYTHON_LINT_PATHS)

fmt: format ## Format Python code (compatibility alias)

format: ## Format Python code and apply safe Ruff fixes
	$(RUFF) format $(PYTHON_FORMAT_PATHS)
	$(RUFF) check --fix $(PYTHON_LINT_PATHS)

format-check: ## Verify Python formatting without changing files
	$(RUFF) format --check $(PYTHON_FORMAT_PATHS)

lint: ## Run Python lint and formatting checks
	$(RUFF) check $(PYTHON_LINT_PATHS)
	$(RUFF) format --check $(PYTHON_FORMAT_PATHS)

typecheck: ## Check Python types using pyproject.toml
	$(MYPY)

dependency-policy: ## Verify lowest dependency constraints match package metadata
	$(PYTHON) -m $(PROJECT_TOOLS_MODULE) check-dependency-boundaries

github-actions-pins: ## Verify remote GitHub Actions use immutable commits
	$(PYTHON) -m $(PROJECT_TOOLS_MODULE) check-github-actions-pins

python-policy: ## Verify the repository-wide supported Python version policy
	$(PYTHON) -m $(PROJECT_TOOLS_MODULE) check-python-policy

release-changelog: ## Verify a dated changelog section (RELEASE_VERSION=x.y.z)
	@test -n "$(strip $(RELEASE_VERSION))" || \
		(echo "RELEASE_VERSION is required" >&2; exit 2)
	$(PYTHON) -m $(PROJECT_TOOLS_MODULE) check-release-changelog "$(RELEASE_VERSION)"

##@ Testing

.PHONY: test test-unit test-integration test-distribution test-installation test-full

test: ## Run the default regression suite
	$(PYTEST) $(TEST_ARGS)

test-unit: ## Run isolated checker and automation contract tests
	$(PYTEST) $(UNIT_TEST_ARGS)

test-integration: ## Run CLI dispatch and reporting integration tests
	$(PYTEST) $(INTEGRATION_TEST_ARGS)

# Without --artifact-dir the fixtures build fresh artifacts in a temporary directory.
test-distribution: ## Build temporary distributions and verify contents and metadata
	$(PYTEST) $(DISTRIBUTION_TEST_ARGS)

test-installation: ## Build and smoke-test wheel and sdist in clean environments
	$(PYTEST) $(INSTALLATION_TEST_ARGS)

test-full: test test-distribution test-installation ## Run all available test suites

##@ Documentation

.PHONY: docs-markdown
docs-markdown: ## Verify local Markdown links and heading anchors
	$(PYTHON) -m $(PROJECT_TOOLS_MODULE) check-docs

##@ Packaging

.PHONY: dist build check-release

dist: ## Build and validate Python distributions without deleting existing output
	$(DIST_BUILD_COMMAND)
	$(DIST_CHECK_COMMAND)

build: dist ## Build Python distributions (compatibility alias)

check-release: check dist ## Validate source and the same built release artifacts
	$(PYTEST) $(TEST_ARGS) "$(TESTS_DIR)/meta" "$(TESTS_DIR)/e2e" --artifact-dir "$(PYTHON_DIST_DIR)"

# !SECTION
