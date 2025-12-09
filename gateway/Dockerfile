FROM nginx:latest

USER root

RUN apt-get update && apt-get install -y gettext-base && apt-get clean

COPY my_entrypoint.sh /usr/local/bin/my_entrypoint.sh
COPY nginx.conf.template /usr/local/bin/nginx.conf.template
COPY ssl.conf.template /usr/local/bin/ssl.conf.template
COPY locations.conf /etc/nginx/locations.conf
COPY favicon.ico /etc/nginx/html/favicon.ico

ENTRYPOINT ["/usr/local/bin/my_entrypoint.sh"]

CMD ["nginx", "-g", "daemon off;"]