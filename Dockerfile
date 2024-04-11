FROM python:3.8-slim

# maintainer label added
MAINTAINER Md Salman (Whatsapp : +880 1521109830)

# changed to pythonunbuffered
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y build-essential && apt-get install -y poppler-utils 

RUN mkdir /app
WORKDIR /app
COPY requirements.txt /app/
RUN pip install --upgrade pip setuptools wheel && pip install -r requirements.txt
COPY . /app/