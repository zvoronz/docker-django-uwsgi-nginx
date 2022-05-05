FROM debian:stretch
MAINTAINER Georgiy Voronov <voron.zvs@gmail.com>

RUN (apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y apt-utils curl aptitude python-mysqldb build-essential git python python-dev python-setuptools nginx sqlite3 supervisor python-pip)
RUN pip install --upgrade pip
RUN pip install uwsgi

ADD src/requirements.txt /opt/django/app/requirements.txt
RUN pip install -r /opt/django/app/requirements.txt
ADD docker /opt/django/
COPY src /opt/django/app

RUN (echo "daemon off;" >> /etc/nginx/nginx.conf &&\
  rm /etc/nginx/sites-enabled/default &&\
  ln -s /opt/django/django.conf /etc/nginx/sites-enabled/ &&\
  ln -s /opt/django/supervisord.conf /etc/supervisor/conf.d/)

EXPOSE 80
CMD ["/opt/django/run.sh"]
