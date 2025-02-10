FROM python:3.12-slim

WORKDIR /app

RUN python -m venv /opt/venv

RUN pip install --no-cache-dir sev-snp-measure pyyaml

COPY *.py /

RUN mkdir -p /output

ENTRYPOINT ["python", "/measure.py"]
