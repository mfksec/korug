# Contributing to Körüg

First off, thank you for considering a contribution to Körüg! It's people like you that make Körüg such a great tool.

## Code of Conduct

This project and everyone participating in it is governed by our
[Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to
uphold this code.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the issue list as you might find out that you don't need to create one. When you are creating a bug report, please include as many details as possible:

* **Use a clear and descriptive title**
* **Describe the exact steps which reproduce the problem**
* **Provide specific examples to demonstrate the steps**
* **Describe the behavior you observed after following the steps**
* **Explain which behavior you expected to see instead and why**
* **Include screenshots/logs if possible**
* **Include your environment details** (OS, Python version, etc.)

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

* **Use a clear and descriptive title**
* **Provide a step-by-step description of the suggested enhancement**
* **Provide specific examples to demonstrate the steps**
* **Describe the current behavior and expected behavior**
* **Explain why this enhancement would be useful**

### Pull Requests

* Fill in the required template
* Follow the Python styleguides
* Include appropriate test cases
* Document new code with docstrings
* End all files with a newline

## Styleguides

### Git Commit Messages

* Use the present tense ("Add feature" not "Added feature")
* Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
* Limit the first line to 72 characters or less
* Reference issues and pull requests liberally after the first line

### Python Styleguide

* Follow PEP 8
* Use type hints for function signatures
* Add docstrings to all public functions and classes
* Keep lines under 100 characters
* Use meaningful variable names

### Documentation Styleguide

* Use Markdown
* Include code examples where applicable
* Keep documentation up-to-date with code changes

## Development Setup

```bash
# Clone the repository
git clone https://github.com/mfksec/korug.git
cd korug

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install development dependencies
pip install -r requirements.txt
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run linting
black src/
isort src/
flake8 src/
```

## Testing

* Write tests for all new features
* Ensure all tests pass before submitting a PR
* Aim for >80% code coverage
* Use pytest for testing

```bash
# Run tests with coverage
pytest tests/ --cov=src/korug --cov-report=html
```

## Additional Notes

### Issue and Pull Request Labels

* `bug` - Something isn't working
* `enhancement` - New feature or request
* `documentation` - Improvements or additions to documentation
* `good first issue` - Good for newcomers
* `help wanted` - Extra attention is needed
* `question` - Further information is requested

## Recognition

Contributors will be recognized in the project's README and releases.

Thank you for contributing! 🎉
