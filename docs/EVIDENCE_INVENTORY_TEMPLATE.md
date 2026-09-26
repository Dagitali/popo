<!--
EVIDENCE_INVENTORY_TEMPLATE.md
popo/docs

Copyright © 2026 Dagitali LLC. All rights reserved.

Optional evidence inventory for public technical claims and release statements.

Maintainer Notes
- Keep this template blank; store sensitive completed records outside the repository.
- Distinguish source, test, artifact, hosted-operation, and publication evidence.
-->

# Evidence Inventory Template

Use this template when a technical claim, compatibility statement, quantitative result, or release
assertion needs more evidence than a straightforward source link. Copy it into an appropriate
working system; it is not an additional mandatory gate for every documentation edit.

Keep only the blank template here. Completed records containing private consumer data, credentials,
vulnerability details, personal information, or confidential logs belong in an access-controlled
system. A sanitized public statement should link only to evidence its audience can access.

- [Candidate Claim](#candidate-claim)
- [Authority and Disclosure](#authority-and-disclosure)
- [Verification](#verification)
- [Metrics and Outcomes](#metrics-and-outcomes)
- [Publication Decision](#publication-decision)

## Candidate Claim

| Field | Record |
| --- | --- |
| Working title | |
| Evidence owner | |
| Evidence category | Implementation / automated test / release artifact / hosted result / consumer report / primary external source / other |
| Source location | |
| Public or private | |
| Proposed claim | |
| Intended documentation, release, or policy surface | |

## Authority and Disclosure

| Question | Record |
| --- | --- |
| Who owns the source material? | |
| Who can authorize disclosure, if needed? | |
| Is written authorization required, and where is it recorded? | |
| Which names, quotations, screenshots, or identifiers may be included? | |
| Which facts must remain private? | |
| Could the wording imply unsupported endorsement, compatibility, security, or release status? | |

## Verification

| Question | Record |
| --- | --- |
| What can the intended reader inspect? | |
| Which source, test, artifact, or hosted result supports the claim? | |
| What exact commit, tag, or artifact does the evidence describe? | |
| Which command, environment, configuration, and dependency versions produced the result? | |
| Which checks passed, failed, or were skipped? | |
| What limitations, uncertainties, or ownership boundaries accompany the claim? | |
| Is the evidence current for the claimed version? | |
| Who verified it, and on what date? | |

A passing checker establishes only the policy it actually validates. Source tests do not establish
clean-install compatibility, and local workflow checks do not prove hosted protections are active.
A built distribution is not evidence of publication. Use the [testing guide] and [release playbook]
to select evidence appropriate to the claim; preserve exact tag and artifact identities.

## Metrics and Outcomes

Complete this section only for a quantitative claim, such as coverage or execution time.

| Question | Record |
| --- | --- |
| Metric definition and units | |
| Baseline, comparison period, and sample scope | |
| Data source | |
| Calculation method, command, or tool configuration | |
| Material confounding factors and excluded cases | |
| Exact proposed public wording | |

## Publication Decision

| Field | Record |
| --- | --- |
| Decision | Publish / revise / hold / reject |
| Approved wording, where approval is required | |
| Required attribution | |
| Reviewer and review date | |
| Next review date or invalidating change | |

Before using the wording, follow the [documentation synchronization guide] and state material
limitations alongside the claim. This record does not authorize publishing packages, creating tags,
disclosing private material, or changing hosted settings. Use the [incident runbook] for failures;
do not expose sensitive incident or vulnerability evidence in public issues or completed templates.

[documentation synchronization guide]: ../CONTRIBUTING.md#documentation-synchronization
[testing guide]: TESTING.md
[release playbook]: playbooks/release.md
[incident runbook]: runbooks/incident-response.md
