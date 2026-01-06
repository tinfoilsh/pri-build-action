FROM ubuntu@sha256:c35e29c9450151419d9448b0fd75374fec4fff364a27f176fb458d472dfc9e54

WORKDIR /app
COPY *.py /
RUN mkdir -p /output /cache

RUN apt update && apt install -y curl python3 python3-venv

# Install GitHub CLI for attestation verification
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg && \
    chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null && \
    apt update && apt install -y gh

# Download and verify tdx-measure binary
RUN curl -L https://github.com/tinfoilsh/tdx-measure/releases/download/v0.0.6/tdx-measure -o tdx-measure && \
    echo "d1bde7b36bdc6437140478428127809f16ac8f024cd08007a05ccdaa4044309e  tdx-measure" | sha256sum -c - && \
    chmod +x tdx-measure

RUN python3 -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir \
        sev-snp-measure==0.0.12 \
        pyyaml==6.0.3 \
        requests==2.32.5

ENTRYPOINT ["/opt/venv/bin/python", "/measure.py"]
