# Cosmos Topic Exporter for Prometheus

Prometheus exporter for `Kafka Topics` topics that are written by CosmosDB connectors.

## Metrics supported

- `cosmos_connector_age_cosmos_record` Age of the latest event, based on Cosmos timestamp (in minutes), AKA how old is the record gotten from cosmos
- `cosmos_connector_age_kafka_record` Age of the latest event based on Kafka timestamp (in minutes), AKA how many time since kafka got a new message
- `cosmos_connector_message_rate` How many messages/sec where gotten in the --timeframe flag

## Configuration

```sh
usage: cosmos_connector_lag_monitor.py [-h] --hostname HOSTNAME --port PORT --username USERNAME --password PASSWORD --timeframe TIMEFRAME --port_prometheus PORT_PROMETHEUS --interval INTERVAL [--debug] (--topics TOPICS | --topic TOPIC)

options:
  -h, --help            show this help message and exit
  --hostname HOSTNAME   The hostname of the Kafka server.
  --port PORT           The port of the Kafka server.
  --username USERNAME   The username for SASL/PLAIN authentication.
  --password PASSWORD   The password for SASL/PLAIN authentication.
  --timeframe TIMEFRAME
                        The timeframe to get the messages from.
  --port_prometheus PORT_PROMETHEUS
                        The port to expose the Prometheus metrics.
  --interval INTERVAL   The interval to update metrics
  --debug               Enable debug mode.
  --topics TOPICS       The names of the topics to get the latest message from. (Comma separated, Cant be used multiple times)
  --topic TOPIC         The name of the topic to get the latest message from. (Can be used multiple times)
```

## Usage

### Option A) Python3 + PIP

```sh
pip install -r /exporter/requirements.txt
/exporter/cosmos_connector_lag_monitor.py --hostname HOSTNAME --port PORT --username USERNAME --password PASSWORD --topics TOPICS --timeframe 60 --port_prometheus PORT_PROMETHEUS --interval 300
```

### Option B) Docker

```sh
docker run --rm -it -p 8956:8956 ghcr.io/lfventura/kafka-cosmosdb-topic-ts-exporter:latest /app/cosmos_connector_lag_monitor.py --hostname HOSTNAME --port PORT --username USERNAME --password PASSWORD --topics TOPICS --timeframe 60 --port_prometheus PORT_PROMETHEUS --interval 300
```

## Metrics

```sh
# HELP cosmos_connector_age_cosmos_record Age of the latest event, based on Cosmos timestamp (in minutes), AKA how old is the record gotten from cosmos
# TYPE cosmos_connector_age_cosmos_record gauge
cosmos_connector_age_cosmos_record{connector_topic="<topic_name>"} xx.xx
...
# HELP cosmos_connector_age_kafka_record Age of the latest event based on Kafka timestamp (in minutes), AKA how many time since kafka got a new message
# TYPE cosmos_connector_age_kafka_record gauge
cosmos_connector_age_kafka_record{connector_topic="<topic_name>"} xx.xx
...
# HELP cosmos_connector_message_rate Amount of messages per second in Topic
# TYPE cosmos_connector_message_rate gauge
cosmos_connector_message_rate{connector_topic="<topic_name>"} xx.xx
..
```

## Contribute

Feel free to open an issue or PR if you have suggestions or ideas about what to add.
