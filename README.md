# Tinfoil Private Inference Builder

## GitHub Actions Example

```yaml
name: Build and Attest

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      packages: write
      id-token: write
      attestations: write

    steps:
      - uses: actions/checkout@8e8c483db84b4bee98b60c0593521ed34d9990e8  # v6.0.1
      - uses: tinfoilsh/measure-image-action@<COMMIT_SHA>  # pin to latest release tag commit
        with:
          config-file: ${{ github.workspace }}/tinfoil-config.yml
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

## Releasing a New Version

Push a `build-v*` tag to trigger the automated pipeline:

```bash
git tag build-v0.0.13
git push origin build-v0.0.13
```

This will:
1. Build and push the container image to ghcr.io
2. Update `action.yaml` with the new container digest
3. Commit the digest update to `main`
4. Create a `v0.0.13` release tag on the commit with the correct digest
5. Create a GitHub Release

Downstream users can then pin to the new version:
```yaml
- uses: tinfoilsh/measure-image-action@v0.0.13
```
