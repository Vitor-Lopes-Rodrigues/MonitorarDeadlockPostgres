FROM python:3.9-slim-buster

COPY . /app

WORKDIR /app

RUN pip install --no-cache-dir -r /app/requirements.txt

RUN mkdir /var/log/PythonLogs

ENV LOGS_PATH=/var/log/PythonLogs

CMD ["python", "DeadlockMonitoring.py"]
