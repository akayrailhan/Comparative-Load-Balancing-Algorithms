"""
Comparative Analysis of Load Balancing Algorithms in Cloud Environments
Simulated Implementation in Python
"""

import random
import time
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum
import statistics


class ServerStatus(Enum):
    IDLE = "idle"
    BUSY = "busy"
    OVERLOADED = "overloaded"


@dataclass
class Server:
    """Represents a cloud server"""
    id: int
    capacity: int
    current_load: int = 0
    total_requests_handled: int = 0
    total_response_time: float = 0.0
    processing_power: float = 1.0  # Relative processing power
    active_connections: int = 0
    request_queue: deque = field(default_factory=deque)
    
    @property
    def load_percentage(self) -> float:
        return (self.current_load / self.capacity) * 100 if self.capacity > 0 else 0
    
    @property
    def status(self) -> ServerStatus:
        if self.load_percentage < 50:
            return ServerStatus.IDLE
        elif self.load_percentage < 80:
            return ServerStatus. BUSY
        else:
            return ServerStatus.OVERLOADED
    
    @property
    def average_response_time(self) -> float:
        return self.total_response_time / self.total_requests_handled if self.total_requests_handled > 0 else 0


@dataclass
class Request:
    """Represents a client request"""
    id: int
    arrival_time: float
    processing_time: float
    client_ip: str
    completion_time: float = 0.0
    assigned_server: int = -1
    
    @property
    def response_time(self) -> float:
        return self. completion_time - self.arrival_time if self.completion_time > 0 else 0


class LoadBalancingAlgorithm:
    """Base class for load balancing algorithms"""
    
    def __init__(self, servers:  List[Server]):
        self.servers = servers
        self.metrics = {
            'requests_processed': 0,
            'total_response_time': 0.0,
            'server_utilization': [],
            'rejected_requests': 0
        }
    
    def select_server(self, request: Request) -> Server:
        raise NotImplementedError
    
    def update_metrics(self):
        self.metrics['server_utilization'] = [s.load_percentage for s in self.servers]


class RoundRobinLB(LoadBalancingAlgorithm):
    """Round Robin Load Balancing"""
    
    def __init__(self, servers: List[Server]):
        super().__init__(servers)
        self.current_index = 0
    
    def select_server(self, request: Request) -> Server:
        server = self.servers[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.servers)
        return server


class WeightedRoundRobinLB(LoadBalancingAlgorithm):
    """Weighted Round Robin based on server capacity"""
    
    def __init__(self, servers: List[Server]):
        super().__init__(servers)
        self.weights = [s.capacity for s in servers]
        self.current_index = 0
        self.current_weight = 0
        self.max_weight = max(self.weights)
        self.gcd_weight = self._gcd_list(self.weights)
    
    def _gcd(self, a: int, b:  int) -> int:
        while b:
            a, b = b, a % b
        return a
    
    def _gcd_list(self, weights: List[int]) -> int:
        result = weights[0]
        for w in weights[1:]:
            result = self._gcd(result, w)
        return result
    
    def select_server(self, request: Request) -> Server:
        while True:
            self.current_index = (self.current_index + 1) % len(self.servers)
            if self.current_index == 0:
                self.current_weight -= self.gcd_weight
                if self.current_weight <= 0:
                    self.current_weight = self.max_weight
            
            if self.weights[self.current_index] >= self.current_weight:
                return self.servers[self.current_index]


class LeastConnectionLB(LoadBalancingAlgorithm):
    """Least Connection Load Balancing"""
    
    def select_server(self, request: Request) -> Server:
        return min(self.servers, key=lambda s: s.active_connections)


class LeastLoadLB(LoadBalancingAlgorithm):
    """Least Load (Current Load) Load Balancing"""
    
    def select_server(self, request: Request) -> Server:
        return min(self. servers, key=lambda s: s.current_load)


class IPHashLB(LoadBalancingAlgorithm):
    """IP Hash Load Balancing"""
    
    def select_server(self, request: Request) -> Server:
        hash_value = hash(request.client_ip)
        server_index = hash_value % len(self.servers)
        return self.servers[server_index]


class RandomLB(LoadBalancingAlgorithm):
    """Random Load Balancing"""
    
    def select_server(self, request: Request) -> Server:
        return random.choice(self. servers)


class LeastResponseTimeLB(LoadBalancingAlgorithm):
    """Least Response Time Load Balancing"""
    
    def select_server(self, request: Request) -> Server:
        # Combine current load and average response time
        def score(server:  Server) -> float:
            avg_response = server.average_response_time if server.average_response_time > 0 else 1.0
            return server.load_percentage * avg_response
        
        return min(self.servers, key=score)


