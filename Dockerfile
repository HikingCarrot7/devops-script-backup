FROM docker.elastic.co/logstash/logstash:7.15.2

# Set root user, to prevent any permission denied error.
USER root

WORKDIR /app

# Python install
RUN yum install -y python3

COPY . .

# Dependencies
RUN python3 -m pip install -r requirements.txt

# Logstash config
RUN rm -f /usr/share/logstash/pipeline/logstash.conf

RUN rm -f /usr/share/logstash/config/logstash.yml

ADD logstash/ /usr/share/logstash/pipeline/

ENTRYPOINT logstash & \
    python3 main.py
