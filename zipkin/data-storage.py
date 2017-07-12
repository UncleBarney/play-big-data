from cassandra.cluster import Cluster
from kafka import KafkaConsumer
from kafka.errors import KafkaError
from py_zipkin.zipkin import zipkin_span
from py_zipkin.zipkin import ZipkinAttrs

import argparse
import atexit
import json
import logging
import requests

# - default kafka topic to read from
topic_name = 'stock-analyzer'

# - default kafka broker location
kafka_broker = '127.0.0.1:9092'

# - default cassandra nodes to connect
contact_points = '192.168.99.101'

# - default keyspace to use
key_space = 'stock'

# - default table to use
data_table = 'stock'

logger_format = '%(asctime)-15s %(message)s'
logging.basicConfig(format=logger_format)
logger = logging.getLogger('data-storage')
logger.setLevel(logging.DEBUG)

def http_transport_handler(span):
    body = '\x0c\x00\x00\x00\x01' + span
    requests.post(
        'http://localhost:9411/api/v1/spans',
        data=body,
        headers={'Content-Type': 'application/x-thrift'},
    )


def construct_zipkin_attrs(data):
    parsed = json.loads(data)[0]
    return ZipkinAttrs(
        trace_id=parsed.get('trace_id'),
        span_id=parsed.get('span_id'),
        parent_span_id=parsed.get('parent_span_id'),
        is_sampled=parsed.get('is_sampled'),
        flags='0',
    )

def persist_data(stock_data, cassandra_session):
    """
    persist stock data into cassandra
    :param stock_data:
        the stock data looks like this:
        [{
            "Index": "NASDAQ",
            "LastTradeWithCurrency": "109.36",
            "LastTradeDateTime": "2016-08-19T16:00:02Z",
            "LastTradePrice": "109.36",
            "LastTradeTime": "4:00PM EDT",
            "LastTradeDateTimeLong": "Aug 19, 4:00PM EDT",
            "StockSymbol": "AAPL",
            "ID": "22144"
        }]
    :param cassandra_session:

    :return: None
    """
    try:
        logger.debug('Start to persist data to cassandra %s', stock_data)
        zipkin_attrs = construct_zipkin_attrs(stock_data)
        parsed = json.loads(stock_data)[0]
        symbol = parsed.get('StockSymbol')
        price = float(parsed.get('LastTradePrice'))
        tradetime = parsed.get('LastTradeDateTime')
        statement = "INSERT INTO %s (stock_symbol, trade_time, trade_price) VALUES ('%s', '%s', %f)" % (data_table, symbol, tradetime, price)
        with zipkin_span(service_name='demo', span_name='cassandra session', zipkin_attrs=zipkin_attrs, transport_handler=http_transport_handler):
            cassandra_session.execute(statement)
        logger.info('Persistend data to cassandra for symbol: %s, price: %f, tradetime: %s' % (symbol, price, tradetime))
    except Exception as e:
        logger.error('Failed to persist data to cassandra %s, %s', stock_data, e)


def shutdown_hook(consumer, session):
    """
    a shutdown hook to be called before the shutdown
    :param consumer: instance of a kafka consumer
    :param session: instance of a cassandra session
    :return: None
    """
    try:
        logger.info('Closing Kafka Consumer')
        consumer.close()
        logger.info('Kafka Consumer closed')
        logger.info('Closing Cassandra Session')
        session.shutdown()
        logger.info('Cassandra Session closed')
    except KafkaError as kafka_error:
        logger.warn('Failed to close Kafka Consumer, caused by: %s', kafka_error.message)
    finally:
        logger.info('Existing program')


if __name__ == '__main__':
    # - setup command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('topic_name', help='the kafka topic to subscribe from')
    parser.add_argument('kafka_broker', help='the location of the kafka broker')
    parser.add_argument('key_space', help='the keyspace to use in cassandra')
    parser.add_argument('data_table', help='the data table to use')
    parser.add_argument('contact_points', help='the contact points for cassandra')

    # - parse arguments
    args = parser.parse_args()
    topic_name = args.topic_name
    kafka_broker = args.kafka_broker
    key_space = args.key_space
    data_table = args.data_table
    contact_points = args.contact_points

    # - initiate a simple kafka consumer
    consumer = KafkaConsumer(
        topic_name,
        bootstrap_servers=kafka_broker
    )

    # - initiate a cassandra session
    cassandra_cluster = Cluster(
        contact_points=contact_points.split(',')
    )
    session = cassandra_cluster.connect()


    session.execute("CREATE KEYSPACE IF NOT EXISTS %s WITH replication = {'class': 'SimpleStrategy', 'replication_factor': '3'} AND durable_writes = 'true'" % key_space)
    session.set_keyspace(key_space)
    session.execute("CREATE TABLE IF NOT EXISTS %s (stock_symbol text, trade_time timestamp, trade_price float, PRIMARY KEY (stock_symbol,trade_time))" % data_table)

    # - setup proper shutdown hook
    atexit.register(shutdown_hook, consumer, session)

    for msg in consumer:
        persist_data(msg.value, session)
