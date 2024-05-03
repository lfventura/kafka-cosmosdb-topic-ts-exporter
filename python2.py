import argparse
import json
import time
from threading import Thread
from confluent_kafka import Consumer, KafkaException, KafkaError, TopicPartition
from prometheus_client import start_http_server, generate_latest, Gauge, Counter

message_count_metric = Counter('message_count', 'The total number of messages received')
time_difference_kafka_metric = Gauge('time_difference_kafka', 'The time difference in minutes for Kafka messages')
time_difference_cosmos_metric = Gauge('time_difference_cosmos', 'The time difference in minutes for Cosmos messages')

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

    try:
        consumer = Consumer(conf)
        consumer.list_topics(timeout=10)  # Tenta listar os tópicos para verificar a conexão
    except Exception as e:
        print(f"Failed to connect: {e}")
        raise

    return consumer

def get_latest_message(consumer, topic, timeframe):
    consumer.subscribe([topic])
    # patition = TopicPartition(topic, 0)
    # consumer.assign([patition])

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
            print(f'Received {message_count} messages in the last {timeframe} seconds ({messages_per_second} messages/second)')

            break

    timestamp = message.timestamp()
    message_value = json.loads(message.value().decode('utf-8'))
    message_cosmos_ts = message_value.get('_ts')

    print(f"\n\nTimestamp Kafka: {message.timestamp()}")
    print(f"Timestamp Cosmos: {message_cosmos_ts}\n\n")

    # Calcula a diferença de tempo em minutos
    current_time = int(time.time())  # Tempo atual em segundos
    message_time_kafka = timestamp[1] / 1000  # Tempo da mensagem Kafka em segundos
    time_difference_kafka = (current_time - message_time_kafka) / 60  # Diferença de tempo em minutos

    message_time_cosmos = message_cosmos_ts  # Tempo da mensagem Cosmos já está em segundos
    time_difference_cosmos = (current_time - message_time_cosmos) / 60  # Diferença de tempo em minutos

    print(f"Current Timestamp:{current_time}")

    print(f"Message received at {timestamp[1]} which is {time_difference_kafka} minutes ago")
    print(f"Message received at  {message_cosmos_ts} which is {time_difference_cosmos} minutes ago")

    consumer.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Connect to Kafka and get the latest message from a topic.')
    parser.add_argument('--hostname', required=True, help='The hostname of the Kafka server.')
    parser.add_argument('--port', required=True, help='The port of the Kafka server.')
    parser.add_argument('--username', required=True, help='The username for SASL/PLAIN authentication.')
    parser.add_argument('--password', required=True, help='The password for SASL/PLAIN authentication.')
    parser.add_argument('--topic', required=True, help='The name of the topic to get the latest message from.')
    parser.add_argument('--timeframe', required=True, type=int, help='The timeframe to get the messages from.')

    args = parser.parse_args()

    try:
        consumer = create_consumer(args)
        get_latest_message(consumer, args.topic, args.timeframe)
    except Exception as e:
        print(f"An error occurred: {e}")
        exit(1)

    # Inicia o servidor HTTP para o Prometheus coletar as métricas
    start_http_server(8000)