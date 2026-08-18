#!/bin/bash

export PORT=${PORT:-8080}

# برای Alpine، مسیر Nginx کمی متفاوت است
envsubst '${PORT}' < /app/nginx.conf.template > /etc/nginx/http.d/default.conf

python3 /app/app.py &

nginx -g "daemon off;"
