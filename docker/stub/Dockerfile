FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py telemetry.py healthcheck.py ./
CMD ["python", "server.py"]
