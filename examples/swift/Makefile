# Makefile
# popo/examples/swift
#
# Copyright © 2026 Dagitali LLC. All rights reserved.
#
# Delegate repository guardrails to one explicit Popo profile.

.PHONY: guardrails test

guardrails:
	popo check-all --profile guardrails

# Swift compilation and tests are separate from Popo's read-only inspection.
test:
	swift test
