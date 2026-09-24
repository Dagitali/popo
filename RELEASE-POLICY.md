# Release Policy

`popo` separates validation from publication. No workflow publishes to PyPI or deploys cloud
resources. Package versions come from Git tags through `setuptools-scm`.

## Candidate validation

The [CD workflow] validates pushed `v*.*.*` tags or a manually selected existing tag. A valid
release tag is annotated, uses `vMAJOR.MINOR.PATCH`, and points to a commit reachable from the
repository's default branch. Tags must not be moved. The tagged checkout must contain the current
packaging, tests, and setup action; older incompatible tags fail validation rather than bypassing
it.

Validation requires a dated changelog entry, `make check`, both built distributions, `twine check`,
clean-install tests, and a wheel version matching the tag. The workflow builds distributions once
and generates a validated runtime SBOM and SHA-256 checksums for those artifacts. Downloads remain
available as workflow artifacts for 14 days.

- [Candidate validation](#candidate-validation)
- [Opt-in GitHub publication](#opt-in-github-publication)
- [Disposable installation test](#disposable-installation-test)

## Opt-in GitHub publication

Publication is disabled by default. To enable it, a maintainer must:

1. Configure the `release` GitHub environment with required reviewers and appropriate branch
   restrictions. Merely referencing an environment does not configure protection.
2. Set the repository variable `ENABLE_RELEASE_PUBLISHING` to exactly `true`.
3. Manually run CD **from the default branch**, select an existing release tag, and explicitly
   select `publish`.
4. Review and approve the environment job when prompted.

The publication job receives only the validated artifacts. It does not check out or run tagged
project code. It checks the remote tag object has not changed and verifies artifact checksums before
creating the GitHub Release. Existing releases are not overwritten; historical releases are not
automatically marked latest. The token is scoped to that job.

Environment protection depends on repository configuration and GitHub plan capabilities. Do not
enable publication without the intended protections. These local files do not configure reviewers,
repository variables, branch protection, or PyPI credentials.

## Disposable installation test

[deployment-test.yml] is the package-oriented equivalent of a disposable deployment test. Run it
manually against the selected workflow ref to build and install its wheel and sdist in clean
environments on Linux, macOS, and Windows with Python 3.13 and 3.14. It tests CLI help, version,
successful checks, and failing checks outside the checkout. Hosted runners dispose of the temporary
environments. It does not test a published PyPI package, mutate a consumer repository, or deploy
AWS.

[CD workflow]: .github/workflows/cd.yml
[deployment-test.yml]: .github/workflows/deployment-test.yml
