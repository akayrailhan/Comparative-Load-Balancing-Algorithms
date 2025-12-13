#!/bin/bash

echo "=== Quick Start:  Load Balancer with Kafka ==="
echo ""

# Install dependencies
echo "1. Installing dependencies..."
pip install -r requirements.txt

# Start Kafka with Docker
echo "2. Starting Kafka..."
docker-compose up -d

# Wait for services
echo "3. Waiting for Kafka to be ready (30 seconds)..."
sleep 30

# Verify setup
echo "4. Verifying Kafka topics..."
docker exec kafka kafka-topics --list --bootstrap-server localhost: 9092

# Start processor in background
echo "5. Starting load balancer processor..."
python kafka_load_balancer_integration.py --mode processor --algorithm least_connection &
PROC_PID=$!

sleep 5

# Generate requests
echo "6. Generating test requests..."
python kafka_load_balancer_integration.py --mode generator --num-requests 100 --rate 10.0

# Show results
echo ""
echo "✓ Setup complete!"
echo ""
echo "Access Kafka UI:  http://localhost:8080"
echo "Processor PID: $PROC_PID"
echo ""
echo "To stop:"
echo "  kill $PROC_PID"
echo "  docker-compose down"