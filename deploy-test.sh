#!/bin/bash

# Test Deployment Script for Serverless ECS Scaler
# This script deploys the test infrastructure and ECS scaler

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Check prerequisites
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
    if [[ ! -f "test-deployment.yml" ]]; then
        print_error "test-deployment.yml not found. Please run this script from the project root directory."
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Deploy test infrastructure
deploy_test() {
    print_status "Deploying test infrastructure..."
    
    # Deploy using the test configuration
    if serverless deploy --config test-deployment.yml --verbose; then
        print_success "Test infrastructure deployed successfully!"
        
        # Get deployment info
        print_status "Getting deployment information..."
        serverless info --config test-deployment.yml
        
        print_status ""
        print_status "🎉 Test deployment completed!"
        print_status ""
        print_status "Next steps:"
        print_status "1. Run the test script: python test-scaler.py"
        print_status "2. Monitor the scaling behavior"
        print_status "3. Check CloudWatch logs for the Lambda function"
        print_status "4. Clean up when done: ./cleanup-test.sh"
        
    else
        print_error "Test deployment failed!"
        exit 1
    fi
}

# Remove test infrastructure
remove_test() {
    print_status "Removing test infrastructure..."
    
    if serverless remove --config test-deployment.yml --verbose; then
        print_success "Test infrastructure removed successfully!"
    else
        print_error "Test infrastructure removal failed!"
        exit 1
    fi
}

# Show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Deploy or remove the test infrastructure for Serverless ECS Scaler

OPTIONS:
    deploy      Deploy test infrastructure
    remove      Remove test infrastructure
    -h, --help  Show this help message

EXAMPLES:
    # Deploy test infrastructure
    $0 deploy

    # Remove test infrastructure
    $0 remove

EOF
}

# Main execution
main() {
    print_status "Serverless ECS Scaler - Test Deployment Script"
    echo
    
    case "${1:-}" in
        deploy)
            check_prerequisites
            deploy_test
            ;;
        remove)
            check_prerequisites
            remove_test
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: ${1:-}"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
