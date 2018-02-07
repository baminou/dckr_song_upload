FROM ubuntu:16.04

MAINTAINER Name <brice.aminou@gmail.com>

RUN apt-get update && apt-get install -y git && apt-get install -y wget
RUN apt-get install -y python3-pip

RUN pip3 install overture_song

RUN mkdir /scripts
RUN wget https://raw.githubusercontent.com/baminou/dckr_song_upload/master/tools/upload_with_song.py -O /scripts/upload

RUN chmod +x /scripts/upload
ENV PATH="/scripts/:${PATH}"
