"""
Comparative Analysis of Load Balancing Algorithms
Simulated Implementation in Python
"""

import random
import time
import statistics
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
import matplotlib.pyplot as plt
import numpy as np


class LoadBalancingStrategy(Enum):
    """Load balancing algorithm types"""
    ROUND_ROBIN = "round_robin"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"
    LEAST_LOAD = "least_load"
    IP_HASH = "ip_hash"
    RANDOM = "random"
    LEAST_RESPONSE_TIME = "least_response_time"


@dataclass
class Server:
    """Represents a server in the load balancer pool"""
    server_id: int
    capacity: int = 100
    current_load: int = 0
    total_requests: int = 0
    total_response_time: float = 0.0
    active_connections: int = 0
    weight: int = 1
    
    @property
    def utilization(self) -> float:
        return (self.current_load / self.capacity) * 100 if self.capacity > 0 else 0
    
    @property
    def avg_response_time(self) -> float:
        return (self.total_response_time / self.total_requests 
                if self.total_requests > 0 else 0)
    
    def can_accept_request(self) -> bool:
        return self.current_load < self.capacity
    
    def process_request(self, request_type: str = "cpu", complexity: int = 5) -> float:
        base_time = {'cpu': 0.1, 'memory': 0.05, 'io': 0.15}.get(request_type, 0.1)
        processing_time = base_time * complexity * random.uniform(0.8, 1.2)
        
        self.current_load += 1
        self.active_connections += 1
        self.total_requests += 1
        
        time.sleep(processing_time / 10)
        
        self.current_load = max(0, self.current_load - 1)
        self.active_connections = max(0, self.active_connections - 1)
        self.total_response_time += processing_time
        
        return processing_time


class LoadBalancer:
    """Base load balancer implementation"""
    
    def __init__(self, servers: List[Server], strategy: LoadBalancingStrategy):
        self.servers = servers
        self.strategy = strategy
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.current_index = 0
        self.current_weight = 0
        
    def route_request(self, client_ip: Optional[str] = None) -> Optional[Server]:
        self.total_requests += 1
        
        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin()
        elif self.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            return self._weighted_round_robin()
        elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._least_connections()
        elif self.strategy == LoadBalancingStrategy.LEAST_LOAD:
            return self._least_load()
        elif self.strategy == LoadBalancingStrategy.IP_HASH:
            return self._ip_hash(client_ip)
        elif self.strategy == LoadBalancingStrategy.RANDOM:
            return self._random()
        elif self.strategy == LoadBalancingStrategy.LEAST_RESPONSE_TIME:
            return self._least_response_time()
        
        return None
    
    def _round_robin(self) -> Optional[Server]:
        attempts = 0
        while attempts < len(self.servers):
            server = self.servers[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.servers)
            if server.can_accept_request():
                return server
            attempts += 1
        return None
    
    def _weighted_round_robin(self) -> Optional[Server]:
        max_weight = max(s.weight for s in self.servers)
        while True:
            self.current_index = (self.current_index + 1) % len(self.servers)
            if self.current_index == 0:
                self.current_weight = (self.current_weight - 1) % max_weight + 1
            server = self.servers[self.current_index]
            if server.weight >= self.current_weight and server.can_accept_request():
                return server
            if self.current_weight == 1:
                available = [s for s in self.servers if s.can_accept_request()]
                return available[0] if available else None
    
    def _least_connections(self) -> Optional[Server]:
        available = [s for s in self.servers if s.can_accept_request()]
        return min(available, key=lambda s: s.active_connections) if available else None
    
    def _least_load(self) -> Optional[Server]:
        available = [s for s in self.servers if s.can_accept_request()]
        return min(available, key=lambda s: s.current_load) if available else None
    
    def _ip_hash(self, client_ip: Optional[str]) -> Optional[Server]:
        if not client_ip:
            client_ip = f"192.168.1.{random.randint(1, 255)}"
        hash_value = hash(client_ip)
        index = hash_value % len(self.servers)
        if self.servers[index].can_accept_request():
            return self.servers[index]
        return self._round_robin()
    
    def _random(self) -> Optional[Server]:
        available = [s for s in self.servers if s.can_accept_request()]
        return random.choice(available) if available else None
    
    def _least_response_time(self) -> Optional[Server]:
        available = [s for s in self.servers if s.can_accept_request()]
        if not available:
            return None
        def score(server):
            response_time = server.avg_response_time if server.avg_response_time > 0 else 1
            return server.utilization * response_time
        return min(available, key=score)


