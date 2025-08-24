#!/usr/bin/env python3
"""
Automated ECS Scaler Test Suite
Tests the serverless-ecs-scaler with real AWS services automatically.
"""

import boto3
import time
import json
import random
import string
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ECSScalerTester:
    def __init__(self):
        """Initialize AWS clients and configuration."""
        self.ecs_client = boto3.client('ecs')
        self.sqs_client = boto3.client('sqs')
        self.logs_client = boto3.client('logs')
        
        # Test configuration
        self.cluster_name = 'test-ecs-scaler-cluster'
        self.service_name = 'test-ecs-scaler-service'
        self.queue_url = None
        self.test_results = []
        
        # Get queue URL
        try:
            response = self.sqs_client.list_queues(QueueNamePrefix='test-ecs-scaler-queue')
            if response['QueueUrls']:
                self.queue_url = response['QueueUrls'][0]
                logger.info(f"Using queue: {self.queue_url}")
            else:
                raise Exception("Test queue not found")
        except Exception as e:
            logger.error(f"Failed to get queue URL: {e}")
            raise

    def get_ecs_status(self):
        """Get current ECS service status."""
        try:
            response = self.ecs_client.describe_services(
                cluster=self.cluster_name,
                services=[self.service_name]
            )
            service = response['services'][0]
            return {
                'desired': service['desiredCount'],
                'running': service['runningCount'],
                'pending': service['pendingCount'],
                'status': service['status']
            }
        except Exception as e:
            logger.error(f"Failed to get ECS status: {e}")
            return None

    def get_queue_depth(self):
        """Get current SQS queue depth."""
        try:
            response = self.sqs_client.get_queue_attributes(
                QueueUrl=self.queue_url,
                AttributeNames=['ApproximateNumberOfMessages']
            )
            return int(response['Attributes']['ApproximateNumberOfMessages'])
        except Exception as e:
            logger.error(f"Failed to get queue depth: {e}")
            return 0

    def send_test_message(self, message_type="test"):
        """Send a test message to SQS."""
        try:
            message_body = {
                'id': ''.join(random.choices(string.ascii_lowercase + string.digits, k=8)),
                'type': message_type,
                'timestamp': datetime.utcnow().isoformat(),
                'data': f"Automated test message {message_type}"
            }
            
            response = self.sqs_client.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(message_body)
            )
            
            logger.info(f"Sent {message_type} message: {response['MessageId']}")
            return response['MessageId']
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return None

    def wait_for_ecs_change(self, expected_desired, timeout=120, check_interval=5):
        """Wait for ECS service to reach expected state."""
        start_time = time.time()
        logger.info(f"Waiting for ECS to reach {expected_desired} desired tasks...")
        
        while time.time() - start_time < timeout:
            status = self.get_ecs_status()
            if status and status['desired'] == expected_desired:
                logger.info(f"ECS reached target: {expected_desired} desired tasks")
                return True
            
            time.sleep(check_interval)
            logger.info(f"Current: {status['desired']} desired, {status['running']} running, {status['pending']} pending")
        
        logger.warning(f"Timeout waiting for ECS to reach {expected_desired} tasks")
        return False

    def run_scaling_test(self, test_name, messages_count=3, expected_scale_up=2):
        """Run a complete scaling test cycle."""
        logger.info(f"\n{'='*50}")
        logger.info(f"Running Test: {test_name}")
        logger.info(f"{'='*50}")
        
        test_result = {
            'test_name': test_name,
            'start_time': datetime.utcnow(),
            'success': False,
            'scale_up_time': None,
            'scale_down_time': None,
            'errors': []
        }
        
        try:
            # Step 1: Verify initial state (0 tasks)
            initial_status = self.get_ecs_status()
            if not initial_status or initial_status['desired'] != 0:
                test_result['errors'].append(f"Initial state not 0 tasks: {initial_status}")
                return test_result
            
            logger.info(f"Initial state: {initial_status['desired']} desired, {initial_status['running']} running")
            
            # Step 2: Send messages to trigger scale-up
            logger.info(f"Sending {messages_count} test messages...")
            message_ids = []
            for i in range(messages_count):
                msg_id = self.send_test_message(f"scale_up_{i}")
                if msg_id:
                    message_ids.append(msg_id)
                time.sleep(1)  # Small delay between messages
            
            # Step 3: Wait for scale-up
            scale_up_start = time.time()
            if self.wait_for_ecs_change(expected_scale_up, timeout=60):
                test_result['scale_up_time'] = time.time() - scale_up_start
                logger.info(f"✅ Scale-up successful in {test_result['scale_up_time']:.1f}s")
            else:
                test_result['errors'].append("Scale-up failed or timed out")
                return test_result
            
            # Step 4: Wait for scale-down (EventBridge will trigger after tasks complete)
            logger.info("Waiting for scale-down (EventBridge trigger)...")
            scale_down_start = time.time()
            if self.wait_for_ecs_change(0, timeout=180):
                test_result['scale_down_time'] = time.time() - scale_down_start
                logger.info(f"✅ Scale-down successful in {test_result['scale_down_time']:.1f}s")
            else:
                test_result['errors'].append("Scale-down failed or timed out")
                return test_result
            
            # Step 5: Verify final state
            final_status = self.get_ecs_status()
            if final_status and final_status['desired'] == 0:
                test_result['success'] = True
                logger.info("✅ Test completed successfully!")
            else:
                test_result['errors'].append(f"Final state not 0 tasks: {final_status}")
            
        except Exception as e:
            test_result['errors'].append(f"Test execution error: {str(e)}")
            logger.error(f"Test execution error: {e}")
        
        test_result['end_time'] = datetime.utcnow()
        test_result['duration'] = (test_result['end_time'] - test_result['start_time']).total_seconds()
        
        return test_result

    def run_load_test(self, duration_minutes=2, message_interval=10):
        """Run a load test with continuous message sending."""
        logger.info(f"\n{'='*50}")
        logger.info(f"Running Load Test: {duration_minutes} minutes, {message_interval}s interval")
        logger.info(f"{'='*50}")
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        message_count = 0
        
        try:
            while time.time() < end_time:
                # Send message
                msg_id = self.send_test_message("load_test")
                if msg_id:
                    message_count += 1
                
                # Check ECS status
                status = self.get_ecs_status()
                logger.info(f"Message {message_count}: ECS {status['desired']} desired, {status['running']} running")
                
                # Wait for next message
                time.sleep(message_interval)
            
            logger.info(f"Load test completed: {message_count} messages sent")
            
        except Exception as e:
            logger.error(f"Load test error: {e}")

    def run_comprehensive_test_suite(self):
        """Run all tests and generate report."""
        logger.info("🚀 Starting Comprehensive ECS Scaler Test Suite")
        logger.info(f"Cluster: {self.cluster_name}")
        logger.info(f"Service: {self.service_name}")
        logger.info(f"Queue: {self.queue_url}")
        
        # Test 1: Basic scaling cycle
        test1 = self.run_scaling_test("Basic Scaling Cycle", messages_count=1, expected_scale_up=2)
        self.test_results.append(test1)
        
        # Wait between tests
        time.sleep(30)
        
        # Test 2: Multiple messages scaling
        test2 = self.run_scaling_test("Multiple Messages Scaling", messages_count=3, expected_scale_up=2)
        self.test_results.append(test2)
        
        # Wait between tests
        time.sleep(30)
        
        # Test 3: Load test
        self.run_load_test(duration_minutes=1, message_interval=15)
        
        # Generate final report
        self.generate_test_report()

    def generate_test_report(self):
        """Generate comprehensive test report."""
        logger.info(f"\n{'='*60}")
        logger.info("📊 TEST RESULTS SUMMARY")
        logger.info(f"{'='*60}")
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests} ✅")
        logger.info(f"Failed: {failed_tests} ❌")
        logger.info(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        for i, result in enumerate(self.test_results, 1):
            logger.info(f"\nTest {i}: {result['test_name']}")
            if result['success']:
                logger.info(f"  ✅ Status: PASSED")
                logger.info(f"  ⏱️  Scale-up: {result['scale_up_time']:.1f}s")
                logger.info(f"  ⏱️  Scale-down: {result['scale_down_time']:.1f}s")
                logger.info(f"  ⏱️  Total Duration: {result['duration']:.1f}s")
            else:
                logger.info(f"  ❌ Status: FAILED")
                for error in result['errors']:
                    logger.info(f"  🔴 Error: {error}")
        
        # Overall assessment
        if passed_tests == total_tests:
            logger.info(f"\n🎉 ALL TESTS PASSED! ECS Scaler is working perfectly!")
        elif passed_tests > 0:
            logger.info(f"\n⚠️  PARTIAL SUCCESS: {passed_tests}/{total_tests} tests passed")
        else:
            logger.info(f"\n❌ ALL TESTS FAILED: ECS Scaler needs attention")

def main():
    """Main function to run the automated test suite."""
    try:
        tester = ECSScalerTester()
        tester.run_comprehensive_test_suite()
        
    except Exception as e:
        logger.error(f"Test suite failed to start: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
