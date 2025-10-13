# Contributing to Auto-M4B

Thank you for your interest in contributing to Auto-M4B! This document provides guidelines and instructions for contributing to the project.

## Ways to Contribute

There are many ways to contribute to Auto-M4B:

1. **Report bugs** - Submit detailed bug reports with reproduction steps
2. **Suggest features** - Propose new features or improvements
3. **Write documentation** - Improve or expand documentation
4. **Fix bugs** - Submit pull requests to fix known issues
5. **Implement features** - Develop new functionality
6. **Test** - Test pre-release versions and provide feedback
7. **Share your experience** - Write tutorials or blog posts

## Getting Started

### Prerequisites

- **Git** - For cloning and version control
- **Docker** and **Docker Compose** - For building and testing
- **Python 3.9+** - For local development
- **pipenv** - For Python dependency management

### Setting Up Development Environment

1. **Fork and clone the repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/auto-m4b.git
   cd auto-m4b
   ```

2. **Install Python dependencies**:
   ```bash
   # Install pipenv if you don't have it
   pip install pipenv

   # Install dependencies
   pipenv install --dev
   ```

3. **Create a test environment**:
   ```bash
   # Create test folders
   mkdir -p ~/auto-m4b-test/{inbox,converted,archive,backup}

   # Copy example env file
   cp .env.example .env.test

   # Edit .env.test with your paths
   ```

4. **Build the Docker image**:
   ```bash
   docker build -t darthdobber/auto-m4b:dev .
   ```

5. **Run tests** (when available):
   ```bash
   pipenv run pytest
   ```

### Development Workflow

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/bug-description
   ```

2. **Make your changes**:
   - Write code
   - Add tests (when test framework is available)
   - Update documentation

