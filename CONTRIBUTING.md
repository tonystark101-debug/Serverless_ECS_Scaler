# Contributing to Serverless ECS Scaler

Thank you for considering contributing to Serverless ECS Scaler! We welcome contributions from the community.

## Getting Started

1. **Fork the repository**
2. **Clone your fork**
   ```bash
   git clone https://github.com/yourusername/serverless-ecs-scaler.git
   cd serverless-ecs-scaler
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements-dev.txt
   npm install
   ```

4. **Install pre-commit hooks**
   ```bash
   pre-commit install
   ```

## Development Process

### Making Changes

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write tests for new functionality
   - Update documentation as needed
   - Follow the existing code style

3. **Test your changes**
   ```bash
   # Run unit tests
   pytest tests/ -v
   
   # Run linting
   flake8 src/ tests/
   
   # Format code
   black src/ tests/
   ```

4. **Commit and push**
   ```bash
   git add .
   git commit -m "Add feature: your feature description"
   git push origin feature/your-feature-name
   ```

5. **Create a Pull Request**

### Code Style

- Use [Black](https://black.readthedocs.io/) for Python code formatting
- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) guidelines
- Use type hints where appropriate
- Write descriptive commit messages

### Testing

- Write unit tests for all new functionality
- Maintain test coverage above 80%
- Include integration tests for major features
- Test both success and failure scenarios

### Documentation

- Update README.md for user-facing changes
- Add docstrings to new functions and classes
- Include examples for new configuration options
- Update the changelog

## Pull Request Guidelines

### Before Submitting

- [ ] Tests pass locally
- [ ] Code is formatted with Black
- [ ] Documentation is updated
- [ ] Commit messages are descriptive
- [ ] PR description explains the changes

### PR Description Template

```markdown
## Description
Brief description of the changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests pass
```

## Reporting Issues

### Bug Reports

Include:
- Serverless Framework version
- AWS region and services used
- Steps to reproduce
- Expected vs actual behavior
- Relevant logs or error messages

### Feature Requests

Include:
- Use case description
- Proposed solution
- Alternative solutions considered
- Additional context

## Development Environment

### Prerequisites

- Python 3.9+
- Node.js 16+
- AWS CLI configured
- Serverless Framework

### Project Structure

```
serverless-ecs-scaler/
├── src/
│   └── scaler.py          # Main Lambda function
├── tests/
│   └── test_scaler.py     # Unit tests
├── examples/
│   ├── video-processing.yml
│   ├── batch-processing.yml
│   └── development.yml
├── docs/                  # Additional documentation
├── serverless.yml         # Main Serverless config
├── requirements.txt       # Python dependencies
└── package.json          # Node.js dependencies
```

### Local Testing

```bash
# Set up test environment variables
export SQS_QUEUE_URL="test-queue-url"
export ECS_CLUSTER_NAME="test-cluster"
export ECS_SERVICE_NAME="test-service"

# Run the Lambda function locally
python src/scaler.py

# Run specific tests
pytest tests/test_scaler.py::TestScaler::test_lambda_handler_scale_up -v
```

## Release Process

1. Update version in `package.json`
2. Update CHANGELOG.md
3. Create and push a git tag
4. GitHub Actions will automatically create a release

## Community

- [GitHub Discussions](https://github.com/yourusername/serverless-ecs-scaler/discussions) for questions and ideas
- [GitHub Issues](https://github.com/yourusername/serverless-ecs-scaler/issues) for bugs and feature requests

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

