FROM python:3.12-slim

WORKDIR /app

RUN python -m venv /opt/venv

RUN pip install --no-cache-dir sev-snp-measure

COPY main.py /app.py

RUN mkdir -p /output

ENTRYPOINT ["python", "/app.py"]
