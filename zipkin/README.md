# Zipkin相关的代码
以kafka的producer为例子演示zipkin的工作过程

## 安装依赖
```sh
pip install -r requirements.txt
```

## 启动运行环境
```sh
docker run -d -p 2181:2181 -p 2888:2888 -p 3888:3888 --name zookeeper confluent/zookeeper
docker run -d -p 9092:9092 -e KAFKA_ADVERTISED_HOST_NAME=localhost -e KAFKA_ADVERTISED_PORT=9092 --name kafka --link zookeeper:zookeeper confluent/kafka
docker run -d -p 7199:7199 -p 9042:9042 -p 9160:9160 -p 7001:7001 --name cassandra cassandra:3.7
docker run -d -p 9411:9411 --name zipkin openzipkin/zipkin
```

## 运行代码
```sh
python data-producer.py AAPL stock-analyzer localhost:9092
python data-storage.py stock-analyzer localhost:9092 data data localhost
```