FROM python:3.10-slim-bullseye

RUN useradd --create-home --shell /bin/bash intelgram
USER intelgram
ENV PATH="/home/intelgram/.local/bin:$PATH"

WORKDIR /app
COPY . .
RUN pip install --disable-pip-version-check --no-cache-dir -r docker-requirements.txt

ENTRYPOINT ["python", "main.py"]
