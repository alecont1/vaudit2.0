#!/bin/sh
# Replace PORT in nginx config and start nginx
PORT=${PORT:-80}
sed -i "s/listen 80;/listen $PORT;/" /etc/nginx/conf.d/default.conf
echo "Starting nginx on port $PORT"
nginx -g 'daemon off;'
