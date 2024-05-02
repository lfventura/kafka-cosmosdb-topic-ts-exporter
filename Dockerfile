FROM python:3.12-slim
LABEL org.opencontainers.image.source "https://github.com/lfventura/kafka-cosmosdb-topic-ts-exporter"
ENV TZ="GMT"
WORKDIR /app
COPY exporter .
RUN pip install --no-cache-dir -r requirements.txt && chmod u+x cosmos_connector_lag_monitor.py
