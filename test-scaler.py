#!/usr/bin/env python3
"""
Test Script for Serverless ECS Scaler
This script helps test the ECS scaler functionality with real AWS services.
"""

import boto3
import json
import time
import sys
from datetime import datetime

def print_status(message):
    """Print a status message with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def get_ecs_service_status(ecs_client, cluster_name, service_name):
    """Get the current status of an ECS service."""
    try:
        response = ecs_client.describe_services(
            cluster=cluster_name,
            services=[service_name]
        )
        
        if response['services']:
            service = response['services'][0]
            return {
                'desired_count': service['desiredCount'],
                'running_count': service['runningCount'],
                'pending_count': service['pendingCount'],
                'status': service['status']
            }
        else:
            return None
    except Exception as e:
        print_status(f"Error getting ECS service status: {e}")
        return None

def get_sqs_queue_depth(sqs_client, queue_url):
    """Get the current depth of an SQS queue."""
    try:
        response = sqs_client.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=['ApproximateNumberOfMessages']
        )
        return int(response['Attributes']['ApproximateNumberOfMessages'])
    except Exception as e:
        print_status(f"Error getting SQS queue depth: {e}")
        return 0

def send_test_message(sqs_client, queue_url, message_body):
    """Send a test message to SQS queue."""
    try:
        response = sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message_body)
        )
        print_status(f"Sent test message: {response['MessageId']}")
        return response['MessageId']
    except Exception as e:
        print_status(f"Error sending test message: {e}")
        return None

def monitor_scaling(ecs_client, sqs_client, cluster_name, service_name, queue_url, duration_minutes=10):
    """Monitor the scaling behavior over time."""
    print_status(f"Starting scaling monitoring for {duration_minutes} minutes...")
    print_status(f"Cluster: {cluster_name}")
    print_status(f"Service: {service_name}")
    print_status(f"Queue: {queue_url}")
    print()
    
    start_time = time.time()
    end_time = start_time + (duration_minutes * 60)
    
    while time.time() < end_time:
        # Get current status
        ecs_status = get_ecs_service_status(ecs_client, cluster_name, service_name)
        queue_depth = get_sqs_queue_depth(sqs_client, queue_url)
        
        if ecs_status:
            print_status(f"ECS Service: {ecs_status['desired_count']} desired, {ecs_status['running_count']} running, {ecs_status['pending_count']} pending")
        else:
            print_status("ECS Service: Status unavailable")
        
        print_status(f"SQS Queue: {queue_depth} messages")
        print_status("-" * 50)
        
        time.sleep(30)  # Check every 30 seconds
    
    print_status("Monitoring completed!")

def run_scaling_test(ecs_client, sqs_client, cluster_name, service_name, queue_url):
    """Run a complete scaling test."""
    print_status("=== ECS Scaler Functional Test ===")
    print()
    
    # Step 1: Check initial state
    print_status("Step 1: Checking initial state...")
    initial_ecs = get_ecs_service_status(ecs_client, cluster_name, service_name)
    initial_queue = get_sqs_queue_depth(sqs_client, queue_url)
    
    if initial_ecs:
        print_status(f"Initial ECS state: {initial_ecs['desired_count']} desired, {initial_ecs['running_count']} running")
    print_status(f"Initial queue depth: {initial_queue}")
    print()
    
    # Step 2: Send test messages to trigger scale-up
    print_status("Step 2: Sending test messages to trigger scale-up...")
    for i in range(3):
        message = {
            'test_id': f'test-{i+1}',
            'timestamp': datetime.now().isoformat(),
            'message': f'Test message {i+1} for ECS scaling'
        }
        send_test_message(sqs_client, queue_url, message)
        time.sleep(2)
    
    print_status("Waiting for scale-up to occur...")
    time.sleep(60)  # Wait for Lambda to process and scale up
    
    # Step 3: Check scale-up state
    print_status("Step 3: Checking scale-up state...")
    scale_up_ecs = get_ecs_service_status(ecs_client, cluster_name, service_name)
    scale_up_queue = get_sqs_queue_depth(sqs_client, queue_url)
    
    if scale_up_ecs:
        print_status(f"Scale-up ECS state: {scale_up_ecs['desired_count']} desired, {scale_up_ecs['running_count']} running")
    print_status(f"Scale-up queue depth: {scale_up_queue}")
    print()
    
    # Step 4: Wait for tasks to complete and scale down
    print_status("Step 4: Waiting for tasks to complete and scale down...")
    print_status("This may take several minutes...")
    time.sleep(180)  # Wait for tasks to complete and scale down
    
    # Step 5: Check final state
    print_status("Step 5: Checking final state...")
    final_ecs = get_ecs_service_status(ecs_client, cluster_name, service_name)
    final_queue = get_sqs_queue_depth(sqs_client, queue_url)
    
    if final_ecs:
        print_status(f"Final ECS state: {final_ecs['desired_count']} desired, {final_ecs['running_count']} running")
    print_status(f"Final queue depth: {final_queue}")
    print()
    
    # Step 6: Analysis
    print_status("=== Test Analysis ===")
    if initial_ecs and scale_up_ecs and final_ecs:
        scale_up_worked = scale_up_ecs['desired_count'] > initial_ecs['desired_count']
        scale_down_worked = final_ecs['desired_count'] < scale_up_ecs['desired_count']
        
        print_status(f"Scale-up successful: {'✅ YES' if scale_up_worked else '❌ NO'}")
        print_status(f"Scale-down successful: {'✅ YES' if scale_down_worked else '❌ NO'}")
        
        if scale_up_worked and scale_down_worked:
            print_status("🎉 ECS Scaler is working correctly!")
        else:
            print_status("⚠️  ECS Scaler may have issues. Check CloudWatch logs.")
    else:
        print_status("❌ Could not determine test results. Check AWS console.")

def main():
    """Main test function."""
    # Configuration
    cluster_name = "test-ecs-scaler-cluster"
    service_name = "test-ecs-scaler-service"
    queue_name = "test-ecs-scaler-queue"
    
    # Initialize AWS clients
    try:
        ecs_client = boto3.client('ecs')
        sqs_client = boto3.client('sqs')
    except Exception as e:
        print_status(f"Error initializing AWS clients: {e}")
        print_status("Make sure you have AWS credentials configured.")
        sys.exit(1)
    
    # Get queue URL
    try:
        response = sqs_client.get_queue_url(QueueName=queue_name)
        queue_url = response['QueueUrl']
    except Exception as e:
        print_status(f"Error getting queue URL: {e}")
        print_status("Make sure the test infrastructure is deployed.")
        sys.exit(1)
    
    print_status("AWS clients initialized successfully")
    print_status(f"Queue URL: {queue_url}")
    print()
    
    # Ask user what to do
    print("What would you like to do?")
    print("1. Run complete scaling test")
    print("2. Monitor scaling behavior")
    print("3. Send test messages")
    print("4. Check current status")
    
    choice = input("Enter your choice (1-4): ").strip()
    
    if choice == "1":
        run_scaling_test(ecs_client, sqs_client, cluster_name, service_name, queue_url)
    elif choice == "2":
        duration = input("Enter monitoring duration in minutes (default: 10): ").strip()
        duration = int(duration) if duration.isdigit() else 10
        monitor_scaling(ecs_client, sqs_client, cluster_name, service_name, queue_url, duration)
    elif choice == "3":
        count = input("Enter number of test messages to send (default: 5): ").strip()
        count = int(count) if count.isdigit() else 5
        
        for i in range(count):
            message = {
                'test_id': f'manual-test-{i+1}',
                'timestamp': datetime.now().isoformat(),
                'message': f'Manual test message {i+1}'
            }
            send_test_message(sqs_client, queue_url, message)
            time.sleep(1)
    elif choice == "4":
        ecs_status = get_ecs_service_status(ecs_client, cluster_name, service_name)
        queue_depth = get_sqs_queue_depth(sqs_client, queue_url)
        
        if ecs_status:
            print_status(f"ECS Service Status:")
            print_status(f"  Desired: {ecs_status['desired_count']}")
            print_status(f"  Running: {ecs_status['running_count']}")
            print_status(f"  Pending: {ecs_status['pending_count']}")
            print_status(f"  Status: {ecs_status['status']}")
        else:
            print_status("ECS Service: Status unavailable")
        
        print_status(f"SQS Queue Depth: {queue_depth}")
    else:
        print_status("Invalid choice. Exiting.")

if __name__ == "__main__":
    main()
