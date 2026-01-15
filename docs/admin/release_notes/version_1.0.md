# v1.0 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

**AI Ops v1.0.0** is the inaugural stable release of the AI Operations application for Nautobot, featuring comprehensive LLM provider integration and multi-agent capabilities.

### Key Features

- **Multi-Provider LLM Support**: Seamless integration with Azure OpenAI, OpenAI, Anthropic, HuggingFace, Ollama, and custom providers
- **LLM Provider Configuration**: Database-driven provider and model management with dynamic configuration
- **Middleware Architecture**: Request/response processing middleware with priority-based execution
- **MCP Server Integration**: Model Context Protocol server support for extended agent capabilities
- **Conversation Checkpointing**: Redis-backed conversation state persistence using LangGraph
- **Rest API**: Comprehensive REST API for LLM operations and model management
- **Health Checks**: Built-in health check system for MCP servers and LLM availability

### Compatibility

- **Nautobot**: 2.4.0 to 3.x.x (tested up to 3.x.x, 4.0.0+ pending testing)
- **Python**: 3.10, 3.11, 3.12, 3.13
- **Databases**: PostgreSQL, MySQL

<!-- towncrier release notes start -->


## [v1.0.6 (2026-01-15)](https://github.com/kvncampos/nautobot-ai-ops/releases/tag/v1.0.6)

### Added

