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
          model: deepseek-r1:70b
          domain: inference.delta.tinfoil.sh
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

## Run Locally

```bash
docker run --rm \
    -v $(pwd)/output:/output \
    -e INFERENCE_IMAGE_VERSION=0.0.6 \
    -e OVMF_VERSION=0.0.2 \
    -e CPUS=16 \
    -e DOMAIN=six.delta.tinfoil.sh \
    -e MODEL=deepseek-r1:70b \
    ghcr.io/tinfoilanalytics/pri-build-action
```
