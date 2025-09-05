# Contributing to Agent Interoperability & Blockchain Integration

Thank you for your interest in contributing to this project! This document provides guidelines and instructions for contributing.

## Code of Conduct

This project adheres to a code of conduct that all contributors are expected to follow. Please be respectful and constructive in all interactions.

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Redis server
- Git

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/brainstems/agent_interoperability_blockchain_integration.git
   cd agent_interoperability_blockchain_integration
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r agents/requirements-dev.txt
   ```

4. **Set up environment variables**
   ```bash
   cp agents/marketing/.env.example agents/marketing/.env
   # Edit .env with your actual credentials
   ```

5. **Run tests**
   ```bash
   pytest tests/
   ```

## Development Workflow

### Branching Strategy

- `main` - Production-ready code
- `develop` - Integration branch for features
- `feature/*` - New features
- `bugfix/*` - Bug fixes
- `hotfix/*` - Urgent production fixes

### Making Changes

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clear, documented code
   - Follow the existing code style
   - Add tests for new functionality
   - Update documentation as needed

3. **Run tests and linting**
   ```bash
   pytest tests/
   black agents/
   flake8 agents/
   mypy agents/
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: Add your feature description"
   ```

   Follow [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` - New feature
   - `fix:` - Bug fix
   - `docs:` - Documentation changes
   - `refactor:` - Code refactoring
   - `test:` - Adding or updating tests
   - `chore:` - Maintenance tasks

5. **Push and create a pull request**
   ```bash
   git push origin feature/your-feature-name
   ```

## Code Style Guidelines

### Python Style

- Follow [PEP 8](https://pep8.org/)
- Use type hints for function signatures
- Maximum line length: 100 characters
- Use `black` for code formatting
- Use `isort` for import sorting

### Documentation

- All public functions/classes must have docstrings
- Use Google-style docstrings
- Include examples in docstrings where helpful
- Keep README files up to date

### Example

```python
from typing import Dict, Any, Optional

def calculate_reward(
    agent_id: str,
    performance_metrics: Dict[str, float],
    baseline: Optional[float] = None
) -> float:
    """
    Calculate reward for an agent based on performance metrics.
    
    Args:
        agent_id: Unique identifier for the agent
        performance_metrics: Dictionary of metric names to values
        baseline: Optional baseline for comparison
        
    Returns:
        Calculated reward value
        
    Example:
        >>> metrics = {"accuracy": 0.95, "speed": 1.2}
        >>> reward = calculate_reward("agent_1", metrics, baseline=0.8)
        >>> print(reward)
        1.15
    """
    # Implementation
    pass
```

## Testing Guidelines

### Writing Tests

- Write unit tests for all new functions
- Write integration tests for new features
- Aim for >80% code coverage
- Use pytest fixtures for common setup
- Mock external dependencies

### Test Structure

```python
import pytest
from infrastructure_crew.rl import RewardCalculator

@pytest.fixture
def reward_calculator():
    """Fixture for reward calculator."""
    return RewardCalculator(base_reward=1.0)

def test_task_completion_reward_success(reward_calculator):
    """Test reward calculation for successful task completion."""
    reward = reward_calculator.calculate_task_completion_reward(
        agent_id="test_agent",
        task_success=True,
        completion_time=30.0,
        expected_time=60.0,
        quality_score=0.9
    )
    
    assert reward.value > 0
    assert reward.agent_id == "test_agent"
    assert reward.reward_type == RewardType.TASK_COMPLETION
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/unit/test_blockchain_consensus.py

# Run with coverage
pytest --cov=agents tests/

# Run with verbose output
pytest -v tests/
```

## Documentation

### Adding Documentation

- Update relevant `.md` files in the `docs/` directory
- Add inline code comments for complex logic
- Update the main `README.md` if adding major features
- Include usage examples

### Documentation Structure

```
docs/
├── BLOCKCHAIN_INTEGRATION.md  # Blockchain features
├── RL_INTEGRATION.md           # RL features
├── API_REFERENCE.md            # API documentation
└── ARCHITECTURE.md             # System architecture
```

## Pull Request Process

1. **Ensure all tests pass**
2. **Update documentation**
3. **Add a clear PR description**
   - What changes were made
   - Why they were made
   - How to test them
4. **Link related issues**
5. **Request review from maintainers**
6. **Address review feedback**

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How to test these changes

## Checklist
- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] No new warnings
```

## Reporting Issues

### Bug Reports

Include:
- Clear description of the bug
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, etc.)
- Error messages/stack traces

### Feature Requests

Include:
- Clear description of the feature
- Use case/motivation
- Proposed implementation (if any)
- Potential impact on existing features

## Community

### Getting Help

- Open an issue for bugs or questions
- Check existing issues and documentation first
- Be specific and provide context

### Communication

- Be respectful and constructive
- Focus on the code, not the person
- Assume good intentions
- Help others when you can

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

## Recognition

Contributors will be recognized in:
- The project README
- Release notes
- The CONTRIBUTORS file

Thank you for contributing! 🎉
