# docker build -t frontend:1 -f frontend/Dockerfile .
FROM python:3.8

LABEL MAINTAINER Robert Lynch "rob@rlyn.ch"

ADD requirements.txt /requirements.txt
RUN pip install -r /requirements.txt
COPY . / 
WORKDIR /app/
CMD python3 -u app.py
