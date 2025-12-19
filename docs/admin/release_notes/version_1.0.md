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


## [v1.0.0 (2025-12-19)](https://github.com/kvncampos/nautobot_ai_ops/releases/tag/v1.0.0)

No significant changes.
