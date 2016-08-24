# Kafka相关的代码

## simple-data-producer.py
实现了一个kafka producer, 每秒钟从Yahoo finance抓取一支股票的信息, 发送给Kafka

### 代码依赖
googlefinance   https://pypi.python.org/pypi/googlefinance
kafka-python    https://github.com/dpkp/kafka-python
schedule        https://pypi.python.org/pypi/schedule

```sh
pip install -r requirements.txt
```

### 运行代码
假如你的Kafka运行在一个叫做bigdata的docker-machine里面, 然后虚拟机的ip是192.168.99.100
```sh
python simple-data-producer.py AAPL stock-analyzer 192.168.99.100:9092
```