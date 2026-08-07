# Release Checklist

Use this checklist for every tagged RunLedger Community release.

The current alpha baseline is `v1alpha1` on Friday, August 7, 2026.

## 1. Source control

- Confirm the working tree is clean.
- Confirm the intended branch is pushed.
- Confirm the release version matches the [versioning policy](./versioning-policy.md).
- Create or verify the annotated git tag for the release.

## 2. Validation

- Run backend tests that cover the changed areas.
- Run frontend typecheck and any relevant UI validation.
- Run targeted script validation for changed simulator or operational flows.
- Verify migrations compile and are ready to apply.

## 3. Documentation

- Update `README.md` for any high-level feature or deployment changes.
- Update the relevant docs pages for operator or user-visible behavior.
- Add or update the `CHANGELOG.md` entry for the release.
- Confirm demo docs still match the seeded product story if demo behavior changed.

## 4. Artifacts

- Build Docker images with the release tag.
- Push Docker images with the release tag.
- Do not deploy automatically unless the release step explicitly includes deployment.

## 5. Release notes

- Summarize the most important added and changed behavior.
- Call out known limitations or manual follow-up where relevant.
- Note any migration or environment changes operators must make.

## 6. Post-release verification

- Confirm the git tag exists on the remote.
- Confirm the pushed image tags exist in the registry.
- Confirm the working tree remains clean after the release process.

## Recommended command set

These are common examples, not a substitute for judgment:

```bash
git status --short
git tag -a v1alpha1 -m "Release v1alpha1"
git push origin main --tags
make build-push TAG=v1alpha1
```

On this repository, avoid `deploy` unless you explicitly intend to recreate running containers.
