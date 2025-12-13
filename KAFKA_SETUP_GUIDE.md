# Apache Kafka Integration Guide for Load Balancing Simulator

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Kafka Installation](#kafka-installation)
3. [Configuration](#configuration)
4. [Running the System](#running-the-system)
5. [Data Flow Architecture](#data-flow-architecture)
6. [Monitoring & Metrics](#monitoring--metrics)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software
- Python 3.8+
- Apache Kafka 2.8+ (or Confluent Platform)
- Apache Zookeeper (comes with Kafka)
- Java 8+ (for Kafka)

### Python Dependencies
```bash
pip install kafka-python confluent-kafka
```

## Kafka Installation

### Option 1: Local Installation (Development)

#### Step 1: Download Kafka
```bash
# Download Kafka
wget https://archive.apache.org/dist/kafka/3.6.0/kafka_2.13-3.6.0.tgz

# Extract
tar -xzf kafka_2.13-3.6.0.tgz
cd kafka_2.13-3.6.0
```

#### Step 2: Start Zookeeper
```bash
# Start Zookeeper (Terminal 1)
bin/zookeeper-server-start.sh config/zookeeper. properties
```

#### Step 3: Start Kafka Broker
```bash
# Start Kafka (Terminal 2)
bin/kafka-server-start.sh config/server.properties
```

#### Step 4: Create Topics
```bash
# Create input topic for requests (Terminal 3)
bin/kafka-topics.sh --create \
  --topic load-balancer-requests \
  --bootstrap-server localhost:9092 \
  --partitions 3 \
  --replication-factor 1

# Create output topic for responses
bin/kafka-topics.sh --create \
  --topic load-balancer-responses \
  --bootstrap-server localhost:9092 \
  --partitions 3 \
  --replication-factor 1

# Create metrics topic
bin/kafka-topics.sh --create \
  --topic load-balancer-metrics \
  --bootstrap-server localhost:9092 \
  --partitions 1 \
  --replication-factor 1
```

#### Step 5: Verify Topics
```bash
# List all topics
bin/kafka-topics.sh --list --bootstrap-server localhost:9092

# Describe topic
bin/kafka-topics.sh --describe \
  --topic load-balancer-requests \
  --bootstrap-server localhost:9092
```

### Option 2: Docker Installation (Recommended)

#### Step 1: Create Docker Compose File

```yaml name=docker-compose.yml
version: '3.8'

services:
  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    hostname: zookeeper
    container_name: zookeeper
    ports:
      - "2181:2181"
    environment: 
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
    volumes:
      - zookeeper-data:/var/lib/zookeeper/data
      - zookeeper-logs:/var/lib/zookeeper/log

  kafka:
    image: confluentinc/cp-kafka: 7.5.0
    hostname: kafka
    container_name:  kafka
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
      - "9101:9101"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: 'zookeeper:2181'
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:29092,PLAINTEXT_HOST://localhost:9092
      KAFKA_METRIC_REPORTERS: io.confluent.metrics.reporter. ConfluentMetricsReporter
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS: 0
      KAFKA_CONFLUENT_METRICS_REPORTER_BOOTSTRAP_SERVERS: kafka:29092
      KAFKA_CONFLUENT_METRICS_REPORTER_TOPIC_REPLICAS: 1
      KAFKA_CONFLUENT_METRICS_ENABLE:  'false'
      KAFKA_JMX_PORT: 9101
      KAFKA_JMX_HOSTNAME: localhost
    volumes:
      - kafka-data:/var/lib/kafka/data

  kafka-ui:
    image: provectuslabs/kafka-ui:latest
    container_name: kafka-ui
    depends_on:
      - kafka
    ports:
      - "8080:8080"
    environment:
      KAFKA_CLUSTERS_0_NAME: local
      KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS: kafka:29092
      KAFKA_CLUSTERS_0_ZOOKEEPER: zookeeper:2181

  kafka-init:
    image: confluentinc/cp-kafka: 7.5.0
    depends_on:
      - kafka
    entrypoint: [ '/bin/sh', '-c' ]
    command:  |
      "
      # Wait for Kafka to be ready
      echo 'Waiting for Kafka to be ready...'
      cub kafka-ready -b kafka:29092 1 60

      # Create topics
      echo 'Creating topics.. .'
      kafka-topics --create --if-not-exists --bootstrap-server kafka:29092 --partitions 3 --replication-factor 1 --topic load-balancer-requests
      kafka-topics --create --if-not-exists --bootstrap-server kafka:29092 --partitions 3 --replication-factor 1 --topic load-balancer-responses
      kafka-topics --create --if-not-exists --bootstrap-server kafka:29092 --partitions 1 --replication-factor 1 --topic load-balancer-metrics

      echo 'Topics created successfully!'
      "

volumes:
  zookeeper-data:
  zookeeper-logs:
  kafka-data:
```

#### Step 2: Start Docker Services
```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f kafka

# Stop services
docker-compose down
```

#### Step 3: Access Kafka UI
Open browser:  http://localhost:8080

### Option 3: Cloud Kafka (Production)

#### Confluent Cloud
```bash
# Install Confluent CLI
curl -sL --http1.1 https://cnfl.io/cli | sh -s -- latest

# Login
confluent login

# Create cluster and topics through web console
# Update configuration with your cluster details
```

#### AWS MSK (Managed Streaming for Kafka)
```bash
# Use AWS Console or CLI to create MSK cluster
# Update bootstrap servers in configuration
```

## Configuration

### Update Configuration File

```python name=kafka_config.py
"""
Kafka Configuration for Load Balancer
"""

class KafkaConfig:
    # Kafka Broker Settings
    BOOTSTRAP_SERVERS = ['localhost:9092']  # Update for your environment
    
    # Topic Names
    INPUT_TOPIC = 'load-balancer-requests'
    OUTPUT_TOPIC = 'load-balancer-responses'
    METRICS_TOPIC = 'load-balancer-metrics'
    
    # Consumer Settings
    CONSUMER_GROUP = 'load-balancer-group'
    AUTO_OFFSET_RESET = 'earliest'  # 'earliest' or 'latest'
    ENABLE_AUTO_COMMIT = True
    MAX_POLL_RECORDS = 500
    
    # Producer Settings
    PRODUCER_ACKS = 'all'  # 0, 1, or 'all'
    PRODUCER_RETRIES = 3
    COMPRESSION_TYPE = 'snappy'  # None, 'gzip', 'snappy', 'lz4', 'zstd'
    
    # Processing Settings
    BATCH_SIZE = 10
    BATCH_TIMEOUT = 1.0  # seconds
    
    # Load Balancer Settings
    NUM_SERVERS = 5
    SERVER_CAPACITY_RANGE = (50, 100)
    DEFAULT_ALGORITHM = 'round_robin'

# For production/cloud environments
class ProductionConfig(KafkaConfig):
    BOOTSTRAP_SERVERS = ['kafka-broker-1:9092', 'kafka-broker-2:9092']
    PRODUCER_ACKS = 'all'
    COMPRESSION_TYPE = 'snappy'
    
# For development
class DevelopmentConfig(KafkaConfig):
    AUTO_OFFSET_RESET = 'latest'
    BATCH_SIZE = 5
```

## Running the System

### Complete Setup Script

```bash name=setup_and_run.sh
#!/bin/bash

echo "=== Load Balancer Kafka Setup ==="

# Step 1: Install Python dependencies
echo "Installing Python dependencies..."
pip install kafka-python numpy matplotlib

# Step 2: Start Kafka (Docker)
echo "Starting Kafka services..."
docker-compose up -d

# Wait for Kafka to be ready
echo "Waiting for Kafka to be ready..."
sleep 30

# Step 3: Verify topics
echo "Verifying Kafka topics..."
docker exec kafka kafka-topics --list --bootstrap-server localhost:9092

# Step 4: Start load balancer processor (in background)
echo "Starting load balancer processor..."
python kafka_load_balancer_integration.py \
  --mode processor \
  --algorithm least_connection &
PROCESSOR_PID=$!

# Wait a bit
sleep 5

# Step 5: Generate test requests
echo "Generating test requests..."
python kafka_load_balancer_integration.py \
  --mode generator \
  --num-requests 1000 \
  --rate 50.0

# Step 6: Monitor metrics
echo "Monitoring metrics..."
python kafka_consumer_monitor.py --topic load-balancer-metrics

# Cleanup
echo "Stopping processor..."
kill $PROCESSOR_PID

echo "Setup complete!"
```

### Manual Execution

#### Terminal 1: Start Processor
```bash
python kafka_load_balancer_integration.py \
  --mode processor \
  --algorithm least_connection \
  --kafka-broker localhost: 9092
```

#### Terminal 2: Generate Requests
```bash
python kafka_load_balancer_integration.py \
  --mode generator \
  --num-requests 1000 \
  --rate 50.0 \
  --kafka-broker localhost:9092
```

#### Terminal 3: Monitor Responses
```bash
# Console consumer to view responses
kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic load-balancer-responses \
  --from-beginning \
  --formatter kafka.tools.DefaultMessageFormatter \
  --property print.key=true \
  --property print.value=true
```

#### Terminal 4: Monitor Metrics
```bash
# Console consumer to view metrics
kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic load-balancer-metrics \
  --from-beginning
```

## Data Flow Architecture

### Request Flow Diagram
```
External System → Kafka Topic (requests) → Load Balancer Processor
                                                ↓
                                          Select Server
                                                ↓
                                          Process Request
                                                ↓
                                    Kafka Topic (responses) → External System
                                                ↓
                                    Kafka Topic (metrics) → Monitoring
```

### Message Format

#### Request Message (Input Topic)
```json
{
  "request_id": 12345,
  "timestamp": 1702468800.123,
  "processing_time": 1.5,
  "client_ip": "192.168.1.100",
  "request_type": "GET",
  "endpoint": "/api/users",
  "payload_size": 1024
}
```

#### Response Message (Output Topic)
```json
{
  "request_id":  12345,
  "status":  "success",
  "server_id": 2,
  "response_time": 0.156,
  "timestamp": 1702468801.279,
  "client_ip": "192.168.1.100"
}
```

#### Metrics Message (Metrics Topic)
```json
{
  "timestamp": 1702468800.500,
  "algorithm": "least_connection",
  "global_metrics": {
    "total_requests": 1000,
    "successful_requests": 985,
    "failed_requests":  15,
    "throughput": 50.5
  },
  "server_metrics": [
    {
      "server_id": 0,
      "capacity": 75,
      "current_load": 45.5,
      "load_percentage": 60.67,
      "total_requests": 197,
      "average_response_time": 0.145,
      "active_connections": 3
    }
  ]
}
```

## Monitoring & Metrics

### Create Metrics Consumer

```python name=kafka_metrics_monitor.py
"""
Real-time metrics monitoring from Kafka
"""

from kafka import KafkaConsumer
import json
import time
from datetime import datetime

def monitor_metrics(bootstrap_servers='localhost:9092', 
                   topic='load-balancer-metrics'):
    """Monitor and display metrics in real-time"""
    
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        auto_offset_reset='latest',
        value_deserializer=lambda m:  json.loads(m.decode('utf-8'))
    )
    
    print("=== Load Balancer Metrics Monitor ===\n")
    
    try:
        for message in consumer: 
            metrics = message.value
            
            print(f"\n--- Metrics Update at {datetime.fromtimestamp(metrics['timestamp'])} ---")
            print(f"Algorithm: {metrics['algorithm']}")
            
            global_metrics = metrics['global_metrics']
            print(f"\nGlobal Metrics:")
            print(f"  Total Requests: {global_metrics['total_requests']}")
            print(f"  Success:  {global_metrics['successful_requests']}")
            print(f"  Failed: {global_metrics['failed_requests']}")
            print(f"  Throughput:  {global_metrics['throughput']:.2f} req/s")
            
            print(f"\nServer Metrics:")
            for server in metrics['server_metrics']:
                print(f"  Server {server['server_id']}:")
                print(f"    Load: {server['load_percentage']:.2f}%")
                print(f"    Requests: {server['total_requests']}")
                print(f"    Avg Response Time: {server['average_response_time']:.4f}s")
                print(f"    Active Connections: {server['active_connections']}")
            
            print("-" * 50)
    
    except KeyboardInterrupt:
        print("\nMonitoring stopped")
    finally:
        consumer.close()

if __name__ == "__main__": 
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--broker', default='localhost:9092')
    parser.add_argument('--topic', default='load-balancer-metrics')
    args = parser.parse_args()
    
    monitor_metrics(args. broker, args.topic)
```

### Run Metrics Monitor
```bash
python kafka_metrics_monitor.py --broker localhost:9092
```

## Troubleshooting

### Common Issues

#### 1. Connection Refused
```bash
# Check if Kafka is running
docker ps
# or
ps aux | grep kafka

# Check Kafka logs
docker logs kafka
# or
tail -f kafka/logs/server.log
```

#### 2. Topic Not Found
```bash
# List topics
kafka-topics. sh --list --bootstrap-server localhost:9092

# Create missing topic
kafka-topics.sh --create \
  --topic load-balancer-requests \
  --bootstrap-server localhost:9092 \
  --partitions 3 \
  --replication-factor 1
```

#### 3. Consumer Lag
```bash
# Check consumer group status
kafka-consumer-groups. sh --bootstrap-server localhost:9092 \
  --group load-balancer-group \
  --describe
```

#### 4. Port Already in Use
```bash
# Find process using port 9092
lsof -i :9092

# Kill process
kill -9 <PID>
```

### Testing

#### Test Kafka Connection
```python name=test_kafka_connection.py
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError

def test_connection(bootstrap_servers='localhost:9092'):
    try:
        # Test producer
        producer = KafkaProducer(bootstrap_servers=bootstrap_servers)
        print("✓ Producer connected successfully")
        producer.close()
        
        # Test consumer
        consumer = KafkaConsumer(
            bootstrap_servers=bootstrap_servers,
            consumer_timeout_ms=1000
        )
        print("✓ Consumer connected successfully")
        consumer.close()
        
        return True
    except KafkaError as e: 
        print(f"✗ Connection failed: {e}")
        return False

if __name__ == "__main__":
    test_connection()
```

## Advanced Configuration

### Multiple Brokers
```python
BOOTSTRAP_SERVERS = [
    'kafka-broker-1:9092',
    'kafka-broker-2:9092',
    'kafka-broker-3:9092'
]
```

### SSL/TLS Configuration
```python
config = {
    'bootstrap_servers': ['broker: 9093'],
    'security_protocol': 'SSL',
    'ssl_cafile': '/path/to/ca-cert',
    'ssl_certfile':  '/path/to/client-cert',
    'ssl_keyfile': '/path/to/client-key',
}
```

### SASL Authentication
```python
config = {
    'bootstrap_servers': ['broker:9093'],
    'security_protocol': 'SASL_SSL',
    'sasl_mechanism': 'PLAIN',
    'sasl_plain_username':  'your-username',
    'sasl_plain_password': 'your-password',
}
```

## Next Steps

1. **Scale Testing**: Increase request rate and monitor performance
2. **Add More Algorithms**: Implement custom load balancing algorithms
3. **Real Data Integration**: Connect to actual application logs
4. **Monitoring Dashboard**: Create Grafana dashboard for visualization
5. **Alert System**:  Implement alerts for anomalies

## Resources

- [Kafka Documentation](https://kafka.apache.org/documentation/)
- [kafka-python Documentation](https://kafka-python.readthedocs.io/)
- [Confluent Platform](https://docs.confluent.io/)