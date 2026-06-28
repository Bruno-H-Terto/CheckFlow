FROM python:3.14-slim AS build

ENV PIP_NO_CACHE_DIR=1

WORKDIR /build

RUN python -m venv /opt/venv

COPY requirements.txt ./
RUN /opt/venv/bin/python -m pip install --upgrade pip \
    && /opt/venv/bin/python -m pip install -r requirements.txt

FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN addgroup --system checkflow \
    && adduser --system --ingroup checkflow checkflow

COPY --from=build /opt/venv /opt/venv
COPY --chown=checkflow:checkflow . .

USER checkflow

EXPOSE 8000 8001

CMD ["honcho", "start"]
