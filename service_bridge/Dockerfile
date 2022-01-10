FROM apache_base

# Copy over the apache configuration file and enable the site
COPY ./service_bridge.conf /etc/apache2/sites-available/service_bridge.conf
COPY ./httpd.conf /etc/apache2/httpd.conf
RUN echo "Include /etc/apache2/httpd.conf" >> /etc/apache2/apache2.conf
COPY ./mpm_event.conf /etc/apache2/mods-available/mpm_event.conf
COPY ./ports.conf /etc/apache2/ports.conf
# COPY ./ports.conf /etc/apache2/ports.conf
RUN a2ensite service_bridge
RUN a2enmod headers

# Copy over the wsgi file
COPY ./service_bridge.wsgi /var/www/service_bridge/service_bridge.wsgi

RUN chmod a+x /var/www/service_bridge/service_bridge.wsgi


COPY ./run.py /var/www/service_bridge/run.py
COPY ./app /var/www/service_bridge/app/

RUN a2dissite 000-default.conf
RUN a2ensite service_bridge.conf

EXPOSE 8080

WORKDIR /var/www/service_bridge

RUN ln -sf /dev/stdout /var/log/apache2/access.log

CMD  /usr/sbin/apache2ctl -D FOREGROUND
