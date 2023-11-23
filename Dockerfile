FROM python:3

# Change l'appel de sh vers bash - Pas mal d'erreurs sont provoquées par sh
SHELL ["/bin/bash", "-c"] 

# Install git
RUN apt-get -y update
RUN apt-get -y install git

# Installation des packages python
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Copy du code et des données
COPY data data
COPY code code 
COPY results results
COPY main.py main.py

RUN python main.py -s -k