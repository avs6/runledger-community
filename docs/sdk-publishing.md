# Publishing the SDKs

The Python SDK (`runledger-sdk` on PyPI) and the TypeScript SDK (`@runledger/sdk` on npm) are
released by `.github/workflows/publish-sdks.yml`. Until the first release, install from the
repository (see each package's README).

## What the workflow does

| Trigger | Python SDK | TypeScript SDK |
|---|---|---|
| Pull request touching `packages/` | lint, mypy, tests, build sdist + wheel, `twine check`, install the wheel | typecheck, tests, build, `npm pack --dry-run` |
| Tag `sdk-py-v<version>` | all of the above, then publish to PyPI | — |
| Tag `sdk-ts-v<version>` | — | all of the above, then `npm publish --provenance` |
| Run workflow (manual) | choose the SDK; `dry_run` (default) builds without publishing | same |

Before publishing, the job checks that the tag version equals `packages/sdk/pyproject.toml` /
`packages/ts-sdk/package.json` and that the package's `CHANGELOG.md` has a `## [<version>]` section.

## One-time setup (repository owner)

1. **PyPI.** Create an account, then add a *pending trusted publisher* for the project
   `runledger-sdk`: owner `avs6`, repository `runledger-community`, workflow `publish-sdks.yml`,
   environment `pypi`. No API token is stored in GitHub.
2. **npm.** Create an account and the `@runledger` organization (scoped packages publish as public
   via `publishConfig`). Create an *automation* access token.
3. **GitHub.** Create two environments under Settings → Environments: `pypi` and `npm`. Add the npm
   token to the `npm` environment as `NPM_TOKEN`. Add required reviewers if you want an approval step
   before each publish.
4. **Licence.** The repository is Apache-2.0 and the Python SDK declares Apache-2.0 (with a copy of
   `LICENSE`). `packages/ts-sdk/package.json` declares MIT: confirm which licence the TypeScript SDK
   ships under before its first publish, and add the matching `LICENSE` file to `packages/ts-sdk/`.

## Releasing

```bash
# Python: bump packages/sdk/pyproject.toml and add the CHANGELOG section, commit, then
git tag sdk-py-v0.7.0 && git push origin sdk-py-v0.7.0

# TypeScript: bump packages/ts-sdk/package.json and add the CHANGELOG section, commit, then
git tag sdk-ts-v0.6.0 && git push origin sdk-ts-v0.6.0
```

The first publish of each package is run by the owner (the workflow needs the accounts above).
After it, update the install instructions in the SDK READMEs and docs from "install from the
repository" to `pip install runledger-sdk` / `npm install @runledger/sdk`.
