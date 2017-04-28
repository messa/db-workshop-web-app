FROM debian:jessie

MAINTAINER Petr Messner

ENV DEBIAN_FRONTEND noninteractive
ENV PYTHONUNBUFFERED 1

RUN apt-get update
RUN apt-get install -y --no-install-recommends python3-venv gcc

RUN python3 -m venv /venv
RUN /venv/bin/pip install -U pip
RUN /venv/bin/pip install gunicorn

COPY requirements.txt /app/requirements.txt
RUN /venv/bin/pip install -r /app/requirements.txt

COPY . /app
WORKDIR /app

RUN useradd --no-create-home www
USER www

ENV ANKETA_CONF /conf/anketa.yaml

CMD [ \
    "/venv/bin/gunicorn", \
    "--workers", "2", \
    "--bind", "0.0.0.0:8000", \
    "--preload", \
    "--max-requests", "100", \
    "anketa:app" \
]
