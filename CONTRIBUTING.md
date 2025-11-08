# Contributing to Humancheck

Thank you for your interest in contributing to Humancheck! This document provides guidelines and instructions for contributing.

## Getting Started

### Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/humancheck.git
   cd humancheck
   ```

2. **Install dependencies**:
   ```bash
   poetry install
   ```

3. **Set up pre-commit hooks** (optional but recommended):
   ```bash
   poetry run pre-commit install
   ```

4. **Initialize configuration**:
   ```bash
   poetry run humancheck init
   ```

5. **Run tests**:
   ```bash
   poetry run pytest
   ```

### Project Structure

```
humancheck/
├── src/humancheck/          # Main package
│   ├── adapters/            # Framework adapters
│   ├── routing/             # Routing engine
│   ├── tools/               # MCP tools
│   ├── api.py               # REST API
│   ├── mcp_server.py        # MCP server
│   ├── config.py            # Configuration
│   ├── database.py          # Database layer
│   ├── models.py            # Core data models
│   ├── platform_models.py   # Multi-tenancy models
│   └── schemas.py           # Pydantic schemas
├── frontend/                # Streamlit dashboard
├── examples/                # Example integrations
├── tests/                   # Test suite
└── docs/                    # Documentation
```

## Development Workflow

### Creating a New Feature

1. **Create a new branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**:
   - Write code
   - Add tests
   - Update documentation

3. **Run tests and linting**:
   ```bash
   poetry run pytest
   poetry run black .
   poetry run ruff check .
   ```

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "Add: your feature description"
   ```

5. **Push and create PR**:
   ```bash
   git push origin feature/your-feature-name
   ```

### Commit Message Guidelines

Follow conventional commits format:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Test additions or changes
- `refactor:` Code refactoring
- `style:` Code style changes (formatting, etc.)
- `chore:` Build process or auxiliary tool changes

Example:
```
feat: add Slack notification support for review decisions
```

## Code Standards

### Python Style

- Follow PEP 8
- Use Black for formatting (line length: 100)
- Use type hints wherever possible
- Write docstrings for all public functions and classes

### Example Code Style

```python
async def create_review(
    task_type: str,
    proposed_action: str,
    confidence_score: Optional[float] = None,
) -> Review:
    """Create a new review request.

    Args:
        task_type: Type of task being reviewed
        proposed_action: The action to be reviewed
        confidence_score: Optional confidence score (0-1)

    Returns:
        Created Review instance

    Raises:
        ValueError: If task_type is invalid
    """
    # Implementation
    pass
```

## Adding New Framework Adapters

To add support for a new AI framework:

1. **Create adapter file**:
   ```python
   # src/humancheck/adapters/your_framework_adapter.py
   from .base import ReviewAdapter, UniversalReview

   class YourFrameworkAdapter(ReviewAdapter):
       def to_universal(self, framework_request):
           # Convert to UniversalReview
           pass

       def from_universal(self, universal_review, decision):
           # Convert back to framework format
           pass

       def get_framework_name(self):
           return "your_framework"

       async def handle_blocking(self, review_id, timeout):
           # Handle blocking requests
           pass
   ```

2. **Register in `__init__.py`**:
   ```python
   from .your_framework_adapter import YourFrameworkAdapter

   __all__ = [..., "YourFrameworkAdapter"]
   ```

3. **Add tests**:
   ```python
   # tests/test_your_framework_adapter.py
   def test_your_framework_adapter():
       # Test adapter functionality
       pass
   ```

4. **Update documentation**:
   - Add example in `examples/`
   - Update README.md
   - Add to adapter documentation

## Testing

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=humancheck

# Run specific test file
poetry run pytest tests/test_api.py

# Run specific test
poetry run pytest tests/test_api.py::test_create_review
```

### Writing Tests

- Write tests for all new features
- Aim for >80% code coverage
- Use pytest fixtures for common setup
- Test both success and error cases

Example:

```python
@pytest.mark.asyncio
async def test_create_review(client):
    """Test creating a review request."""
    response = await client.post("/reviews", json={
        "task_type": "test",
        "proposed_action": "Test action",
    })
    assert response.status_code == 201
    assert response.json()["status"] == "pending"
```

## Documentation

### Updating Documentation

- Keep README.md up to date
- Add docstrings to all public APIs
- Update examples when adding features
- Add inline comments for complex logic

### Building Documentation (future)

```bash
poetry run mkdocs serve
```

## Pull Request Process

1. **Ensure tests pass**:
   ```bash
   poetry run pytest
   ```

2. **Update documentation** if needed

3. **Create pull request**:
   - Clear title and description
   - Reference any related issues
   - Include screenshots for UI changes

4. **Code review**:
   - Address reviewer feedback
   - Keep discussions professional and constructive

5. **Merge**:
   - Squash commits if requested
   - Delete branch after merge

## Reporting Issues

### Bug Reports

Include:
- Description of the bug
- Steps to reproduce
- Expected vs actual behavior
- Environment (OS, Python version, etc.)
- Relevant logs or error messages

### Feature Requests

Include:
- Clear description of the feature
- Use case and motivation
- Example API or usage
- Any alternatives considered

## Code of Conduct

### Our Standards

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Respect different viewpoints
- Prioritize community well-being

### Unacceptable Behavior

- Harassment or discrimination
- Trolling or insulting comments
- Publishing private information
- Unprofessional conduct

## Questions?

- Open a [GitHub Issue](https://github.com/yourusername/humancheck/issues)
- Join our [Discord](https://discord.gg/humancheck)
- Email: hello@humancheck.dev

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Humancheck! 🎉
