FROM ubuntu:24.04

WORKDIR /app
COPY *.py /
RUN mkdir -p /output /cache

RUN apt update && apt install -y curl python3 python3-venv

# Install GitHub CLI for attestation verification
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg && \
    chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null && \
    apt update && apt install -y gh

RUN curl -L https://github.com/tinfoilsh/tdx-measure/releases/download/v0.0.6/tdx-measure -o tdx-measure
RUN chmod +x tdx-measure

RUN python3 -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir sev-snp-measure pyyaml requests

ENTRYPOINT ["/opt/venv/bin/python", "/measure.py"]
