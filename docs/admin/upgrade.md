# Upgrading the App

Here you will find any steps necessary to upgrade the App in your Nautobot environment.

## Upgrade Guide

When a new release of the AI Ops app is available, follow these steps to upgrade:

### 1. Update the Package

Upgrade the `ai-ops` package using pip:

```shell
pip install --upgrade ai-ops
```

### 2. Run Migrations

Execute the post-upgrade command to run any database migrations:

```shell
nautobot-server post_upgrade
```

This command will:
- Apply any new database migrations
- Update the schema for LLM models, middleware, and MCP configurations
- Clear caches and regenerate static files

### 3. Restart Services

Restart the Nautobot services to load the updated app:

```shell
sudo systemctl restart nautobot nautobot-worker nautobot-scheduler
```

### 4. Verify Configuration

After upgrading, verify that:
- All LLM models are still configured correctly
- Middleware configurations are intact
- MCP servers are still responding to health checks
- The cleanup job is still scheduled (if it was previously configured)

## Breaking Changes

Refer to the [release notes](release_notes/index.md) for any breaking changes or required configuration updates for the specific version you're upgrading to.
