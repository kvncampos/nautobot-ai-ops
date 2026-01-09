# PyPI Publishing Setup

This document describes how the AI Ops app is published to PyPI using GitHub Actions and trusted publishing.

## Overview

The project uses GitHub Actions with PyPI's Trusted Publishing feature to automatically publish releases. This approach follows Python packaging best practices and eliminates the need for long-lived PyPI API tokens.

## Automated Publishing Workflow

The [`publish-pypi.yml`](https://github.com/kvncampos/nautobot-ai-ops/blob/main/.github/workflows/publish-pypi.yml) workflow handles all aspects of building and publishing the package:

### Workflow Triggers

The workflow runs in the following scenarios:

1. **Automatic Publishing to PyPI**: When a GitHub release is published
2. **Manual Testing**: Via workflow dispatch with option to publish to TestPyPI

### Workflow Jobs

#### 1. Build Distribution

- Checks out the repository code
- Sets up Python 3.11 and Poetry
- Builds both wheel and source distributions
- Validates package metadata using `twine check`
- Uploads build artifacts for downstream jobs

#### 2. Publish to PyPI (Production)

- Triggers only when a GitHub release is published
- Downloads the built distributions
- Uses PyPI's Trusted Publishing to upload packages
- Requires no API tokens (uses OIDC)

#### 3. Publish to TestPyPI (Testing)

- Triggers only via manual workflow dispatch
- Allows testing the publishing process before production releases
- Uses TestPyPI's Trusted Publishing

#### 4. Update GitHub Release Notes

- Automatically appends installation instructions to the GitHub release notes
- Runs after successful PyPI publication

## PyPI Trusted Publishing

The workflow uses [Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (OpenID Connect) instead of API tokens. This provides:

- **Enhanced Security**: No long-lived credentials to manage or leak
- **Automatic Rotation**: Authentication tokens are short-lived and automatically managed
- **Audit Trail**: All publishing actions are logged with clear attribution

### Setting Up Trusted Publishing

Repository maintainers need to configure Trusted Publishing on PyPI:

1. **Create the PyPI project** (first release only):
   - Register the package name on PyPI: `nautobot-ai-ops`
   - Or publish the first version manually using `poetry publish`

2. **Configure Trusted Publishing on PyPI**:
   - Go to [PyPI project settings](https://pypi.org/manage/project/nautobot-ai-ops/settings/)
   - Navigate to "Publishing" section
   - Click "Add a new publisher"
   - Enter the following details:
     - **PyPI Project Name**: `nautobot-ai-ops`
     - **Owner**: `kvncampos`
     - **Repository name**: `nautobot-ai-ops`
     - **Workflow name**: `publish-pypi.yml`
     - **Environment name**: `pypi`

3. **Configure Trusted Publishing on TestPyPI** (optional, for testing):
   - Go to [TestPyPI project settings](https://test.pypi.org/manage/project/nautobot-ai-ops/settings/)
   - Follow the same steps as above, but use environment name: `testpypi`

4. **Configure GitHub Environments**:
   - In the repository settings, go to "Environments"
   - Create two environments: `pypi` and `testpypi`
   - Optionally add protection rules (e.g., required reviewers)

## Package Metadata

The package metadata is defined in `pyproject.toml`:

```toml
[tool.poetry]
name = "nautobot-ai-ops"
version = "1.0.0"
description = "AI Ops - Advanced artificial intelligence capabilities for Nautobot"
authors = ["Kevin Campos <kvncampos@duck.com>"]
readme = "README.md"
license = "Apache-2.0"
# ... additional metadata
```

### Best Practices Implemented

1. **Clear Package Name**: Uses `nautobot-ai-ops` for PyPI (follows Nautobot app naming convention)
2. **Comprehensive Metadata**: Includes description, authors, license, homepage, repository, and documentation URLs
3. **Keywords**: Relevant keywords for discoverability on PyPI
4. **Classifiers**: Proper Python version classifiers and development status
5. **README**: Includes detailed README.md with badges and documentation links
6. **License**: Apache-2.0 license properly declared
7. **Version Management**: Uses semantic versioning via Poetry

## Testing the Workflow

Before publishing to production PyPI, you can test the workflow:

1. **Trigger TestPyPI publishing**:
   - Go to Actions tab
   - Select "Publish to PyPI" workflow
   - Click "Run workflow"
   - Check "Publish to TestPyPI"
   - Click "Run workflow"

2. **Verify the test package**:
   - Check [TestPyPI project page](https://test.pypi.org/project/nautobot-ai-ops/)
   - Try installing: `pip install --index-url https://test.pypi.org/simple/ nautobot-ai-ops`

## Release Process

For maintainers publishing a new release:

1. Follow the [Release Checklist](release_checklist.md)
2. Create and publish a GitHub release with a version tag (e.g., `1.0.0`)
3. The workflow automatically triggers and publishes to PyPI
4. Monitor the workflow in the [Actions tab](https://github.com/kvncampos/nautobot-ai-ops/actions/workflows/publish-pypi.yml)
5. Verify the package on [PyPI](https://pypi.org/project/nautobot-ai-ops/)

## Troubleshooting

### Build Failures

If the build step fails:

- Check that all dependencies are properly specified in `pyproject.toml`
- Ensure the version in `pyproject.toml` matches the release tag
- Verify that `poetry.lock` is up to date (`poetry lock --no-update`)

### Publishing Failures

If publishing to PyPI fails:

- Verify Trusted Publishing is configured correctly on PyPI
- Check that the GitHub environment name matches (`pypi` or `testpypi`)
- Ensure the workflow has `id-token: write` permission
- Verify the version doesn't already exist on PyPI (versions cannot be re-uploaded)

### Package Not Found After Publishing

- PyPI can take a few minutes to index new packages
- Check the package appears on [PyPI](https://pypi.org/project/nautobot-ai-ops/)
- Clear pip cache if testing installation: `pip cache purge`

## Manual Publishing

In case automated publishing fails, maintainers can publish manually:

```bash
# Build the package
poetry build

# Verify the package
poetry run twine check dist/*

# Publish to TestPyPI (testing)
poetry run twine upload --repository testpypi dist/*

# Publish to PyPI (production)
poetry publish
```

!!! warning
    Manual publishing requires PyPI credentials. Using the automated workflow with Trusted Publishing is strongly recommended.

## Security Considerations

- Never commit PyPI API tokens or credentials to the repository
- Use Trusted Publishing instead of API tokens whenever possible
- Protect the `pypi` GitHub environment with required reviewers
- Monitor the Actions workflow logs for suspicious activity
- Review and approve any changes to the publishing workflow

## Additional Resources

- [Python Packaging User Guide](https://packaging.python.org/)
- [Poetry Documentation](https://python-poetry.org/docs/)
- [PyPI Trusted Publishing Guide](https://docs.pypi.org/trusted-publishers/)
- [GitHub Actions Security](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
