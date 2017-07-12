from googlefinance import getQuotes
from kafka import KafkaProducer
from kafka.errors import KafkaError, KafkaTimeoutError
from py_zipkin.zipkin import zipkin_span
from py_zipkin.thread_local import get_zipkin_attrs
from py_zipkin.util import generate_random_64bit_string

import argparse
import atexit
import datetime
import logging
import json
import random
import schedule
import time
import requests

# - default kafka topic to write to
topic_name = 'stock-analyzer'

# - default kafka broker location
kafka_broker = '127.0.0.1:9092'

# instrumentation
logger_format = '%(asctime)-15s %(message)s'
logging.basicConfig(format=logger_format)
logger = logging.getLogger('data-producer')
logger.setLevel(logging.DEBUG)

def http_transport_handler(span):
    body = '\x0c\x00\x00\x00\x01' + span
    requests.post(
        'http://localhost:9411/api/v1/spans',
        data=body,
        headers={'Content-Type': 'application/x-thrift'},
    )

@zipkin_span(service_name='demo', span_name='fetch_price')
def fetch_price(symbol):
    return json.dumps(getQuotes(symbol))

def enrich_with_zipkin_data(data):
    zipkin_attr = get_zipkin_attrs()
    data[0]['trace_id'] = zipkin_attr.trace_id
    data[0]['parent_span_id'] = zipkin_attr.span_id
    data[0]['span_id'] = generate_random_64bit_string()
    data[0]['is_sampled'] = True if zipkin_attr.is_sampled else False
    return data

@zipkin_span(service_name='demo', span_name='send_to_kafka')
def send_to_kafka(producer, price):
    try:
        logger.debug('Retrieved stock info %s', price)
        price = json.dumps(enrich_with_zipkin_data(json.loads(price)))
        logger.debug(price)
        producer.send(topic=topic_name, value=price, timestamp_ms=time.time())
        logger.debug('Sent stock price for %s to Kafka', symbol)
    except KafkaTimeoutError as timeout_error:
        logger.warn('Failed to send stock price for %s to kafka, caused by: %s', (symbol, timeout_error.message))
    except Exception:
        logger.warn('Failed to fetch stock price for %s', symbol)


def fetch_price_and_send(producer, symbol):
    """
    helper function to retrieve stock data and send it to kafka
    :param producer: instance of a kafka producer
    :param symbol: symbol of the stock
    :return: None
    """
    with zipkin_span(service_name='demo', span_name='data_producer', transport_handler=http_transport_handler, sample_rate=100.0):
        logger.debug('Start to fetch stock price for %s', symbol)
        price = fetch_price(symbol)
        send_to_kafka(producer, price)


def shutdown_hook(producer):
    """
    a shutdown hook to be called before the shutdown
    :param producer: instance of a kafka producer
    :return: None
    """
    try:
        logger.info('Flushing pending messages to kafka, timeout is set to 10s')
        producer.flush(10)
        logger.info('Finish flushing pending messages to kafka')
    except KafkaError as kafka_error:
        logger.warn('Failed to flush pending messages to kafka, caused by: %s', kafka_error.message)
    finally:
        try:
            logger.info('Closing kafka connection')
            producer.close(10)
        except Exception as e:
            logger.warn('Failed to close kafka connection, caused by: %s', e.message)


if __name__ == '__main__':
    # - setup command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('symbol', help='the symbol of the stock to collect')
    parser.add_argument('topic_name', help='the kafka topic push to')
    parser.add_argument('kafka_broker', help='the location of the kafka broker')

    # - parse arguments
    args = parser.parse_args()
    symbol = args.symbol
    topic_name = args.topic_name
    kafka_broker = args.kafka_broker

    # - instantiate a simple kafka producer
    producer = KafkaProducer(
        bootstrap_servers=kafka_broker
    )

    # - schedule and run the fetch_price function every second
    schedule.every(1).second.do(fetch_price_and_send, producer, symbol)

    # - setup proper shutdown hook
    atexit.register(shutdown_hook, producer)

    while True:
        schedule.run_pending()
        time.sleep(1)