3. **Test your changes**:
   ```bash
   # Run locally with test mode
   pipenv run python -m src --test --debug

   # Or build and run in Docker
   docker build -t darthdobber/auto-m4b:test .
   docker-compose -f docker-compose.test.yml up
   ```

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

   See [Commit Message Guidelines](#commit-message-guidelines) below.

5. **Push and create a pull request**:
   ```bash
   git push origin feature/your-feature-name
   ```

   Then open a pull request on GitHub.

## Code Style

### Python Style

We follow [PEP 8](https://pep8.org/) with some modifications:

- **Line length**: 88 characters (Black default)
- **Quotes**: Double quotes for strings
- **Imports**: Organized (stdlib, third-party, local)
- **Type hints**: Use type hints for function signatures

### Code Formatting

We use **Black** for code formatting:

```bash
# Format all Python files
pipenv run black src/

# Check formatting without changes
pipenv run black --check src/
```

### Linting

We use **flake8** for linting:

```bash
pipenv run flake8 src/
```

### Type Checking

We use **mypy** for type checking:

```bash
pipenv run mypy src/
```

## Commit Message Guidelines

We use [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- **feat**: A new feature
- **fix**: A bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, etc.)
- **refactor**: Code refactoring
- **test**: Adding or updating tests
- **chore**: Maintenance tasks (dependencies, build, etc.)
- **perf**: Performance improvements

### Examples

```
feat(conversion): add support for OGG files

Adds support for converting OGG Vorbis files to M4B.
Includes file detection and format validation.

Closes #123
```

```
fix(permissions): correct PUID/PGID handling in entrypoint

The entrypoint script was not properly creating users with
specified PUID/PGID values. This fix ensures user creation
works correctly for all UID/GID combinations.

Fixes #456
```

```
docs(config): document all environment variables

Adds comprehensive documentation for all configuration
options with examples and default values.
```

## Testing

### Manual Testing

1. **Test with a sample audiobook**:
   ```bash
   # Copy test book to inbox
   cp -r test-data/sample-book ~/auto-m4b-test/inbox/

   # Run Auto-M4B in test mode
   python -m src --test --debug --max_loops 1

   # Verify output
   ls -la ~/auto-m4b-test/converted/
   ```

2. **Test different scenarios**:
   - Single MP3 file
   - Multi-file folder
   - Multi-disc structure
   - Already-converted M4B
   - Corrupted files (error handling)

### Automated Testing (Future)

When the test framework is implemented (Phase 4.3):

```bash
# Run all tests
pipenv run pytest

# Run specific test file
pipenv run pytest tests/test_audiobook.py

# Run with coverage
pipenv run pytest --cov=src
```

## Pull Request Process

### Before Submitting

- [ ] Code follows style guidelines
- [ ] Commit messages follow conventions
- [ ] Tests pass (when available)
- [ ] Documentation updated (if applicable)
- [ ] CHANGELOG.md updated (for significant changes)

### PR Checklist

Your pull request should:

1. **Have a clear title and description**:
   - What does it do?
   - Why is it needed?
   - How was it tested?

2. **Reference related issues**:
   - "Fixes #123"
   - "Closes #456"
   - "Related to #789"

3. **Include test results**:
   - Manual testing steps
   - Test output/logs
   - Before/after comparisons

4. **Update documentation**:
   - README.md (if user-facing)
   - docs/ (for major features)
   - Inline code comments

### Review Process

1. **Automated checks** run (linting, formatting, tests when available)
2. **Maintainer review** - typically within 1-7 days
3. **Feedback** - address any requested changes
4. **Approval** - once approved, will be merged
5. **Release** - included in next release

## Coding Guidelines

### File Organization

```python
# 1. Standard library imports
import os
import sys
from pathlib import Path

# 2. Third-party imports
import cachetools
from pydantic import BaseModel

# 3. Local imports
from src.lib.config import cfg
from src.lib.audiobook import Audiobook
```

### Function Documentation

Use docstrings for public functions:

```python
def convert_book(book: Audiobook) -> bool:
    """
    Convert an audiobook to M4B format.

    Args:
        book: Audiobook object to convert

    Returns:
        True if conversion succeeded, False otherwise

    Raises:
        ValueError: If book path does not exist
        RuntimeError: If m4b-tool fails
    """
    ...
```

### Error Handling

- Use specific exception types
- Provide meaningful error messages
- Log errors with context
- Fail gracefully when possible

```python
try:
    result = m4b_tool.merge(book)
except subprocess.CalledProcessError as e:
    print_error(f"m4b-tool merge failed for {book.title}: {e}")
    fail_book(book, error=str(e))
    return False
```

### Configuration

- All configuration via environment variables
- Use `cfg` singleton for access
- Provide sensible defaults
- Validate configuration at startup

```python
from src.lib.config import cfg

cpu_cores = cfg.CPU_CORES  # Auto-detected default
sleep_time = cfg.SLEEP_TIME  # 10 seconds default
```

## Project Structure

### Key Files

- **`src/auto_m4b.py`**: Main application loop
- **`src/lib/run.py`**: Core processing logic
- **`src/lib/audiobook.py`**: Audiobook data model
- **`src/lib/config.py`**: Configuration management
- **`src/lib/inbox_state.py`**: State tracking
- **`Dockerfile`**: Container definition
- **`entrypoint.sh`**: Container startup

### Adding New Features

1. **Create issue** describing the feature
2. **Discuss approach** in issue comments
3. **Implement** in feature branch
4. **Test** thoroughly
5. **Document** in code and docs
6. **Submit PR** with tests and docs

### Example: Adding a New Configuration Option

1. **Add to `config.py`**:
   ```python
   @env_property(typ=bool, default=False)
   def _NEW_FEATURE(self): ...

   NEW_FEATURE = _NEW_FEATURE
   ```

2. **Use in code**:
   ```python
   from src.lib.config import cfg

   if cfg.NEW_FEATURE:
       do_something()
   ```

3. **Document in `docs/configuration.md`**:
   ```markdown
   ### NEW_FEATURE
   - **Type**: Boolean
   - **Default**: `N`
   - **Description**: Enables the new feature
   ```

4. **Add to example docker-compose**:
   ```yaml
   environment:
     - NEW_FEATURE=Y
   ```

## Documentation

### Documentation Standards

- **Clear and concise** - Easy to understand
- **Examples** - Show real usage
- **Up-to-date** - Keep in sync with code
- **Comprehensive** - Cover common use cases

### Where to Document

- **README.md**: Quick start, overview
- **docs/**: Detailed guides and reference
- **Code comments**: Complex logic, non-obvious behavior
- **Docstrings**: Public functions and classes

### Building Documentation

Currently documentation is in Markdown. Future: Consider Sphinx or MkDocs.

```bash
# Preview locally
# (Use any Markdown previewer)
```

## Release Process

(For maintainers)

1. **Update version** in relevant files
2. **Update CHANGELOG.md** with changes
3. **Create release tag**:
   ```bash
   git tag -a v1.2.0 -m "Release v1.2.0"
   git push origin v1.2.0
   ```
4. **Build and push Docker images**:
   ```bash
   docker build -t darthdobber/auto-m4b:1.2.0 .
   docker tag darthdobber/auto-m4b:1.2.0 darthdobber/auto-m4b:latest
   docker push darthdobber/auto-m4b:1.2.0
   docker push darthdobber/auto-m4b:latest
   ```
5. **Create GitHub release** with notes

## Community

### Getting Help

- **GitHub Discussions**: Ask questions, share ideas
- **GitHub Issues**: Bug reports, feature requests
- **Gitter Chat**: Real-time discussion (if available)

### Code of Conduct

We follow the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).

In summary:
- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Assume good intentions

## Recognition

Contributors are recognized in:
- GitHub contributors list
- CHANGELOG.md
- Release notes

Significant contributors may be added to:
- README.md acknowledgments
- Project authors

## Resources

### Helpful Links

- **Auto-M4B GitHub**: https://github.com/DarthDobber/auto-m4b
- **m4b-tool**: https://github.com/sandreas/m4b-tool
- **FFmpeg**: https://ffmpeg.org/
- **Python Style Guide**: https://pep8.org/
- **Conventional Commits**: https://www.conventionalcommits.org/

### Learning Resources

- **Docker**: https://docs.docker.com/get-started/
- **Python**: https://docs.python.org/3/
- **Audiobook Formats**: https://en.wikipedia.org/wiki/Audiobook

## Questions?

If you have questions about contributing:

1. Check existing [GitHub Issues](https://github.com/DarthDobber/auto-m4b/issues)
2. Ask in [GitHub Discussions](https://github.com/DarthDobber/auto-m4b/discussions)
3. Review [documentation](README.md)

Thank you for contributing to Auto-M4B! 🎉
