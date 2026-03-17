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
      - uses: tinfoilsh/measure-image-action@a2029deb5bc01e5ad2c66f7782eab407b7636e00  # v0.6.4
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