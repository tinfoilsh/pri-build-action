FROM ubuntu:24.04

WORKDIR /app
COPY *.py /
RUN mkdir -p /output

RUN apt update && apt install -y curl python3 python3-venv
RUN curl -L https://github.com/tinfoilsh/tdx-measure/releases/download/v0.0.5/tdx-measure -o tdx-measure
RUN chmod +x tdx-measure

RUN python3 -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir sev-snp-measure pyyaml requests

ENTRYPOINT ["/opt/venv/bin/python", "/measure.py"]
