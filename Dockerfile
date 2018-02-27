FROM ubuntu:16.04

MAINTAINER Name <brice.aminou@gmail.com>

RUN apt-get update && apt-get install -y git && apt-get install -y wget
#RUN apt-get install -y python3-pip
#RUN pip3 install overture_song

RUN apt-get update && apt-get install -y software-properties-common && apt-get install -y python-software-properties
RUN \
  echo oracle-java8-installer shared/accepted-oracle-license-v1-1 select true | debconf-set-selections && \
  add-apt-repository -y ppa:webupd8team/java && \
  apt-get update && \
  apt-get install -y oracle-java8-installer && \
  rm -rf /var/lib/apt/lists/* && \
  rm -rf /var/cache/oracle-jdk8-installer
# Define commonly used JAVA_HOME variable
ENV JAVA_HOME /usr/lib/jvm/java-8-oracle

RUN add-apt-repository ppa:jonathonf/python-3.6
RUN apt-get update
RUN apt-get install -y python3.6
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.5 1
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.6 2
RUN update-alternatives --config python3

RUN apt-get install -y python3-pip
RUN pip3 install dataclasses==0.3
RUN pip3 install overture_song

RUN mkdir /icgc-storage-client
RUN wget -O icgc-storage-client.tar.gz https://dcc.icgc.org/api/v1/ui/software/icgc-storage-client/latest
RUN tar -zxvf icgc-storage-client.tar.gz -C /icgc-storage-client --strip-components=1

#RUN touch /icgc-storage-client/conf/application-aws.properties
RUN echo "accessToken=\$ACCESSTOKEN" > /icgc-storage-client/conf/application-aws.properties
RUN echo "storage.url=\$STORAGEURL" >> /icgc-storage-client/conf/application-aws.properties
RUN echo "metadata.url=\$METADATAURL" >> /icgc-storage-client/conf/application-aws.properties
RUN echo "logging.file=./storage-client.log" >> /icgc-storage-client/conf/application-aws.properties

RUN mkdir /scripts
RUN wget https://raw.githubusercontent.com/baminou/dckr_song_upload/master/tools/upload_with_song.py -O /scripts/upload

RUN chmod +x /scripts/upload

ENV PATH="/scripts/:${PATH}"
ENV PATH="/icgc-storage-client/bin:${PATH}"
