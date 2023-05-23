FROM arm32v7/python:3.8

WORKDIR /app

COPY requirements.txt /tmp/

RUN apt-get update 

COPY ./src .
COPY docker-entrypoint.sh . 

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["python3"]
