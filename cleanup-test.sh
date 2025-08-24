#!/bin/bash

# Cleanup Script for Serverless ECS Scaler Test
# This script removes the test infrastructure

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

# Check if user really wants to clean up
confirm_cleanup() {
    print_warning "⚠️  WARNING: This will remove ALL test infrastructure!"
    print_warning "This includes:"
    print_warning "  - ECS Cluster and Service"
    print_warning "  - SQS Queues"
    print_warning "  - Lambda Function"
    print_warning "  - VPC and Network Resources"
    print_warning "  - IAM Roles"
    print_warning "  - CloudWatch Log Groups"
    echo
    read -p "Are you sure you want to continue? (yes/no): " -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        print_status "Cleanup cancelled."
        exit 0
    fi
}

# Clean up test infrastructure
cleanup_test() {
    print_status "Starting cleanup of test infrastructure..."
    
    # Check if test deployment exists
    if [[ ! -f "test-deployment.yml" ]]; then
        print_error "test-deployment.yml not found. Cannot proceed with cleanup."
        exit 1
    fi
    
    # Remove using serverless
    print_status "Removing test infrastructure using Serverless Framework..."
    if serverless remove --config test-deployment.yml --verbose; then
        print_success "Test infrastructure removed successfully!"
    else
        print_error "Failed to remove test infrastructure using Serverless Framework."
        print_warning "You may need to manually clean up resources in the AWS console."
        exit 1
    fi
    
    # Additional cleanup checks
    print_status "Performing additional cleanup checks..."
    
    # Check for any remaining resources
    check_remaining_resources
    
    print_success "🎉 Cleanup completed successfully!"
    print_status "All test resources have been removed from AWS."
}

# Check for remaining resources
check_remaining_resources() {
    print_status "Checking for any remaining resources..."
    
    # Check ECS clusters
    if aws ecs list-clusters --query 'clusterArns[?contains(@, `test-ecs-scaler`)]' --output text | grep -q .; then
        print_warning "Found remaining ECS clusters. You may need to delete them manually."
    fi
    
    # Check SQS queues
    if aws sqs list-queues --query 'QueueUrls[?contains(@, `test-ecs-scaler`)]' --output text | grep -q .; then
        print_warning "Found remaining SQS queues. You may need to delete them manually."
    fi
    
    # Check Lambda functions
    if aws lambda list-functions --query 'Functions[?contains(FunctionName, `test-ecs-scaler`)].FunctionName' --output text | grep -q .; then
        print_warning "Found remaining Lambda functions. You may need to delete them manually."
    fi
    
    # Check VPCs
    if aws ec2 describe-vpcs --filters "Name=tag:Name,Values=test-ecs-scaler-vpc" --query 'Vpcs[].VpcId' --output text | grep -q .; then
        print_warning "Found remaining VPC. You may need to delete it manually."
    fi
    
    # Check IAM roles
    if aws iam list-roles --query 'Roles[?contains(RoleName, `test-ecs-scaler`)].RoleName' --output text | grep -q .; then
        print_warning "Found remaining IAM roles. You may need to delete them manually."
    fi
    
    # Check CloudWatch log groups
    if aws logs describe-log-groups --query 'logGroups[?contains(logGroupName, `test-ecs-scaler`)].logGroupName' --output text | grep -q .; then
        print_warning "Found remaining CloudWatch log groups. You may need to delete them manually."
    fi
}

# Show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Clean up the test infrastructure for Serverless ECS Scaler

OPTIONS:
    -f, --force    Skip confirmation prompt
    -h, --help     Show this help message

EXAMPLES:
    # Clean up with confirmation
    $0

    # Force cleanup without confirmation
    $0 --force

EOF
}

# Main execution
main() {
    print_status "Serverless ECS Scaler - Test Cleanup Script"
    echo
    
    # Parse arguments
    FORCE=false
    while [[ $# -gt 0 ]]; do
        case $1 in
            -f|--force)
                FORCE=true
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
    
    # Confirm cleanup unless forced
    if [[ "$FORCE" != true ]]; then
        confirm_cleanup
    fi
    
    # Proceed with cleanup
    cleanup_test
}

# Run main function
main "$@"
