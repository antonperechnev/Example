FROM python:3.8-slim

WORKDIR /var/www/services/Work

COPY Project/requirements.txt ./

RUN apt-get update
RUN apt-get install -y gcc
RUN apt-get install -y python3.8-dev
RUN pip3 install -r requirements.txt