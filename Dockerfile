FROM python:3.10-alpine

RUN apk add --no-cache nginx curl bash gettext

RUN pip install --no-cache-dir flask

COPY . /app
WORKDIR /app

RUN chmod +x start.sh

CMD ["/app/start.sh"]
