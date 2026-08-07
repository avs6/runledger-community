# Versioning Policy

RunLedger Community uses semantic-style release tags with explicit pre-stable channels.

## Current channel

As of Friday, August 7, 2026, the project is in the `alpha` channel and the first tagged release is `v1alpha1`.

## Tag format

Release tags use one of these forms:

- `v1alpha1`, `v1alpha2`, `v1alpha3`
- `v1beta1`, `v1beta2`
- `v1rc1`
- `v1.0.0`
- `v1.0.1`

## Meaning of each channel

- `alpha`: feature velocity is high, APIs and operational defaults may still change, and release notes should call out rough edges clearly.
- `beta`: major product surfaces are expected to exist, but compatibility and operational polish may still evolve.
- `rc`: release candidate. Only targeted bug fixes, docs updates, and release blockers should land here.
- `stable`: semantic versioning applies in the usual `MAJOR.MINOR.PATCH` form.

## Compatibility expectations

- Before `v1.0.0`, backward compatibility is a goal but not a guarantee.
- Starting at `v1.0.0`, breaking API or deployment changes require a major version bump.
- New backwards-compatible features require a minor version bump.
- Backwards-compatible fixes, documentation updates, and low-risk operational improvements require a patch version bump.

## What requires a breaking-version decision

Treat these as potentially breaking and call them out in release notes:

- API request or response schema changes
- migration changes that require operator action
- renamed environment variables or Compose/Helm values
- dashboard routes or integration workflows that invalidate existing runbooks
- changed event formats for Kafka/webhook/MCP/OTLP consumers

## Release hygiene

Every tagged release should have:

- a `CHANGELOG.md` entry
- a completed [release checklist](./release-checklist.md)
- updated docs for any user-visible behavior change
- a pushed git tag that matches the release version
- matching Docker image tags for the released services
