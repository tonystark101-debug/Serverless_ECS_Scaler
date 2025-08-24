# Testing Guide for Serverless ECS Scaler

This guide will help you test the ECS scaler functionality with real AWS services to ensure it works correctly before releasing it as an open-source solution.

## 🎯 **Testing Objectives**

1. **Validate Core Functionality**: Ensure the Lambda function can scale ECS services up and down
2. **Test Performance**: Measure response times for scaling operations
3. **Verify Integration**: Confirm SQS and EventBridge triggers work correctly
4. **Check Error Handling**: Test various failure scenarios
5. **Monitor Costs**: Ensure the solution is cost-effective

## 🚀 **Quick Start Testing**

### Prerequisites

- ✅ AWS CLI configured with appropriate permissions
- ✅ Serverless Framework installed (`npm install -g serverless`)
- ✅ Python 3.9+ with required packages
- ✅ AWS account with permissions for ECS, SQS, Lambda, VPC, IAM

### Step 1: Deploy Test Infrastructure

```bash
# Deploy the test infrastructure
./deploy-test.sh deploy
```

This will create:
- ECS cluster with Fargate capacity
- ECS service (initially scaled to 0)
- SQS queue for job processing
- Lambda function with ECS scaler logic
- VPC with public subnets
- All necessary IAM roles and security groups

### Step 2: Run Functional Tests

```bash
# Run the automated test script
python test-scaler.py
```

Choose option **1** to run the complete scaling test.

### Step 3: Monitor Results

The test will:
1. Check initial state (0 tasks)
2. Send test messages to SQS
3. Monitor scale-up (should scale to 2 tasks)
4. Wait for tasks to complete
5. Monitor scale-down (should scale back to 0)
6. Provide test results analysis

## 🔍 **Manual Testing Scenarios**

### Scenario 1: Basic Scale-Up Test

1. **Check initial state**:
   ```bash
   python test-scaler.py
   # Choose option 4: Check current status
   ```

2. **Send test messages**:
   ```bash
   python test-scaler.py
   # Choose option 3: Send test messages
   # Enter: 5
   ```

3. **Monitor scaling**:
   ```bash
   python test-scaler.py
   # Choose option 2: Monitor scaling behavior
   # Enter: 5 (minutes)
   ```

### Scenario 2: Performance Testing

1. **Measure scale-up time**:
   - Send message to SQS
   - Start timer
   - Check ECS service until desired count changes
   - Record response time

2. **Measure scale-down time**:
   - Wait for queue to empty
   - Start timer
   - Check ECS service until running count reaches 0
   - Record response time

### Scenario 3: Load Testing

1. **Send multiple messages rapidly**:
   ```bash
   # Send 10 messages quickly
   for i in {1..10}; do
     aws sqs send-message \
       --queue-url $(aws sqs get-queue-url --queue-name test-ecs-scaler-queue --output text) \
       --message-body "{\"test\": \"load-test-$i\"}"
   done
   ```

2. **Monitor scaling behavior**:
   - Check if service scales to target (2 tasks)
   - Verify no more than 2 tasks are created
   - Monitor task processing

## 📊 **Expected Results**

### ✅ **Successful Test Results**

- **Scale-Up**: ECS service should scale from 0 to 2 tasks within 30-60 seconds
- **Scale-Down**: ECS service should scale from 2 to 0 tasks within 2-3 minutes
- **Queue Processing**: Messages should be processed by ECS tasks
- **Logs**: CloudWatch logs should show scaling operations

### ❌ **Common Issues & Solutions**

#### Issue: ECS Service Not Scaling
- **Check**: Lambda function logs in CloudWatch
- **Solution**: Verify IAM permissions for ECS operations

#### Issue: Tasks Not Starting
- **Check**: ECS service events and task definition
- **Solution**: Verify VPC configuration and security groups

#### Issue: Lambda Function Errors
- **Check**: CloudWatch logs for the Lambda function
- **Solution**: Verify environment variables and IAM permissions

