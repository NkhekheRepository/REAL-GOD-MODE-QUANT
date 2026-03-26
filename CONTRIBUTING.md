# Contributing to God Mode Quant Trading Orchestrator

Thank you for considering contributing to the God Mode Quant Trading Orchestrator! This document outlines the process for contributing to this project.

## How to Contribute

### Reporting Issues
Before submitting an issue, please check if it has already been reported. When submitting an issue, please include:
- A clear and descriptive title
- Steps to reproduce the issue
- Expected behavior vs. actual behavior
- Relevant log snippets (remove sensitive information)
- Environment details (Docker version, OS, etc.)

### Suggesting Features
Feature requests are welcome! Please provide:
- A clear description of the feature and its benefits
- Any potential implementation considerations
- How it aligns with the project goals

### Submitting Changes
1. Fork the repository on GitHub
2. Create a new branch from `main`: `git checkout -b feature/your-feature-name`
3. Make your changes, following the coding standards below
4. Add tests for any new functionality
5. Ensure all tests pass
6. Commit your changes with a clear commit message
7. Push your branch to your fork
8. Open a Pull Request against the `main` branch

## Coding Standards

### Python Code
- Follow [PEP 8](https://pep8.org/) style guide
- Use 4 spaces for indentation (no tabs)
- Limit line length to 88 characters (Black formatter default)
- Use descriptive names for variables and functions
- Add docstrings to all public modules, functions, and classes
- Use type hints where beneficial

### Git Practices
- Make small, focused commits
- Write clear commit messages in the format: `type(scope): description`
  - Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`
  - Scope: Optional, indicates the part of the codebase affected
  - Example: `feat(trading): add moving average crossover strategy`

### Documentation
- Update README.md if your changes affect usage or configuration
- Add comments to complex code sections
- Keep docstrings up to date with code changes

## Development Setup

### Local Development (Without Docker)
1. Clone your fork: `git clone https://github.com/yourusername/godmode-quant-orchestrator.git`
2. Create a virtual environment: `python -m venv venv`
3. Activate the environment: 
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and configure your settings
6. Run the application: `python main.py`

### Docker Development
1. Ensure Docker and Docker Compose are installed
2. Copy `.env.example` to `.env` and configure your settings
3. Build and run: `docker-compose up --build`
4. View logs: `docker-compose logs -f`

## Testing

Currently, the project has minimal automated tests. As the project grows, we will implement:
- Unit tests for core functionality
- Integration tests for Docker services
- End-to-end tests for critical workflows

Please add tests for any new functionality you implement.

## Code Review Process

All contributions require code review:
1. Pull Requests must be reviewed by at least one maintainer
2. Address all review comments before merging
3. Ensure your branch is up to date with `main` before merging
4. Squash commits if requested by reviewers

## Community

Please follow our [Code of Conduct](CODE_OF_CONDUCT.md) in all interactions with the project.

## Getting Help

If you need help with your contribution:
- Check existing issues and documentation
- Ask questions in the Issues section
- Maintainers will respond to PR comments

Thank you for contributing to the God Mode Quant Trading Orchestrator!