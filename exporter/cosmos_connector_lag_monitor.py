#!/usr/bin/env python
import argparse
import json
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from confluent_kafka import Consumer, KafkaException, KafkaError, TopicPartition
from prometheus_client import start_http_server, generate_latest, Gauge, Counter

def error_cb(err):
    """ The error callback is used for generic client errors. These
        errors are generally to be considered informational as the client will
        automatically try to recover from all errors, and no extra action
        is typically required by the application.
        For this example however, we terminate the application if the client
        is unable to connect to any broker (_ALL_BROKERS_DOWN) and on
        authentication errors (_AUTHENTICATION). """

    print("Client error: {}".format(err))
    if err.code() == KafkaError._ALL_BROKERS_DOWN or \
       err.code() == KafkaError._AUTHENTICATION:
        # Any exception raised from this callback will be re-raised from the
        # triggering flush() or poll() call.
        raise KafkaException(err)
    
def create_consumer(args):
    conf = {
        'bootstrap.servers': f"{args.hostname}:{args.port}",
        'group.id': 'monitoring_cosmos',
        'security.protocol': 'SASL_SSL',
        'sasl.mechanisms': 'PLAIN',
        'sasl.username': args.username,
        'sasl.password': args.password,
        'auto.offset.reset': 'latest',
        'enable.auto.commit': 'false',
        'error_cb': error_cb,
    }

    consumer = Consumer(conf)
    return consumer

def get_latest_message(consumer, topic, timeframe):
    consumer.subscribe([topic])

    message_count = 0
    start_time = time.time()

    while True:
        message = consumer.poll(1.0)

        if message is None:
            continue
        if message.error():
            if message.error().code() == KafkaError._PARTITION_EOF:
                continue
            else:
                raise KafkaException(message.error())
            
        message_count += 1

        if time.time() - start_time > timeframe:
            messages_per_second = message_count / timeframe
            break

    timestamp = message.timestamp()
    message_value = json.loads(message.value().decode('utf-8'))
    message_cosmos_ts = message_value.get('_ts')
    # Calcula a diferença de tempo em minutos
    current_time = int(time.time())  # Tempo atual em segundos
    message_kafka_ts = timestamp[1] / 1000  # Tempo da mensagem Kafka em segundos
    time_difference_kafka = (current_time - message_kafka_ts) / 60  # Diferença de tempo em minutos
    time_difference_cosmos = (current_time - message_cosmos_ts) / 60  # Diferença de tempo em minutos

    if args.debug:
        print(f"------- Start proccessing topic: " + topic)
        print(f'Received {message_count} messages in the last {timeframe} seconds ({messages_per_second} messages/second)')
        print(f"Timestamp Kafka: {message.timestamp()}")
        print(f"Timestamp Cosmos: {message_cosmos_ts}")
        print(f"Current Timestamp:{current_time}")
        print(f"Message received at {timestamp[1]} which is {time_difference_kafka} minutes ago")
        print(f"Message received at  {message_cosmos_ts} which is {time_difference_cosmos} minutes ago")
        print(f"------- End proccessing topic: " + topic)

    consumer.close()

    return {
        'timestamp': timestamp,
        'message_time_kafka': message_kafka_ts,
        'message_time_cosmos': message_cosmos_ts,
        'time_difference_cosmos': time_difference_cosmos,
        'time_difference_kafka': time_difference_kafka,
        'messages_per_second': messages_per_second,
    }

def split_topics(s):
    return s.split(',') if ',' in s else s.split()

def process_topic(topic):
    consumer = create_consumer(args)
    result = get_latest_message(consumer, topic, args.timeframe)
    
    prom['cosmos_connector_age_cosmos_record'].labels(
        connector_topic=topic,
    ).set(result['time_difference_cosmos'])

    prom['cosmos_connector_age_kafka_record'].labels(
        connector_topic=topic,
    ).set(result['time_difference_kafka'])

    prom['cosmos_connector_message_rate'].labels(
        connector_topic=topic,
    ).set(result['messages_per_second'])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Connect to Kafka topics written by CosmosDB and have how old the records are, along with message rate.')
    parser.add_argument('--hostname', required=True, help='The hostname of the Kafka server.')
    parser.add_argument('--port', required=True, help='The port of the Kafka server.')
    parser.add_argument('--username', required=True, help='The username for SASL/PLAIN authentication.')
    parser.add_argument('--password', required=True, help='The password for SASL/PLAIN authentication.')
    parser.add_argument('--timeframe', required=True, type=int, help='The timeframe to get the messages from.')
    parser.add_argument('--port_prometheus', required=True, type=int, help='The port to expose the Prometheus metrics.')
    parser.add_argument('--interval', required=True, type=int, help='The interval to update metrics')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode.')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--topics', type=split_topics, help='The names of the topics to get the latest message from. (Comma separated, Cant be used multiple times)')
    group.add_argument('--topic', action='append', help='The name of the topic to get the latest message from. (Can be used multiple times)')
    args = parser.parse_args()

    if args.topic is not None:
        # User --topic
        topics = args.topic
    elif args.topic is not None:
        # User --topics
        topics = args.topics

    prom = {
        'cosmos_connector_age_cosmos_record': Gauge('cosmos_connector_age_cosmos_record', 'Age of the latest event, based on Cosmos timestamp (in minutes), AKA how old is the record gotten from cosmos',
            ['connector_topic']),
        'cosmos_connector_age_kafka_record': Gauge('cosmos_connector_age_kafka_record', 'Age of the latest event based on Kafka timestamp (in minutes), AKA how many time since kafka got a new message',
            ['connector_topic']),
        'cosmos_connector_message_rate': Gauge('cosmos_connector_message_rate', 'Amount of messages per second in Topic',
            ['connector_topic']),
    }

    start_http_server(args.port_prometheus)
    print("[ " + str(datetime.now()) + " ] Starting HTTP Server in :" + str(args.port_prometheus))

    try:
        while True:
            with ThreadPoolExecutor() as executor:
                for topic in topics:
                    executor.submit(process_topic, topic)
                
                executor.shutdown(wait=True)
                print("[ " + str(datetime.now()) + " ] Finish Loop! Starting next loop in: " + str(args.interval))
                time.sleep(args.interval)

    except Exception as e:
        print(f"An error occurred: {e}")
        exit(1)