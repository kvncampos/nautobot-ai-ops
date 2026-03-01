"""Signal handlers for ai_ops.

All default data seeding and scheduled job creation has been moved to Django data
migrations so that each operation runs exactly once on install, is fully reversible,
and never clobbers data that users have intentionally modified:

- ``0006_populate_default_data``       — LLM providers, middleware types, MCPServer /
                                         SystemPrompt statuses and default system prompt.
- ``0008_default_scheduled_jobs``      — MCP Server Health Check, Hourly Checkpoint
                                         Cleanup, and Chat Session Cleanup scheduled jobs.

This file is intentionally empty of business logic.  It is kept so that
``__init__.py`` import paths remain stable.
"""
