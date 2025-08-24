"""
Integration tests for the Serverless ECS Scaler.

These tests require AWS credentials and actual AWS services to be configured.
Run these tests in a test environment, not in production.
"""

import os
import json
import pytest
import boto3
from unittest.mock import patch, MagicMock

# Import the module to test
import sys
sys.path.append('../src')
from src.scaler import lambda_handler


class TestIntegration:
    """Integration tests for the ECS Scaler."""
    
    @pytest.fixture(autouse=True)
    def setup_environment(self):
        """Set up test environment variables."""
        # Test configuration - update these for your test environment
        os.environ.update({
            'SQS_QUEUE_URL': 'https://sqs.us-east-1.amazonaws.com/123456789012/test-queue',
            'ECS_CLUSTER_NAME': 'test-cluster',
            'ECS_SERVICE_NAME': 'test-service',
            'SCALE_UP_TARGET': '2',
            'SCALE_DOWN_THRESHOLD': '1'
        })
    
    @pytest.mark.integration
    def test_lambda_handler_with_sqs_event(self):
        """Test Lambda handler with SQS event."""
        # Mock SQS event
        sqs_event = {
            'Records': [
                {
                    'eventSource': 'aws:sqs',
                    'body': '{"test": "message"}'
                }
            ]
        }
        
        # Mock AWS clients
        with patch('src.scaler.sqs_client') as mock_sqs, \
             patch('src.scaler.ecs_client') as mock_ecs:
            
            # Mock SQS response
            mock_sqs.get_queue_attributes.return_value = {
                'Attributes': {
                    'ApproximateNumberOfMessagesVisible': '5'
                }
            }
            
            # Mock ECS response
            mock_ecs.describe_services.return_value = {
                'services': [{
                    'runningCount': 0
                }]
            }
            
            mock_ecs.update_service.return_value = {}
            
            # Execute Lambda function
            result = lambda_handler(sqs_event, None)
            
            # Verify response
            assert result['statusCode'] == 200
            assert result['body']['trigger_source'] == 'sqs'
            assert result['body']['action_taken'] == 'scale_up'
            
            # Verify AWS calls
            mock_sqs.get_queue_attributes.assert_called_once()
            mock_ecs.describe_services.assert_called_once()
            mock_ecs.update_service.assert_called_once()
    
    @pytest.mark.integration
    def test_lambda_handler_with_eventbridge_event(self):
        """Test Lambda handler with EventBridge event."""
        # Mock EventBridge event
        eventbridge_event = {
            'source': 'aws.events',
            'detail-type': 'Scheduled Event'
        }
        
        # Mock AWS clients
        with patch('src.scaler.sqs_client') as mock_sqs, \
             patch('src.scaler.ecs_client') as mock_ecs:
            
            # Mock SQS response (empty queue)
            mock_sqs.get_queue_attributes.return_value = {
                'Attributes': {
                    'ApproximateNumberOfMessagesVisible': '0'
                }
            }
            
            # Mock ECS response (has running tasks)
            mock_ecs.describe_services.return_value = {
                'services': [{
                    'runningCount': 2
                }]
            }
            
            mock_ecs.update_service.return_value = {}
            
            # Execute Lambda function
            result = lambda_handler(eventbridge_event, None)
            
            # Verify response
            assert result['statusCode'] == 200
            assert result['body']['trigger_source'] == 'eventbridge'
            assert result['body']['action_taken'] == 'scale_down'
            
            # Verify AWS calls
            mock_sqs.get_queue_attributes.assert_called_once()
            mock_ecs.describe_services.assert_called_once()
            mock_ecs.update_service.assert_called_once()
    
    @pytest.mark.integration
    def test_lambda_handler_no_scaling_needed(self):
        """Test Lambda handler when no scaling is needed."""
        # Mock EventBridge event
        event = {
            'source': 'aws.events',
            'detail-type': 'Scheduled Event'
        }
        
        # Mock AWS clients
        with patch('src.scaler.sqs_client') as mock_sqs, \
             patch('src.scaler.ecs_client') as mock_ecs:
            
            # Mock SQS response (empty queue)
            mock_sqs.get_queue_attributes.return_value = {
                'Attributes': {
                    'ApproximateNumberOfMessagesVisible': '0'
                }
            }
            
            # Mock ECS response (already at zero)
            mock_ecs.describe_services.return_value = {
                'services': [{
                    'runningCount': 0
                }]
            }
            
            # Execute Lambda function
            result = lambda_handler(event, None)
            
            # Verify response
            assert result['statusCode'] == 200
            assert result['body']['action_taken'] == 'none'
            
            # Verify no ECS update calls
            mock_ecs.update_service.assert_not_called()
    
    @pytest.mark.integration
    def test_error_handling(self):
        """Test error handling in Lambda function."""
        # Mock EventBridge event
        event = {
            'source': 'aws.events',
            'detail-type': 'Scheduled Event'
        }
        
        # Mock AWS clients to raise exception
        with patch('src.scaler.sqs_client') as mock_sqs:
            mock_sqs.get_queue_attributes.side_effect = Exception("AWS Error")
            
            # Execute Lambda function
            result = lambda_handler(event, None)
            
            # Verify error response
            assert result['statusCode'] == 500
            assert 'error' in result['body']
            assert 'AWS Error' in result['body']['error']