class CloudLoadBalancerSimulator:
    """Main simulator for cloud load balancing"""
    
    def __init__(self, num_servers: int = 5, server_capacity_range:  Tuple[int, int] = (50, 100)):
        self.servers = self._initialize_servers(num_servers, server_capacity_range)
        self.requests:  List[Request] = []
        self.current_time = 0.0
        self.results:  Dict[str, Dict] = {}
    
    def _initialize_servers(self, num_servers: int, capacity_range: Tuple[int, int]) -> List[Server]:
        servers = []
        for i in range(num_servers):
            capacity = random.randint(*capacity_range)
            processing_power = random.uniform(0.8, 1.2)
            servers.append(Server(id=i, capacity=capacity, processing_power=processing_power))
        return servers
    
    def generate_requests(self, num_requests: int, arrival_rate: float = 1.0):
        """Generate requests with exponential inter-arrival times"""
        self.requests = []
        current_time = 0.0
        
        for i in range(num_requests):
            # Exponential inter-arrival time
            inter_arrival = random.expovariate(arrival_rate)
            current_time += inter_arrival
            
            # Random processing time
            processing_time = random.expovariate(1.0)
            
            # Random client IP
            client_ip = f"192.168.{random. randint(1, 255)}.{random.randint(1, 255)}"
            
            request = Request(
                id=i,
                arrival_time=current_time,
                processing_time=processing_time,
                client_ip=client_ip
            )
            self.requests. append(request)
    
    def simulate(self, algorithm:  LoadBalancingAlgorithm, algorithm_name: str):
        """Run simulation with a specific algorithm"""
        # Reset servers
        for server in self.servers:
            server.current_load = 0
            server.total_requests_handled = 0
            server. total_response_time = 0.0
            server.active_connections = 0
            server.request_queue.clear()
        
        completed_requests = []
        rejected_requests = 0
        
        for request in self.requests:
            # Select server using the algorithm
            server = algorithm.select_server(request)
            
            # Check if server can handle the request
            if server.current_load + request.processing_time > server.capacity:
                rejected_requests += 1
                continue
            
            # Assign request to server
            request.assigned_server = server.id
            server.active_connections += 1
            server.current_load += request.processing_time
            
            # Simulate processing
            completion_time = request.arrival_time + (request.processing_time / server. processing_power)
            request.completion_time = completion_time
            
            # Update server metrics
            server.total_requests_handled += 1
            server.total_response_time += request.response_time
            server.active_connections -= 1
            
            completed_requests.append(request)
        
        # Calculate metrics
        response_times = [r.response_time for r in completed_requests]
        server_loads = [s.current_load for s in self.servers]
        server_utilizations = [s.load_percentage for s in self.servers]
        
        self.results[algorithm_name] = {
            'completed_requests': len(completed_requests),
            'rejected_requests': rejected_requests,
            'average_response_time': statistics.mean(response_times) if response_times else 0,
            'median_response_time': statistics.median(response_times) if response_times else 0,
            'std_response_time': statistics.stdev(response_times) if len(response_times) > 1 else 0,
            'min_response_time': min(response_times) if response_times else 0,
            'max_response_time': max(response_times) if response_times else 0,
            'server_utilization': server_utilizations,
            'average_utilization': statistics.mean(server_utilizations),
            'load_balance_score': 1 / (statistics.stdev(server_utilizations) + 1) if server_utilizations else 0,
            'throughput': len(completed_requests) / (self.requests[-1].arrival_time if self.requests else 1),
            'server_requests':  [s.total_requests_handled for s in self.servers]
        }
    
    def run_all_algorithms(self, num_requests: int = 1000):
        """Run simulation for all algorithms"""
        print(f"Generating {num_requests} requests...")
        self.generate_requests(num_requests)
        
        algorithms = [
            (RoundRobinLB(self._clone_servers()), "Round Robin"),
            (WeightedRoundRobinLB(self._clone_servers()), "Weighted Round Robin"),
            (LeastConnectionLB(self._clone_servers()), "Least Connection"),
            (LeastLoadLB(self._clone_servers()), "Least Load"),
            (IPHashLB(self._clone_servers()), "IP Hash"),
            (RandomLB(self._clone_servers()), "Random"),
            (LeastResponseTimeLB(self._clone_servers()), "Least Response Time")
        ]
        
        for algorithm, name in algorithms:
            print(f"Running {name} algorithm...")
            self.simulate(algorithm, name)
    
    def _clone_servers(self) -> List[Server]:
        """Create fresh copies of servers for each simulation"""
        return [Server(id=s.id, capacity=s.capacity, processing_power=s.processing_power) 
                for s in self.servers]
    
    def print_results(self):
        """Print detailed results"""
        print("\n" + "="*80)
        print("COMPARATIVE ANALYSIS OF LOAD BALANCING ALGORITHMS")
        print("="*80 + "\n")
        
        for algo_name, metrics in self.results.items():
            print(f"\n{algo_name}")
            print("-" * 40)
            print(f"  Completed Requests: {metrics['completed_requests']}")
            print(f"  Rejected Requests: {metrics['rejected_requests']}")
            print(f"  Average Response Time: {metrics['average_response_time']:.4f}s")
            print(f"  Median Response Time:  {metrics['median_response_time']:.4f}s")
            print(f"  Std Dev Response Time: {metrics['std_response_time']:.4f}s")
            print(f"  Min Response Time: {metrics['min_response_time']:.4f}s")
            print(f"  Max Response Time: {metrics['max_response_time']:. 4f}s")
            print(f"  Average Server Utilization: {metrics['average_utilization']:.2f}%")
            print(f"  Load Balance Score: {metrics['load_balance_score']:.4f}")
            print(f"  Throughput: {metrics['throughput']:.2f} req/s")
    
    def visualize_results(self):
        """Create visualization of results"""
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle('Comparative Analysis of Load Balancing Algorithms', fontsize=16, fontweight='bold')
        
        algo_names = list(self.results.keys())
        
        # 1. Average Response Time
        ax = axes[0, 0]
        response_times = [self.results[name]['average_response_time'] for name in algo_names]
        bars = ax.bar(range(len(algo_names)), response_times, color='skyblue')
        ax.set_xlabel('Algorithm')
        ax.set_ylabel('Time (seconds)')
        ax.set_title('Average Response Time')
        ax.set_xticks(range(len(algo_names)))
        ax.set_xticklabels(algo_names, rotation=45, ha='right')
        ax.grid(axis='y', alpha=0.3)
        
        # 2. Throughput
        ax = axes[0, 1]
        throughputs = [self.results[name]['throughput'] for name in algo_names]
        bars = ax.bar(range(len(algo_names)), throughputs, color='lightgreen')
        ax.set_xlabel('Algorithm')
        ax.set_ylabel('Requests/Second')
        ax.set_title('Throughput')
        ax.set_xticks(range(len(algo_names)))
        ax.set_xticklabels(algo_names, rotation=45, ha='right')
        ax.grid(axis='y', alpha=0.3)
        
        # 3. Average Server Utilization
        ax = axes[0, 2]
        utilizations = [self.results[name]['average_utilization'] for name in algo_names]
        bars = ax.bar(range(len(algo_names)), utilizations, color='lightcoral')
        ax.set_xlabel('Algorithm')
        ax.set_ylabel('Utilization (%)')
        ax.set_title('Average Server Utilization')
        ax.set_xticks(range(len(algo_names)))
        ax.set_xticklabels(algo_names, rotation=45, ha='right')
        ax.grid(axis='y', alpha=0.3)
        
        # 4. Load Balance Score
        ax = axes[1, 0]
        lb_scores = [self.results[name]['load_balance_score'] for name in algo_names]
        bars = ax.bar(range(len(algo_names)), lb_scores, color='plum')
        ax.set_xlabel('Algorithm')
        ax.set_ylabel('Score')
        ax.set_title('Load Balance Score (Higher is Better)')
        ax.set_xticks(range(len(algo_names)))
        ax.set_xticklabels(algo_names, rotation=45, ha='right')
        ax.grid(axis='y', alpha=0.3)
        
        # 5. Server Utilization Distribution
        ax = axes[1, 1]
        x = np.arange(len(self.servers))
        width = 0.12
        for i, algo_name in enumerate(algo_names):
            utilizations = self.results[algo_name]['server_utilization']
            offset = width * (i - len(algo_names)/2)
            ax.bar(x + offset, utilizations, width, label=algo_name)
        ax.set_xlabel('Server ID')
        ax.set_ylabel('Utilization (%)')
        ax.set_title('Server Utilization Distribution')
        ax.set_xticks(x)
        ax.legend(fontsize=8)
        ax.grid(axis='y', alpha=0.3)
        
        # 6. Request Distribution
        ax = axes[1, 2]
        x = np.arange(len(self. servers))
        width = 0.12
        for i, algo_name in enumerate(algo_names):
            requests = self.results[algo_name]['server_requests']
            offset = width * (i - len(algo_names)/2)
            ax.bar(x + offset, requests, width, label=algo_name)
        ax.set_xlabel('Server ID')
        ax.set_ylabel('Number of Requests')
        ax.set_title('Request Distribution Across Servers')
        ax.set_xticks(x)
        ax.legend(fontsize=8)
        ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('load_balancing_analysis.png', dpi=300, bbox_inches='tight')
        print("\nVisualization saved as 'load_balancing_analysis.png'")
        plt.show()


def main():
    """Main execution function"""
    print("Cloud Load Balancing Simulator")
    print("="*80)
    
    # Create simulator with 5 servers
    simulator = CloudLoadBalancerSimulator(num_servers=5, server_capacity_range=(50, 100))
    
    # Run simulations
    simulator.run_all_algorithms(num_requests=1000)
    
    # Print results
    simulator.print_results()
    
    # Visualize results
    simulator.visualize_results()


if __name__ == "__main__":
    main()