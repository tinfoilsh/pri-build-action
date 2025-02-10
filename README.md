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
      - uses: actions/checkout@v4
      - uses: tinfoilanalytics/pri-build-action@main
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
```