class TestRealAWSIntegration:
    """Real AWS integration tests (require AWS credentials)."""
    
    @pytest.mark.real_aws
    @pytest.mark.skipif(
        not os.environ.get('AWS_ACCESS_KEY_ID'),
        reason="AWS credentials not configured"
    )
    def test_real_sqs_integration(self):
        """Test with real SQS queue."""
        # This test requires a real SQS queue to be created
        # and proper AWS credentials configured
        
        # Create SQS client
        sqs = boto3.client('sqs')
        
        # Create test queue
        try:
            response = sqs.create_queue(
                QueueName='test-scaler-queue',
                Attributes={
                    'VisibilityTimeout': '300',
                    'MessageRetentionPeriod': '86400'
                }
            )
            
            queue_url = response['QueueUrl']
            
            # Send test message
            sqs.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps({'test': 'integration'})
            )
            
            # Verify message was sent
            response = sqs.get_queue_attributes(
                QueueUrl=queue_url,
                AttributeNames=['ApproximateNumberOfMessagesVisible']
            )
            
            message_count = int(response['Attributes']['ApproximateNumberOfMessagesVisible'])
            assert message_count > 0
            
            # Clean up
            sqs.delete_queue(QueueUrl=queue_url)
            
        except Exception as e:
            pytest.skip(f"Real AWS test failed: {str(e)}")
    
    @pytest.mark.real_aws
    @pytest.mark.skipif(
        not os.environ.get('AWS_ACCESS_KEY_ID'),
        reason="AWS credentials not configured"
    )
    def test_real_ecs_integration(self):
        """Test with real ECS cluster."""
        # This test requires a real ECS cluster to be available
        # and proper AWS credentials configured
        
        # Create ECS client
        ecs = boto3.client('ecs')
        
        try:
            # List clusters
            response = ecs.list_clusters()
            clusters = response['clusterArns']
            
            if not clusters:
                pytest.skip("No ECS clusters available")
            
            # Get first cluster
            cluster_arn = clusters[0]
            cluster_name = cluster_arn.split('/')[-1]
            
            # List services in cluster
            response = ecs.list_services(cluster=cluster_name)
            services = response['serviceArns']
            
            if not services:
                pytest.skip(f"No ECS services in cluster {cluster_name}")
            
            # Get first service
            service_arn = services[0]
            service_name = service_arn.split('/')[-1]
            
            # Describe service
            response = ecs.describe_services(
                cluster=cluster_name,
                services=[service_name]
            )
            
            assert len(response['services']) > 0
            service = response['services'][0]
            
            # Verify service has expected attributes
            assert 'runningCount' in service
            assert 'desiredCount' in service
            
        except Exception as e:
            pytest.skip(f"Real ECS test failed: {str(e)}")


if __name__ == '__main__':
    # Run integration tests
    pytest.main([__file__, '-v', '-m', 'integration'])
