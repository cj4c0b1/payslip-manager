# Contributing to Payslip Manager

Thank you for your interest in contributing to Payslip Manager! This document outlines the process for contributing to our project.

## Table of Contents
- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Git Flow Guide](#git-flow-guide)
- [Pull Request Process](#pull-request-process)
- [Code Style](#code-style)
- [Testing](#testing)
- [Reporting Issues](#reporting-issues)

## Code of Conduct

This project adheres to the [Contributor Covenant](https://www.contributor-covenant.org/version/2/0/code_of_conduct/). By participating, you are expected to uphold this code.

## Getting Started

1. **Fork** the repository on GitHub
2. **Clone** your fork locally
   ```bash
   git clone git@github.com:your-username/payslip-manager.git
   cd payslip-manager
   ```
3. **Set up** the development environment
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

## Development Workflow

We use Git Flow for our branching model. Here's how it works:

### Git Flow Guide

#### 1. Starting a New Feature

```bash
# Create and switch to a new feature branch
git flow feature start feature-name

# Work on your feature, make commits
git add .
git commit -m "Implement feature X"

# Push the feature branch to remote
git flow feature publish feature-name
```

#### 2. Finishing a Feature

```bash
# Merge the feature into develop and delete the feature branch
git flow feature finish feature-name

# Push changes to develop
git push origin develop
```

#### 3. Starting a Release

```bash
# Create a release branch
git flow release start 1.2.0

# Bump version numbers, update changelog, etc.
# Then commit the changes
git commit -am "Bump version to 1.2.0"

# Publish the release branch
git flow release publish 1.2.0
```

#### 4. Finishing a Release

```bash
# Finish the release (creates tag, merges to main and develop)
git flow release finish '1.2.0'

# Push the tag
git push origin --tags

# Push the changes to main and develop
git push origin main develop
```

#### 5. Hotfixes

```bash
# Create a hotfix branch from main
git flow hotfix start 1.2.1

# Make your fixes and commit
git commit -am "Fix critical bug in login"

# Finish the hotfix
git flow hotfix finish 1.2.1

# Push the changes and tags
git push origin main develop --tags
```

## Pull Request Process

1. Fork the repository and create your branch from `develop`.
2. If you've added code that should be tested, add tests.
3. Ensure the test suite passes.
4. Make sure your code lints.
5. Issue that pull request!

### Pull Request Requirements
- Reference any related issues in your PR description
- Include screenshots if your PR includes visual changes
- Update the documentation if needed
- Ensure all tests pass

## Code Style

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) for Python code
- Use type hints for all function parameters and return values
- Document all public functions and classes with docstrings
- Keep lines under 88 characters (Black default)

## Testing

Before submitting a pull request, please ensure:

1. All tests pass:
   ```bash
   pytest
   ```
2. Code is properly formatted:
   ```bash
   black .
   ```
3. No linting issues:
   ```bash
   flake8
   ```

## Reporting Issues

When creating an issue, please include:
- A clear title and description
- Steps to reproduce the issue
- Expected vs actual behavior
- Screenshots if applicable
- Your environment details (OS, Python version, etc.)

## License

By contributing, you agree that your contributions will be licensed under the project's [LICENSE](LICENSE) file.
