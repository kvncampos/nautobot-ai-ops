# Uninstall the App from Nautobot

Here you will find any steps necessary to cleanly remove the App from your Nautobot environment.

## Database Cleanup

Prior to removing the app from the `nautobot_config.py`, run the following command to roll back any migration specific to this app.

```shell
nautobot-server migrate ai_ops zero
```

!!! info "Database Objects Removed"
    The migration rollback will remove all AI Ops-specific database objects including:
    - LLM Providers, Models, and Middleware configurations
    - MCP Server configurations
    - Conversation checkpoints stored in Redis
    - Any custom webhooks or relationships tied to AI Ops models

## Clear Redis Cache

After the migration, clear any remaining conversation checkpoints from Redis:

```shell
# Clear the LangGraph checkpoint database
redis-cli -n 2 FLUSHDB
```

## Remove App configuration

Remove the configuration you added in `nautobot_config.py` from `PLUGINS` & `PLUGINS_CONFIG`.

## Uninstall the package

```bash
$ pip3 uninstall ai-ops
```
