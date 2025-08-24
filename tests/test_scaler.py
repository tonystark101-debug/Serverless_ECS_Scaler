"""
Unit tests for the ECS Scaler Lambda function.
"""

import json
import os
import pytest
import unittest.mock as mock
from unittest.mock import patch, MagicMock

# Import the module to test
import sys
sys.path.append('../src')
from src.scaler import (
    get_queue_depth,
    get_current_task_count,
    scale_service,
    should_scale_up,
    should_scale_down,
    lambda_handler
)


class TestScaler:
    
    @patch('src.scaler.sqs_client')
    def test_get_queue_depth_success(self, mock_sqs):
        """Test successful queue depth retrieval."""
        mock_sqs.get_queue_attributes.return_value = {
            'Attributes': {
                'ApproximateNumberOfMessagesVisible': '5'
            }
        }
        
        result = get_queue_depth()
        assert result == 5
        mock_sqs.get_queue_attributes.assert_called_once()

    @patch('src.scaler.sqs_client')
    def test_get_queue_depth_failure(self, mock_sqs):
        """Test queue depth retrieval failure."""
        mock_sqs.get_queue_attributes.side_effect = Exception("SQS Error")
        
        with pytest.raises(Exception):
            get_queue_depth()

    @patch('src.scaler.ecs_client')
    def test_get_current_task_count_success(self, mock_ecs):
        """Test successful task count retrieval."""
        mock_ecs.describe_services.return_value = {
            'services': [{
                'runningCount': 3
            }]
        }
        
        result = get_current_task_count()
        assert result == 3
        mock_ecs.describe_services.assert_called_once()

    @patch('src.scaler.ecs_client')
    def test_get_current_task_count_service_not_found(self, mock_ecs):
        """Test task count retrieval when service doesn't exist."""
        mock_ecs.describe_services.return_value = {
            'services': []
        }
        
        with pytest.raises(ValueError):
            get_current_task_count()

    @patch('src.scaler.ecs_client')
    @patch('src.scaler.get_current_task_count')
    def test_scale_service_success(self, mock_get_count, mock_ecs):
        """Test successful service scaling."""
        mock_get_count.return_value = 0
        mock_ecs.update_service.return_value = {}
        
        result = scale_service(2)
        assert result is True
        mock_ecs.update_service.assert_called_once()

    @patch('src.scaler.get_current_task_count')
    def test_scale_service_no_change_needed(self, mock_get_count):
        """Test scaling when service is already at desired count."""
        mock_get_count.return_value = 2
        
        result = scale_service(2)
        assert result is True

    @patch.dict(os.environ, {
        'SQS_QUEUE_URL': 'test-queue-url',
        'ECS_CLUSTER_NAME': 'test-cluster',
        'ECS_SERVICE_NAME': 'test-service',
        'SCALE_UP_TARGET': '2'
    })
    def test_should_scale_up(self):
        """Test scale-up decision logic."""
        # Should scale up: queue has messages, current tasks < target
        assert should_scale_up(queue_depth=5, current_tasks=0) is True
        
        # Should not scale up: queue empty
        assert should_scale_up(queue_depth=0, current_tasks=0) is False
        
        # Should not scale up: already at target (target is 2 from env)
        assert should_scale_up(queue_depth=5, current_tasks=2) is False

    def test_should_scale_down(self):
        """Test scale-down decision logic."""
        # Should scale down: queue empty, has running tasks
        assert should_scale_down(queue_depth=0, current_tasks=2) is True
        
        # Should not scale down: queue has messages
        assert should_scale_down(queue_depth=5, current_tasks=2) is False
        
        # Should not scale down: already at zero
        assert should_scale_down(queue_depth=0, current_tasks=0) is False

    @patch.dict(os.environ, {
        'SQS_QUEUE_URL': 'test-queue-url',
        'ECS_CLUSTER_NAME': 'test-cluster',
        'ECS_SERVICE_NAME': 'test-service',
        'SCALE_UP_TARGET': '2'
    })
    @patch('src.scaler.get_queue_depth')
    @patch('src.scaler.get_current_task_count')
    @patch('src.scaler.scale_service')
    def test_lambda_handler_scale_up(self, mock_scale, mock_get_tasks, mock_get_queue):
        """Test Lambda handler scale-up scenario."""
        mock_get_queue.return_value = 5
        mock_get_tasks.return_value = 0
        mock_scale.return_value = True
        
        event = {'Records': [{'eventSource': 'aws:sqs'}]}
        result = lambda_handler(event, None)
        
        assert result['statusCode'] == 200
        assert result['body']['action_taken'] == 'scale_up'
        mock_scale.assert_called_once_with(2, 0)

    @patch.dict(os.environ, {
        'SQS_QUEUE_URL': 'test-queue-url',
        'ECS_CLUSTER_NAME': 'test-cluster',
        'ECS_SERVICE_NAME': 'test-service'
    })
    @patch('src.scaler.get_queue_depth')
    @patch('src.scaler.get_current_task_count')
    @patch('src.scaler.scale_service')
    def test_lambda_handler_scale_down(self, mock_scale, mock_get_tasks, mock_get_queue):
        """Test Lambda handler scale-down scenario."""
        mock_get_queue.return_value = 0
        mock_get_tasks.return_value = 2
        mock_scale.return_value = True
        
        event = {'source': 'aws.events'}
        result = lambda_handler(event, None)
        
        assert result['statusCode'] == 200
        assert result['body']['action_taken'] == 'scale_down'
        mock_scale.assert_called_once_with(0, 2)

    @patch.dict(os.environ, {
        'SQS_QUEUE_URL': 'test-queue-url',
        'ECS_CLUSTER_NAME': 'test-cluster',
        'ECS_SERVICE_NAME': 'test-service'
    })
    @patch('src.scaler.get_queue_depth')
    @patch('src.scaler.get_current_task_count')
    def test_lambda_handler_no_action(self, mock_get_tasks, mock_get_queue):
        """Test Lambda handler when no scaling action is needed."""
        mock_get_queue.return_value = 0
        mock_get_tasks.return_value = 0
        
        event = {'source': 'aws.events'}
        result = lambda_handler(event, None)
        
        assert result['statusCode'] == 200
        assert result['body']['action_taken'] == 'none'

    @patch.dict(os.environ, {
        'SQS_QUEUE_URL': 'test-queue-url',
        'ECS_CLUSTER_NAME': 'test-cluster',
        'ECS_SERVICE_NAME': 'test-service'
    })
    @patch('src.scaler.get_queue_depth')
    def test_lambda_handler_error(self, mock_get_queue):
        """Test Lambda handler error handling."""
        mock_get_queue.side_effect = Exception("Test error")
        
        event = {'source': 'aws.events'}
        result = lambda_handler(event, None)
        
        assert result['statusCode'] == 500
        assert 'error' in result['body']


if __name__ == '__main__':
    pytest.main([__file__])

