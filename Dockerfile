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

ENV ANKETA_CONF /app/conf/anketa.sample.yaml

EXPOSE 80

CMD [ \
    "/venv/bin/gunicorn", \
    "--workers", "2", \
    "--bind", "0.0.0.0:80", \
    "--preload", \
    "--max-requests", "100", \
    "--access-logfile", "-", \
    "--error-logfile", "-", \
    "anketa:app" \
]
