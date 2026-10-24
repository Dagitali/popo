# Makefile
# popo/examples/cdk
#
# Copyright © 2026 Dagitali LLC. All rights reserved.
#
# Delegate repository guardrails to one explicit Popo profile.

.PHONY: guardrails test synth

guardrails:
	popo check-all --profile guardrails

# Application tests are separate from Popo's read-only inspection.
test:
	python -m unittest discover -s tests

# Explicit local synthesis writes cdk.out; guardrails never invoke it.
synth:
	python app.py