def run_simulation(num_servers: int = 5, num_requests: int = 100, 
                   strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN) -> Dict:
    servers = [Server(server_id=i, capacity=random.randint(50, 150), 
                     weight=random.randint(1, 5)) for i in range(num_servers)]
    lb = LoadBalancer(servers, strategy)
    start_time = time.time()
    response_times = []
    
    for i in range(num_requests):
        server = lb.route_request(client_ip=f"192.168.1.{i % 255}")
        if server:
            request_type = random.choice(['cpu', 'memory', 'io'])
            complexity = random.randint(1, 10)
            processing_time = server.process_request(request_type, complexity)
            response_times.append(processing_time)
            lb.successful_requests += 1
        else:
            lb.failed_requests += 1
    
    total_time = time.time() - start_time
    
    return {
        'strategy': strategy.value,
        'total_requests': num_requests,
        'successful_requests': lb.successful_requests,
        'failed_requests': lb.failed_requests,
        'total_time': total_time,
        'throughput': num_requests / total_time if total_time > 0 else 0,
        'avg_response_time': statistics.mean(response_times) if response_times else 0,
        'median_response_time': statistics.median(response_times) if response_times else 0,
        'min_response_time': min(response_times) if response_times else 0,
        'max_response_time': max(response_times) if response_times else 0,
        'server_stats': [{'server_id': s.server_id, 'capacity': s.capacity,
                         'total_requests': s.total_requests, 'utilization': s.utilization,
                         'avg_response_time': s.avg_response_time} for s in servers]
    }


def compare_algorithms(num_servers: int = 5, num_requests: int = 100):
    strategies = list(LoadBalancingStrategy)
    results = {}
    print("Running comparative analysis...")
    print("=" * 60)
    
    for strategy in strategies:
        print(f"\nTesting {strategy.value}...")
        result = run_simulation(num_servers, num_requests, strategy)
        results[strategy.value] = result
        print(f"  Successful: {result['successful_requests']}/{result['total_requests']}")
        print(f"  Avg Response Time: {result['avg_response_time']:.4f}s")
        print(f"  Throughput: {result['throughput']:.2f} req/s")
    
    visualize_comparison(results)
    return results


def visualize_comparison(results: Dict):
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    fig.suptitle('Load Balancing Algorithms Comparison', fontsize=16, fontweight='bold')
    strategies = list(results.keys())
    
    ax = axes[0, 0]
    response_times = [results[s]['avg_response_time'] for s in strategies]
    ax.bar(range(len(strategies)), response_times, color='skyblue')
    ax.set_xticks(range(len(strategies)))
    ax.set_xticklabels([s.replace('_', '\n') for s in strategies], fontsize=8)
    ax.set_ylabel('Time (seconds)')
    ax.set_title('Average Response Time')
    ax.grid(axis='y', alpha=0.3)
    
    ax = axes[0, 1]
    throughputs = [results[s]['throughput'] for s in strategies]
    ax.bar(range(len(strategies)), throughputs, color='lightgreen')
    ax.set_xticks(range(len(strategies)))
    ax.set_xticklabels([s.replace('_', '\n') for s in strategies], fontsize=8)
    ax.set_ylabel('Requests/Second')
    ax.set_title('Throughput')
    ax.grid(axis='y', alpha=0.3)
    
    ax = axes[0, 2]
    success_rates = [(results[s]['successful_requests'] / results[s]['total_requests']) * 100 
                    for s in strategies]
    ax.bar(range(len(strategies)), success_rates, color='lightcoral')
    ax.set_xticks(range(len(strategies)))
    ax.set_xticklabels([s.replace('_', '\n') for s in strategies], fontsize=8)
    ax.set_ylabel('Success Rate (%)')
    ax.set_title('Success Rate')
    ax.set_ylim([0, 105])
    ax.grid(axis='y', alpha=0.3)
    
    first_strategy = strategies[0]
    ax = axes[1, 0]
    server_requests = [s['total_requests'] for s in results[first_strategy]['server_stats']]
    server_ids = [s['server_id'] for s in results[first_strategy]['server_stats']]
    ax.bar(server_ids, server_requests, color='plum')
    ax.set_xlabel('Server ID')
    ax.set_ylabel('Number of Requests')
    ax.set_title(f'Request Distribution\n({first_strategy})')
    ax.grid(axis='y', alpha=0.3)
    
    ax = axes[1, 1]
    mins = [results[s]['min_response_time'] for s in strategies]
    maxs = [results[s]['max_response_time'] for s in strategies]
    x = np.arange(len(strategies))
    width = 0.35
    ax.bar(x - width/2, mins, width, label='Min', color='lightblue')
    ax.bar(x + width/2, maxs, width, label='Max', color='orange')
    ax.set_xticks(range(len(strategies)))
    ax.set_xticklabels([s.replace('_', '\n') for s in strategies], fontsize=8)
    ax.set_ylabel('Time (seconds)')
    ax.set_title('Min/Max Response Times')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    
    ax = axes[1, 2]
    utilizations = [s['utilization'] for s in results[first_strategy]['server_stats']]
    ax.bar(server_ids, utilizations, color='gold')
    ax.set_xlabel('Server ID')
    ax.set_ylabel('Utilization (%)')
    ax.set_title(f'Server Utilization\n({first_strategy})')
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('load_balancing_comparison.png', dpi=300, bbox_inches='tight')
    print("\nVisualization saved as 'load_balancing_comparison.png'")
    plt.show()


if __name__ == "__main__":
    print("Load Balancing Simulator")
    print("=" * 60)
    results = compare_algorithms(num_servers=5, num_requests=200)
    print("\n" + "=" * 60)
    print("Simulation complete!")
    print("Check 'load_balancing_comparison.png' for visualization")