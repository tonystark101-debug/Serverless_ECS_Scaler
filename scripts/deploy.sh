#!/bin/bash

# Serverless ECS Scaler Deployment Script
# This script provides easy deployment options for different environments

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
STAGE="dev"
REGION="us-east-1"
CLUSTER=""
SERVICE=""
QUEUE=""
SCALE_UP_TARGET="1"
SCALE_DOWN_THRESHOLD="2"
VERBOSE=false

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Deploy the Serverless ECS Scaler to AWS

OPTIONS:
    -s, --stage STAGE           Deployment stage (dev, staging, prod) [default: dev]
    -r, --region REGION         AWS region [default: us-east-1]
    -c, --cluster CLUSTER       ECS cluster name (required)
    -S, --service SERVICE       ECS service name (required)
    -q, --queue QUEUE           SQS queue name (required)
    -u, --scale-up-target N     Target task count when scaling up [default: 1]
    -d, --scale-down-threshold N Minutes to wait before scaling down [default: 2]
    -v, --verbose               Enable verbose output
    -h, --help                  Show this help message

EXAMPLES:
    # Deploy to dev environment
    $0 --cluster my-cluster --service my-service --queue my-queue

    # Deploy to production with custom scaling
    $0 --stage prod --cluster prod-cluster --service prod-service --queue prod-queue --scale-up-target 5 --scale-down-threshold 3

    # Deploy to specific region
    $0 --region us-west-2 --cluster west-cluster --service west-service --queue west-queue

EOF
}

# Function to validate required parameters
validate_params() {
    if [[ -z "$CLUSTER" ]]; then
        print_error "ECS cluster name is required. Use --cluster option."
        exit 1
    fi
    
    if [[ -z "$SERVICE" ]]; then
        print_error "ECS service name is required. Use --service option."
        exit 1
    fi
    
    if [[ -z "$QUEUE" ]]; then
        print_error "SQS queue name is required. Use --queue option."
        exit 1
    fi
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if serverless is installed
    if ! command -v serverless &> /dev/null; then
        print_error "Serverless Framework is not installed. Please install it first:"
        echo "npm install -g serverless"
        exit 1
    fi
    
    # Check if AWS CLI is configured
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS CLI is not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    # Check if we're in the right directory
    if [[ ! -f "serverless.yml" ]]; then
        print_error "serverless.yml not found. Please run this script from the project root directory."
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Function to deploy
deploy() {
    print_status "Deploying to $STAGE environment in $REGION..."
    
    # Build deployment command
    DEPLOY_CMD="serverless deploy"
    DEPLOY_CMD="$DEPLOY_CMD --stage $STAGE"
    DEPLOY_CMD="$DEPLOY_CMD --region $REGION"
    DEPLOY_CMD="$DEPLOY_CMD --cluster $CLUSTER"
    DEPLOY_CMD="$DEPLOY_CMD --service $SERVICE"
    DEPLOY_CMD="$DEPLOY_CMD --queue $QUEUE"
    DEPLOY_CMD="$DEPLOY_CMD --scale-up-target $SCALE_UP_TARGET"
    DEPLOY_CMD="$DEPLOY_CMD --scale-down-threshold $SCALE_DOWN_THRESHOLD"
    
    if [[ "$VERBOSE" == true ]]; then
        DEPLOY_CMD="$DEPLOY_CMD --verbose"
    fi
    
    print_status "Running: $DEPLOY_CMD"
    
    # Execute deployment
    if eval $DEPLOY_CMD; then
        print_success "Deployment completed successfully!"
        print_status "Your ECS service '$SERVICE' in cluster '$CLUSTER' is now auto-scaling based on SQS queue '$QUEUE'"
        
        # Show useful information
        echo
        print_status "Useful commands:"
        echo "  # Monitor Lambda logs:"
        echo "  serverless logs -f ecsScaler --stage $STAGE --tail"
        echo
        echo "  # Check ECS service status:"
        echo "  aws ecs describe-services --cluster $CLUSTER --services $SERVICE --region $REGION"
        echo
        echo "  # Send test message to trigger scaling:"
        echo "  aws sqs send-message --queue-url \$(aws sqs get-queue-url --queue-name $QUEUE --region $REGION --output text) --message-body '{\"test\": \"message\"}'"
        
    else
        print_error "Deployment failed!"
        exit 1
    fi
}

# Function to remove deployment
remove() {
    print_status "Removing deployment from $STAGE environment in $REGION..."
    
    REMOVE_CMD="serverless remove"
    REMOVE_CMD="$REMOVE_CMD --stage $STAGE"
    REMOVE_CMD="$REMOVE_CMD --region $REGION"
    
    if [[ "$VERBOSE" == true ]]; then
        REMOVE_CMD="$REMOVE_CMD --verbose"
    fi
    
    print_status "Running: $REMOVE_CMD"
    
    if eval $REMOVE_CMD; then
        print_success "Removal completed successfully!"
    else
        print_error "Removal failed!"
        exit 1
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--stage)
            STAGE="$2"
            shift 2
            ;;
        -r|--region)
            REGION="$2"
            shift 2
            ;;
        -c|--cluster)
            CLUSTER="$2"
            shift 2
            ;;
        -S|--service)
            SERVICE="$2"
            shift 2
            ;;
        -q|--queue)
            QUEUE="$2"
            shift 2
            ;;
        -u|--scale-up-target)
            SCALE_UP_TARGET="$2"
            shift 2
            ;;
        -d|--scale-down-threshold)
            SCALE_DOWN_THRESHOLD="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --remove)
            REMOVE_MODE=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    print_status "Serverless ECS Scaler Deployment Script"
    echo
    
    # Validate parameters
    validate_params
    
    # Check prerequisites
    check_prerequisites
    
    # Deploy or remove
    if [[ "$REMOVE_MODE" == true ]]; then
        remove
    else
        deploy
    fi
}

# Run main function
main "$@"
