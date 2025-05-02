FROM python:3.13-slim

ARG USERNAME=appuser
ARG UID=1000
ARG GID=1000

RUN addgroup --gid ${GID} ${USERNAME} \
    && adduser --disabled-password --gecos "" --uid ${UID} --gid ${GID} ${USERNAME}

WORKDIR /app

COPY requirements.txt .
COPY main.py .

RUN pip install --no-cache-dir -r requirements.txt

RUN chown -R ${UID}:${GID} /app
USER ${USERNAME}

CMD ["python", "main.py"]