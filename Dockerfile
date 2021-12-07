FROM docker.elastic.co/logstash/logstash:7.15.2

# Set root user, to prevent any permission denied error.
USER root

WORKDIR /root

# Install python3
RUN yum -y install python3

# Install crontabs
RUN yum -y install crontabs

COPY . .

# Dependencies
RUN python3 -m pip install -r requirements.txt

# comment out PAM
RUN sed -i -e '/pam_loginuid.so/s/^/#/' /etc/pam.d/crond

#Add your cron file
ADD crontab /etc/cron.d/backup
RUN chmod 0644 /etc/cron.d/backup

#This will add it to the cron table (crontab -e)
RUN crontab /etc/cron.d/backup

# Logstash config
RUN rm -f /usr/share/logstash/pipeline/logstash.conf

RUN rm -f /usr/share/logstash/config/logstash.yml

ADD logstash/ /usr/share/logstash/pipeline/

ENTRYPOINT logstash & \
    crond && tail -f /dev/null
