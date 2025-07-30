# Contributing to NSP MCP Connector

Thank you for your interest in contributing to the NSP MCP Connector! This document provides guidelines for contributing to this project.

## Code of Conduct

This project and its participants are governed by a Code of Conduct. By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

- Use the GitHub issue tracker
- Include detailed steps to reproduce the bug
- Include your environment details (OS, Python version, etc.)
- Include error messages and stack traces

### Suggesting Enhancements

- Use the GitHub issue tracker
- Describe the enhancement clearly
- Explain why this enhancement would be useful
- Include any mockups or examples if applicable

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## Development Setup

1. Clone your fork
2. Install dependencies:
   ```bash
   cd local-server
   pip install -r requirements.txt
   
   cd ../azure-function
   pip install -r requirements.txt
   ```
3. Set up environment variables (see README.md)
4. Run tests to ensure everything works

## Code Style

- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add docstrings to all public functions
- Keep functions small and focused
- Add type hints where appropriate

## Testing

- Write tests for new functionality
- Ensure all existing tests pass
- Run the test suite before submitting a PR:
  ```bash
  python test_local_server.py
  ```

## Documentation

- Update README.md if you add new features
- Add docstrings to new functions
- Update deployment guide if you change configuration

## Questions?

If you have questions about contributing, please open an issue or contact the maintainers.

Thank you for contributing! 