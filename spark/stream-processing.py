import atexit
import logging
import json
import sys
import time

from kafka import KafkaProducer
from kafka.errors import KafkaError, KafkaTimeoutError
from pyspark import SparkContext
from pyspark.streaming import StreamingContext
from pyspark.streaming.kafka import KafkaUtils

logger_format = '%(asctime)-15s %(message)s'
logging.basicConfig(format=logger_format)
logger = logging.getLogger('stream-processing')
logger.setLevel(logging.INFO)

topic = None
target_topic = None
brokers = None
kafka_producer = None


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


def process(timeobj, rdd):
    num_of_records = rdd.count()
    if num_of_records == 0:
        return
    price_sum = rdd \
        .map(lambda record: float(json.loads(record[1].decode('utf-8'))[0].get('LastTradePrice'))) \
        .reduce(lambda a, b: a + b)

    average = price_sum / num_of_records
    logger.info('Received %d records from kafka, average price is %f' % (num_of_records, average))
    current_time = time.time()
    data = json.dumps({
        'timestamp': current_time,
        'average': average
    })
    try:
        kafka_producer.send(target_topic, value=data)
    except KafkaError as error:
        logger.warn('Failed to send average stock price to kafka, caused by: %s', error.message)

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: stream-process.py [topic] [target-topic] [broker-list]")
        exit(1)

    # - create SparkContext and StreamingContext
    sc = SparkContext("local[2]", "StockAveragePrice")
    sc.setLogLevel('ERROR')
    ssc = StreamingContext(sc, 5)

    topic, target_topic, brokers = sys.argv[1:]

    # - instantiate a kafka stream for processing
    directKafkaStream = KafkaUtils.createDirectStream(ssc, [topic], {'metadata.broker.list': brokers})
    directKafkaStream.foreachRDD(process)

    # - instantiate a simple kafka producer
    kafka_producer = KafkaProducer(
        bootstrap_servers=brokers
    )

    # - setup proper shutdown hook
    atexit.register(shutdown_hook, kafka_producer)

    ssc.start()
    ssc.awaitTermination()
