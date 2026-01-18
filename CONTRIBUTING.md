# Contributing to ByteIT

We welcome contributions from the community! Whether you're reporting bugs, suggesting features, or submitting code, your help makes ByteIT better.

## Getting Started

### Prerequisites
- Python 3.8 or higher
- `git` for version control
- A ByteIT API key (for integration testing)

### Setup Development Environment

1. Clone the repository:
```bash
git clone https://github.com/byteit-ai/byteit-api.git
cd byteit-api
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install in development mode:
```bash
pip install -e ".[dev]"
```

## Running Tests

### Unit Tests
```bash
pytest tests/ -v
```

### Integration Tests (requires API key)
```bash
export BYTEIT_API_KEY="your_api_key"
pytest -m integration
```

### Run All Tests
```bash
pytest
```

## Code Style

We use Black for code formatting and isort for import sorting.

### Format Code
```bash
black byteit tests
isort byteit tests
```

### Check Formatting
```bash
black --check byteit tests
isort --check-only byteit tests
```

### Type Checking
```bash
mypy byteit
```

## Reporting Issues

When reporting bugs, please include:
- Python version
- OS and version
- Steps to reproduce
- Expected behavior
- Actual behavior
- Any error messages or stack traces

## Submitting Changes

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`pytest`)
6. Format code (`black byteit tests && isort byteit tests`)
7. Commit with clear messages (`git commit -am 'Add feature X'`)
8. Push to your fork (`git push origin feature/your-feature`)
9. Open a Pull Request with a clear description

## Pull Request Guidelines

- One feature per PR
- Tests for all new code
- Update documentation as needed
- Ensure CI checks pass
- Squash commits if requested
- Use clear, descriptive commit messages

## Code Standards

- Follow PEP 8
- Use type hints
- Add docstrings to public functions
- Keep functions focused and simple
- Write tests for edge cases

## Community

- **Issues**: Report bugs or request features via GitHub Issues
- **Discussions**: Join our community discussions for questions
- **Support**: For commercial support, visit [https://byteit.ai/contact](https://byteit.ai/contact)

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.

Thank you for contributing to ByteIT!
