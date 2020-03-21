FROM python:3.7
MAINTAINER Alex Lubbock <code@alexlubbock.com>
ENV PYTHONUNBUFFERED 1
ENV MUSYC_HOME=/musyc

RUN mkdir $MUSYC_HOME
WORKDIR $MUSYC_HOME

CMD ["uwsgi", "--master", "--socket", ":8000", "--module", "musycdjango.wsgi", "--uid", "www-data", "--gid", "www-data", "--enable-threads"]
ADD requirements.txt $MUSYC_HOME
RUN pip install -r requirements.txt
ADD manage.py $MUSYC_HOME
ADD musycdjango $MUSYC_HOME/musycdjango
ADD static $MUSYC_HOME/static
ADD musyc_code $MUSYC_HOME/musyc_code
ADD musycweb $MUSYC_HOME/musycweb