- [#33](https://github.com/kvncampos/nautobot-ai-ops/issues/33) - Updated documentation, updated bootstrap 5 UI and updated default prompt.

## [v1.0.4 (2026-01-13)](https://github.com/kvncampos/nautobot-ai-ops/releases/tag/v1.0.4)

### Added

- [#29](https://github.com/kvncampos/nautobot-ai-ops/issues/29) - Added Dynamic System Prompts feature allowing UI-based management of AI agent prompts with support for template variables ({current_date}, {current_month}, {model_name}), file-based prompts, status-based approval workflow, and model-specific prompt assignment.

### Changed

- [#30](https://github.com/kvncampos/nautobot-ai-ops/issues/30) - Enhanced chat widget markdown rendering with comprehensive CSS styling for tables, code blocks, lists, blockquotes, and all markdown elements. Added intelligent query handling to request clarification for ambiguous identifiers (e.g., "DFW-ATO" could be device/site/circuit) before searching. Improved system prompt with explicit filtering examples for specific items and detailed markdown formatting requirements including proper table syntax with separator rows and blank lines between elements. Added MCP server logging to warn when GET requests are made without filter parameters for debugging LLM behavior.

### Documentation

- [#28](https://github.com/kvncampos/nautobot-ai-ops/issues/28) - Updated documentation to reflect removal of TTL field from LLMMiddleware model and transition to fresh middleware instantiation per request from LangChain graph to prevent state leaks between conversations.

## [v1.0.3 (2026-01-12)](https://github.com/kvncampos/nautobot-ai-ops/releases/tag/v1.0.3)

### Added

- [#27](https://github.com/kvncampos/nautobot-ai-ops/issues/27) - Added `mcp_nautobot_query` tool to MCP server for simplified Nautobot API queries with automatic endpoint discovery, eliminating the need for agents to manually chain schema discovery and API request tools.
- [#27](https://github.com/kvncampos/nautobot-ai-ops/issues/27) - 
- [#27](https://github.com/kvncampos/nautobot-ai-ops/issues/27) - Enhanced system prompt with explicit tool workflow instructions requiring agents to use discovery tools before making API requests, preventing guessed URL 404 errors.
- [#27](https://github.com/kvncampos/nautobot-ai-ops/issues/27) - 
- [#27](https://github.com/kvncampos/nautobot-ai-ops/issues/27) - Improved `mcp_nautobot_dynamic_api_request` to return helpful guidance on 404 errors instead of raising exceptions, allowing agents to self-correct.

### Documentation

- [#24](https://github.com/kvncampos/nautobot-ai-ops/issues/24) - Added comprehensive configuration guides for all 6 LLM providers (Ollama, OpenAI, Azure AI, Anthropic, HuggingFace, Custom) with prerequisites, authentication methods, and deployment strategies.
- [#24](https://github.com/kvncampos/nautobot-ai-ops/issues/24) - 
- [#24](https://github.com/kvncampos/nautobot-ai-ops/issues/24) - Added middleware configuration guide covering built-in middleware (Cache, Retry, Logging, RateLimit, Validation) and custom middleware examples (PII Redaction, Cost Tracking, Circuit Breaker) with priority-based execution and performance optimization.
- [#24](https://github.com/kvncampos/nautobot-ai-ops/issues/24) - 
- [#24](https://github.com/kvncampos/nautobot-ai-ops/issues/24) - Added MCP Server configuration guide with 6 server type implementations including Python/FastAPI examples, Docker deployment, health monitoring, and security patterns.
- [#24](https://github.com/kvncampos/nautobot-ai-ops/issues/24) - 
- [#24](https://github.com/kvncampos/nautobot-ai-ops/issues/24) - Expanded external_interactions.md to cover all 6 LLM providers instead of Azure-only with data flows and authentication details.
- [#24](https://github.com/kvncampos/nautobot-ai-ops/issues/24) - 
- [#24](https://github.com/kvncampos/nautobot-ai-ops/issues/24) - Enhanced app_getting_started.md with multi-provider quick start options and references to comprehensive configuration guides.
- [#24](https://github.com/kvncampos/nautobot-ai-ops/issues/24) - 
- [#24](https://github.com/kvncampos/nautobot-ai-ops/issues/24) - Improved app_use_cases.md with detailed provider selection guide, cost optimization strategies, and real-world deployment examples.
- [#24](https://github.com/kvncampos/nautobot-ai-ops/issues/24) - 
- [#24](https://github.com/kvncampos/nautobot-ai-ops/issues/24) - Reorganized mkdocs navigation structure with new "Configuration Guides" subsection for better documentation hierarchy.
- [#24](https://github.com/kvncampos/nautobot-ai-ops/issues/24) - 
- [#24](https://github.com/kvncampos/nautobot-ai-ops/issues/24) - Updated README homepage to clarify production-ready features (replacing "Enterprise features") and added project evolution note indicating continuous development.

### Housekeeping

- [#towncrier-automation](https://github.com/kvncampos/nautobot-ai-ops/issues/towncrier-automation) - Added automatic synchronization of fallback version strings in ai_ops/__init__.py when running towncrier release notes generation.

## [v1.0.2 (2026-01-09)](https://github.com/kvncampos/nautobot-ai-ops/releases/tag/v1.0.2)

### Added

- [#middleware-config-improvements](https://github.com/kvncampos/nautobot-ai-ops/issues/middleware-config-improvements) - Added default configuration templates for all middleware types, displaying type indicators in the LLMMiddleware form to guide users on expected parameter types when configuring middleware instances.

### Changed

- [#workflow-update](https://github.com/kvncampos/nautobot-ai-ops/issues/workflow-update) - Modernized repository branching strategy to use single main branch with beta pre-releases (1.0.0b1 format), updated all documentation and GitHub Actions workflows to support simplified release process, and enforced squash merge for all PRs to maintain clean commit history.

### Fixed

- Added explicit Download, Bug Tracker, and Changelog URLs to package metadata to improve PyPI integration.

## [v1.0.1 (2026-01-08)](https://github.com/kvncampos/nautobot-ai-ops/releases/tag/v1.0.1)

### Added

- [#pypi-publish](https://github.com/kvncampos/nautobot-ai-ops/issues/pypi-publish) - Added automated PyPI publishing workflow using GitHub Actions with trusted publishing for secure package distribution following Python best practices.
- [#8](https://github.com/kvncampos/nautobot-ai-ops/issues/8) - Fixed event loop blocking by converting synchronous database and HTTP calls to async in view methods (AIChatBotGenericView.get(), ChatMessageView.post(), MCPServerViewSet.health_check()).

## [v1.0.0 (2025-12-19)](https://github.com/kvncampos/nautobot-ai-ops/releases/tag/v1.0.0)

No significant changes.
