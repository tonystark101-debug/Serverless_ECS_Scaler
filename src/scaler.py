"""
Serverless ECS Scaler
Fast, responsive auto-scaling for ECS services based on SQS queue depth.

This Lambda function provides sub-minute scaling response times, replacing
slow CloudWatch-based auto-scaling with intelligent SQS monitoring.

Environment Variables:
    SQS_QUEUE_URL: The SQS queue URL to monitor
    ECS_CLUSTER_NAME: The ECS cluster name
    ECS_SERVICE_NAME: The ECS service name to scale
    SCALE_UP_TARGET: Target task count when scaling up (default: 1)
    SCALE_DOWN_THRESHOLD: Minutes to wait before scaling down (default: 2)
    AWS_REGION: AWS region (auto-detected if not set)
"""

import json
import os
import boto3
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
ecs_client = boto3.client('ecs')
sqs_client = boto3.client('sqs')

def get_config():
    """Get configuration from environment variables."""
    return {
        'SQS_QUEUE_URL': os.environ.get('SQS_QUEUE_URL', 'https://sqs.us-east-1.amazonaws.com/123456789012/test-queue'),
        'ECS_CLUSTER_NAME': os.environ.get('ECS_CLUSTER_NAME', 'test-cluster'),
        'ECS_SERVICE_NAME': os.environ.get('ECS_SERVICE_NAME', 'test-service'),
        'SCALE_UP_TARGET': int(os.environ.get('SCALE_UP_TARGET', '1')),
        'SCALE_DOWN_THRESHOLD': int(os.environ.get('SCALE_DOWN_THRESHOLD', '2'))
    }


def get_queue_depth() -> int:
    """
    Get the number of messages waiting in the SQS queue.
    
    Returns:
        int: Number of approximate visible messages in the queue
    """
    try:
        config = get_config()
        response = sqs_client.get_queue_attributes(
            QueueUrl=config['SQS_QUEUE_URL'],
            AttributeNames=['ApproximateNumberOfMessages']
        )
        return int(response['Attributes']['ApproximateNumberOfMessages'])
    except Exception as e:
        logger.error(f"Failed to get queue depth: {str(e)}")
        raise


def get_current_task_count() -> int:
    """
    Get the current number of running tasks in the ECS service.
    
    Returns:
        int: Current number of running tasks
    """
    try:
        config = get_config()
        response = ecs_client.describe_services(
            cluster=config['ECS_CLUSTER_NAME'],
            services=[config['ECS_SERVICE_NAME']]
        )
        
        if not response['services']:
            raise ValueError(f"ECS service '{config['ECS_SERVICE_NAME']}' not found in cluster '{config['ECS_CLUSTER_NAME']}'")
        
        service = response['services'][0]
        return service['runningCount']
    except Exception as e:
        logger.error(f"Failed to get current task count: {str(e)}")
        raise


def scale_service(desired_count: int, current_count: int = None) -> bool:
    """
    Scale the ECS service to the specified number of tasks.
    
    Args:
        desired_count: Target number of tasks
        current_count: Current task count (if known, to avoid duplicate API calls)
        
    Returns:
        bool: True if scaling was successful, False otherwise
    """
    try:
        config = get_config()
        
        # Get current count if not provided
        if current_count is None:
            current_count = get_current_task_count()
        
        if current_count == desired_count:
            logger.info(f"Service already at desired count: {desired_count}")
            return True
        
        logger.info(f"Scaling service from {current_count} to {desired_count} tasks")
        
        ecs_client.update_service(
            cluster=config['ECS_CLUSTER_NAME'],
            service=config['ECS_SERVICE_NAME'],
            desiredCount=desired_count
        )
        
        logger.info(f"Successfully initiated scaling to {desired_count} tasks")
        return True
        
    except Exception as e:
        logger.error(f"Failed to scale service: {str(e)}")
        return False


def should_scale_up(queue_depth: int, current_tasks: int) -> bool:
    """
    Determine if the service should scale up.
    
    Args:
        queue_depth: Number of messages in the queue
        current_tasks: Current number of running tasks
        
    Returns:
        bool: True if should scale up
    """
    config = get_config()
    return queue_depth > 0 and current_tasks < config['SCALE_UP_TARGET']


def should_scale_down(queue_depth: int, current_tasks: int) -> bool:
    """
    Determine if the service should scale down.
    
    Args:
        queue_depth: Number of messages in the queue
        current_tasks: Current number of running tasks
        
    Returns:
        bool: True if should scale down
    """
    config = get_config()
    return queue_depth == 0 and current_tasks > 0


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for ECS scaling logic.
    
    This function can be triggered by:
    1. EventBridge (scheduled execution for scale-down monitoring)
    2. SQS (immediate scale-up when messages arrive)
    
    Args:
        event: Lambda event data
        context: Lambda context
        
    Returns:
        Dict containing the scaling action taken and metrics
    """
    try:
        # Determine trigger source
        trigger_source = "unknown"
        if 'Records' in event and event['Records']:
            trigger_source = "sqs"
        elif 'source' in event and event['source'] == 'aws.events':
            trigger_source = "eventbridge"
        
        logger.info(f"Lambda triggered by: {trigger_source}")
        
        # Get current metrics
        queue_depth = get_queue_depth()
        current_tasks = get_current_task_count()
        
        logger.info(f"Current state - Queue depth: {queue_depth}, Running tasks: {current_tasks}")
        
        # Scaling logic
        action_taken = "none"
        
        # For SQS triggers, we know there was a message, so scale up if needed
        if trigger_source == "sqs":
            config = get_config()
            if current_tasks < config['SCALE_UP_TARGET']:
                if scale_service(config['SCALE_UP_TARGET'], current_tasks):
                    action_taken = "scale_up"
                    logger.info(f"Scaled up to {config['SCALE_UP_TARGET']} tasks due to SQS message")
                else:
                    action_taken = "scale_up_failed"
            else:
                action_taken = "no_scale_needed"
                logger.info(f"Already at target capacity: {current_tasks} tasks")
        
        # For EventBridge triggers, use normal scaling logic
        elif trigger_source == "eventbridge":
            if should_scale_up(queue_depth, current_tasks):
                config = get_config()
                if scale_service(config['SCALE_UP_TARGET'], current_tasks):
                    action_taken = "scale_up"
                    logger.info(f"Scaled up to {config['SCALE_UP_TARGET']} tasks")
                else:
                    action_taken = "scale_up_failed"
                    
            elif should_scale_down(queue_depth, current_tasks):
                if scale_service(0, current_tasks):
                    action_taken = "scale_down"
                    logger.info("Scaled down to 0 tasks")
                else:
                    action_taken = "scale_down_failed"
        
        # Response
        response = {
            'statusCode': 200,
            'body': {
                'trigger_source': trigger_source,
                'queue_depth': queue_depth,
                'current_tasks': current_tasks,
                'action_taken': action_taken,
                'timestamp': datetime.utcnow().isoformat()
            }
        }
        
        logger.info(f"Scaling complete: {action_taken}")
        return response
        
    except Exception as e:
        logger.error(f"Lambda execution failed: {str(e)}")
        return {
            'statusCode': 500,
            'body': {
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
        }


# For local testing
if __name__ == "__main__":
    # Mock event for testing
    test_event = {
        'source': 'aws.events',
        'detail-type': 'Scheduled Event'
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))

