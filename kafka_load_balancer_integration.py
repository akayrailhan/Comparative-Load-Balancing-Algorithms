"""
Load Balancing Simulator with Apache Kafka Integration
Real-time request processing from Kafka streams
"""

import json
import time
import threading
from typing import List, Dict, Optional
from datetime import datetime
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError
import logging

# Import from the main simulator
from load_balancing_simulator import (
    Server, Request, CloudLoadBalancerSimulator,
    RoundRobinLB, WeightedRoundRobinLB, LeastConnectionLB,
    LeastLoadLB, IPHashLB, RandomLB, LeastResponseTimeLB
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KafkaLoadBalancerConfig:
    """Configuration for Kafka integration"""
    
    def __init__(self):
        # Kafka broker configuration
        self.bootstrap_servers = ['localhost:9092']
        
        # Topic configuration
        self.input_topic = 'load-balancer-requests'
        self.output_topic = 'load-balancer-responses'
        self.metrics_topic = 'load-balancer-metrics'
        
        # Consumer configuration
        self.consumer_group = 'load-balancer-group'
        self.auto_offset_reset = 'earliest'
        self.enable_auto_commit = True
        
        # Producer configuration
        self. producer_acks = 'all'
        self.producer_retries = 3
        
        # Processing configuration
        self.batch_size = 10
        self.batch_timeout = 1.0  # seconds
        
    def get_consumer_config(self) -> Dict:
        """Get Kafka consumer configuration"""
        return {
            'bootstrap_servers': self.bootstrap_servers,
            'group_id': self.consumer_group,
            'auto_offset_reset': self.auto_offset_reset,
            'enable_auto_commit': self.enable_auto_commit,
            'value_deserializer': lambda m: json.loads(m.decode('utf-8')),
            'key_deserializer': lambda m:  m.decode('utf-8') if m else None
        }
    
    def get_producer_config(self) -> Dict:
        """Get Kafka producer configuration"""
        return {
            'bootstrap_servers': self.bootstrap_servers,
            'acks': self.producer_acks,
            'retries': self.producer_retries,
            'value_serializer': lambda m: json.dumps(m).encode('utf-8'),
            'key_serializer':  lambda m: m.encode('utf-8') if m else None
        }


class KafkaRequestProcessor:
    """Processes requests from Kafka and applies load balancing"""
    
    def __init__(self, config: KafkaLoadBalancerConfig, algorithm_name: str = 'round_robin'):
        self.config = config
        self.algorithm_name = algorithm_name
        
        # Initialize consumer and producer
        self.consumer = None
        self.producer = None
        
        # Initialize load balancer
        self.simulator = CloudLoadBalancerSimulator(num_servers=5)
        self.load_balancer = self._create_load_balancer(algorithm_name)
        
        # Processing state
        self.is_running = False
        self.request_count = 0
        self.processing_thread = None
        
        # Metrics
        self.metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'average_response_time': 0.0,
            'throughput':  0.0,
            'start_time': None
        }
    
    def _create_load_balancer(self, algorithm_name: str):
        """Create load balancer instance based on algorithm name"""
        algorithms = {
            'round_robin': RoundRobinLB,
            'weighted_round_robin': WeightedRoundRobinLB,
            'least_connection': LeastConnectionLB,
            'least_load':  LeastLoadLB,
            'ip_hash': IPHashLB,
            'random': RandomLB,
            'least_response_time': LeastResponseTimeLB
        }
        
        algorithm_class = algorithms. get(algorithm_name, RoundRobinLB)
        return algorithm_class(self. simulator. servers)
    
    def connect(self):
        """Connect to Kafka broker"""
        try:
            logger.info("Connecting to Kafka broker...")
            
            # Create consumer
            self. consumer = KafkaConsumer(
                self.config.input_topic,
                **self.config.get_consumer_config()
            )
            
            # Create producer
            self. producer = KafkaProducer(
                **self.config.get_producer_config()
            )
            
            logger.info("Successfully connected to Kafka")
            return True
            
        except KafkaError as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from Kafka"""
        logger.info("Disconnecting from Kafka...")
        
        if self.consumer:
            self.consumer.close()
        
        if self.producer:
            self.producer.flush()
            self.producer.close()
        
        logger.info("Disconnected from Kafka")
    
    def parse_request(self, message: Dict) -> Optional[Request]:
        """Parse Kafka message to Request object"""
        try:
            request = Request(
                id=message. get('request_id', self.request_count),
                arrival_time=message.get('timestamp', time.time()),
                processing_time=message.get('processing_time', 1.0),
                client_ip=message.get('client_ip', '0.0.0.0')
            )
            return request
            
        except Exception as e:
            logger.error(f"Failed to parse request: {e}")
            return None
    
    def process_request(self, request: Request) -> Dict:
        """Process a single request using load balancer"""
        try:
            start_time = time.time()
            
            # Select server using load balancing algorithm
            server = self.load_balancer.select_server(request)
            
            # Check if server can handle the request
            if server. current_load + request.processing_time > server.capacity:
                return {
                    'request_id': request.id,
                    'status': 'rejected',
                    'reason': 'server_overloaded',
                    'timestamp': time.time()
                }
            
            # Assign request to server
            request.assigned_server = server. id
            server.active_connections += 1
            server.current_load += request.processing_time
            
            # Simulate processing
            time.sleep(request.processing_time / 10)  # Scaled down for simulation
            
            # Complete request
            completion_time = time.time()
            request.completion_time = completion_time
            response_time = completion_time - start_time
            
            # Update server metrics
            server.total_requests_handled += 1
            server.total_response_time += response_time
            server.active_connections -= 1
            server.current_load = max(0, server.current_load - request.processing_time)
            
            # Return response
            return {
                'request_id': request.id,
                'status': 'success',
                'server_id': server.id,
                'response_time': response_time,
                'timestamp': completion_time,
                'client_ip': request.client_ip
            }
            
        except Exception as e:
            logger. error(f"Error processing request {request.id}: {e}")
            return {
                'request_id': request.id,
                'status': 'error',
                'error': str(e),
                'timestamp': time.time()
            }
    
    def send_response(self, response: Dict):
        """Send response to Kafka output topic"""
        try:
            future = self.producer.send(
                self.config.output_topic,
                key=str(response['request_id']),
                value=response
            )
            future.get(timeout=10)
            
        except Exception as e:
            logger.error(f"Failed to send response:  {e}")
    
    def send_metrics(self):
        """Send current metrics to Kafka metrics topic"""
        try:
            # Calculate current metrics
            if self.metrics['start_time']: 
                elapsed_time = time.time() - self.metrics['start_time']
                self.metrics['throughput'] = self.metrics['successful_requests'] / elapsed_time if elapsed_time > 0 else 0
            
            # Add server metrics
            server_metrics = []
            for server in self.simulator.servers:
                server_metrics.append({
                    'server_id': server.id,
                    'capacity': server.capacity,
                    'current_load': server.current_load,
                    'load_percentage': server.load_percentage,
                    'total_requests': server.total_requests_handled,
                    'average_response_time': server.average_response_time,
                    'active_connections': server.active_connections
                })
            
            metrics_payload = {
                'timestamp': time.time(),
                'algorithm': self.algorithm_name,
                'global_metrics': self.metrics. copy(),
                'server_metrics': server_metrics
            }
            
            self.producer.send(
                self.config.metrics_topic,
                value=metrics_payload
            )
            
        except Exception as e:
            logger.error(f"Failed to send metrics: {e}")
    
    def start(self):
        """Start processing requests from Kafka"""
        if not self.connect():
            logger.error("Failed to start:  Could not connect to Kafka")
            return
        
        self.is_running = True
        self. metrics['start_time'] = time. time()
        
        logger.info(f"Started processing with {self.algorithm_name} algorithm")
        
        # Start metrics reporting thread
        metrics_thread = threading.Thread(target=self._metrics_reporter, daemon=True)
        metrics_thread.start()
        
        try:
            batch = []
            batch_start_time = time.time()
            
            for message in self.consumer:
                if not self.is_running:
                    break
                
                # Parse request
                request_data = message.value
                request = self. parse_request(request_data)
                
                if request: 
                    batch.append(request)
                    self.request_count += 1
                    self.metrics['total_requests'] += 1
                
                # Process batch when size or timeout is reached
                if (len(batch) >= self.config.batch_size or 
                    time.time() - batch_start_time >= self.config.batch_timeout):
                    
                    self._process_batch(batch)
                    batch = []
                    batch_start_time = time. time()
            
            # Process remaining requests
            if batch:
                self._process_batch(batch)
                
        except KeyboardInterrupt:
            logger. info("Received interrupt signal")
        except Exception as e:
            logger. error(f"Error in processing loop: {e}")
        finally:
            self.stop()
    
    def _process_batch(self, batch:  List[Request]):
        """Process a batch of requests"""
        logger.info(f"Processing batch of {len(batch)} requests")
        
        for request in batch: 
            response = self. process_request(request)
            
            if response['status'] == 'success': 
                self.metrics['successful_requests'] += 1
            else:
                self.metrics['failed_requests'] += 1
            
            self.send_response(response)
    
    def _metrics_reporter(self):
        """Background thread to report metrics periodically"""
        while self.is_running:
            time.sleep(5)  # Report every 5 seconds
            self.send_metrics()
            self._log_metrics()
    
    def _log_metrics(self):
        """Log current metrics"""
        logger.info(f"Metrics - Total:  {self.metrics['total_requests']}, "
                   f"Success: {self.metrics['successful_requests']}, "
                   f"Failed: {self.metrics['failed_requests']}, "
                   f"Throughput: {self.metrics['throughput']:.2f} req/s")
    
    def stop(self):
        """Stop processing"""
        logger.info("Stopping processor...")
        self.is_running = False
        self.disconnect()
        logger.info("Processor stopped")


class KafkaRequestGenerator:
    """Generates sample requests and sends to Kafka"""
    
    def __init__(self, config: KafkaLoadBalancerConfig):
        self.config = config
        self.producer = None
        self.is_running = False
    
    def connect(self):
        """Connect to Kafka"""
        try:
            self.producer = KafkaProducer(
                **self.config.get_producer_config()
            )
            logger.info("Request generator connected to Kafka")
            return True
        except KafkaError as e:
            logger. error(f"Failed to connect generator: {e}")
            return False
    
    def generate_request(self, request_id: int) -> Dict:
        """Generate a sample request"""
        import random
        
        return {
            'request_id':  request_id,
            'timestamp': time.time(),
            'processing_time': random.uniform(0.5, 3.0),
            'client_ip': f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}",
            'request_type':  random.choice(['GET', 'POST', 'PUT', 'DELETE']),
            'endpoint': random.choice(['/api/users', '/api/products', '/api/orders']),
            'payload_size': random.randint(100, 5000)
        }
    
    def start(self, num_requests: int = 100, rate:  float = 10.0):
        """Start generating requests"""
        if not self.connect():
            return
        
        self.is_running = True
        logger.info(f"Starting to generate {num_requests} requests at {rate} req/s")
        
        try:
            for i in range(num_requests):
                if not self.is_running:
                    break
                
                request = self.generate_request(i)
                
                self.producer.send(
                    self.config.input_topic,
                    key=str(i),
                    value=request
                )
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Generated {i + 1} requests")
                
                # Control request rate
                time.sleep(1.0 / rate)
            
            self.producer.flush()
            logger.info(f"Finished generating {num_requests} requests")
            
        except Exception as e:
            logger.error(f"Error generating requests: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop generator"""
        self.is_running = False
        if self.producer:
            self.producer.close()
        logger.info("Request generator stopped")


def main():
    """Main execution with Kafka integration"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Load Balancer with Kafka Integration')
    parser.add_argument('--mode', choices=['processor', 'generator'], 
                       default='processor', help='Run mode')
    parser.add_argument('--algorithm', choices=[
        'round_robin', 'weighted_round_robin', 'least_connection',
        'least_load', 'ip_hash', 'random', 'least_response_time'
    ], default='round_robin', help='Load balancing algorithm')
    parser.add_argument('--num-requests', type=int, default=100,
                       help='Number of requests to generate')
    parser.add_argument('--rate', type=float, default=10.0,
                       help='Request generation rate (req/s)')
    parser.add_argument('--kafka-broker', default='localhost:9092',
                       help='Kafka broker address')
    
    args = parser.parse_args()
    
    # Create configuration
    config = KafkaLoadBalancerConfig()
    config.bootstrap_servers = [args.kafka_broker]
    
    if args.mode == 'processor': 
        # Start request processor
        processor = KafkaRequestProcessor(config, args.algorithm)
        processor.start()
    
    elif args.mode == 'generator':
        # Start request generator
        generator = KafkaRequestGenerator(config)
        generator.start(num_requests=args.num_requests, rate=args.rate)


if __name__ == "__main__":
    main()