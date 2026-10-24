# Makefile
# popo/examples/python
#
# Copyright © 2026 Dagitali LLC. All rights reserved.
#
# Delegate repository guardrails to one explicit Popo profile.

.PHONY: guardrails test

guardrails:
	popo check-all --profile guardrails

# Application tests are separate from Popo's read-only inspection.
test:
	python -m unittest discover -s tests