#### Issue: SQS Messages Not Triggering
- **Check**: SQS event source mapping
- **Solution**: Verify queue ARN and Lambda permissions

## 🔧 **Troubleshooting Commands**

### Check ECS Service Status
```bash
aws ecs describe-services \
  --cluster test-ecs-scaler-cluster \
  --services test-ecs-scaler-service
```

### Check SQS Queue Depth
```bash
aws sqs get-queue-attributes \
  --queue-url $(aws sqs get-queue-url --queue-name test-ecs-scaler-queue --output text) \
  --attribute-names ApproximateNumberOfMessagesVisible
```

### Check Lambda Function Logs
```bash
aws logs tail /aws/lambda/test-ecs-scaler --follow
```

### Check ECS Task Logs
```bash
# Get task ARN first
TASK_ARN=$(aws ecs list-tasks --cluster test-ecs-scaler-cluster --service-name test-ecs-scaler-service --query 'taskArns[0]' --output text)

# Get logs
aws logs tail /ecs/test-ecs-scaler --follow
```

## 💰 **Cost Monitoring**

### Expected Costs (us-east-1)
- **Lambda**: ~$0.01-0.05 per test run
- **ECS Fargate**: ~$0.01-0.02 per task-minute
- **SQS**: ~$0.0000004 per message
- **VPC**: ~$0.01 per hour
- **Total**: <$0.10 per complete test

### Cost Optimization
- Tests run for minimal time
- ECS tasks scale to 0 when idle
- VPC resources are cleaned up after testing

## 🧹 **Cleanup After Testing**

### Option 1: Automated Cleanup
```bash
./cleanup-test.sh
```

### Option 2: Force Cleanup
```bash
./cleanup-test.sh --force
```

### Option 3: Manual Cleanup
```bash
serverless remove --config test-deployment.yml
```

## 📈 **Performance Benchmarks**

### Target Performance Metrics
- **Scale-Up Response**: <60 seconds
- **Scale-Down Response**: <3 minutes
- **Lambda Execution**: <5 seconds
- **ECS Task Startup**: <2 minutes

### Recording Results
Create a test results file:
```bash
# Create test results
cat > test-results-$(date +%Y%m%d-%H%M%S).txt << EOF
Test Date: $(date)
AWS Region: us-east-1
Test Duration: [duration]

Scale-Up Performance:
- Response Time: [X] seconds
- Target Achieved: [YES/NO]
- Issues: [description]

Scale-Down Performance:
- Response Time: [X] minutes
- Scale to Zero: [YES/NO]
- Issues: [description]

Overall Assessment: [PASS/FAIL]
Notes: [any observations]
EOF
```

## 🎉 **Success Criteria**

The test is considered **successful** if:

1. ✅ ECS service scales from 0 to 2 tasks when messages arrive
2. ✅ ECS service scales from 2 to 0 tasks when queue is empty
3. ✅ Scaling operations complete within expected timeframes
4. ✅ No errors in CloudWatch logs
5. ✅ All AWS resources are properly cleaned up

## 🚨 **Important Notes**

- **Test Environment**: This creates real AWS resources that will incur costs
- **Cleanup Required**: Always clean up test resources to avoid ongoing charges
- **Region Specific**: Tests are configured for us-east-1 by default
- **Permissions**: Ensure your AWS user has sufficient permissions
- **VPC Limits**: Be aware of VPC limits in your AWS account

## 🔗 **Next Steps After Testing**

1. **If Tests Pass**: Proceed with open-source release
2. **If Issues Found**: Fix problems and re-test
3. **Document Results**: Record performance metrics and observations
4. **Optimize**: Make improvements based on test results
5. **Release**: Share the working solution with the community

---

**Happy Testing! 🧪✨**

If you encounter any issues during testing, check the troubleshooting section above or refer to the main README.md for additional guidance.
