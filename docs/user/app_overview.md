# App Overview

This document provides an overview of the AI Ops App including critical information and important considerations when applying it to your Nautobot environment.

!!! note
    Throughout this documentation, the terms "app" and "plugin" will be used interchangeably.

## Description

The AI Ops App is a comprehensive AI-powered operations assistant for Nautobot that integrates Large Language Models (LLMs) from multiple providers with the Model Context Protocol (MCP) to provide intelligent automation and assistance capabilities. The app supports a flexible multi-provider architecture (Ollama, OpenAI, Azure AI, Anthropic, HuggingFace, and custom providers) and includes a powerful middleware system for request/response processing. It leverages LangChain and LangGraph frameworks to create conversational AI agents that can interact with various MCP servers and perform complex operational tasks.

### Key Features

- **AI Chat Assistant**: Interactive chat interface powered by configurable LLM models for conversational interactions
- **Multi-Provider Support**: Use Ollama, OpenAI, Azure AI, Anthropic, HuggingFace, or custom providers
- **LLM Provider Management**: Configure and manage multiple LLM providers with provider-specific settings
- **LLM Model Management**: Configure and manage multiple models from different providers with varying capabilities and settings
- **Middleware System**: Apply middleware chains to models for caching, logging, validation, retry logic, and more
- **MCP Server Integration**: Connect to multiple Model Context Protocol servers for extended functionality
- **Conversation History**: Persistent conversation tracking using Redis-based checkpointing
- **Health Monitoring**: Automatic health checks for MCP servers with status management
- **Background Jobs**: Automated maintenance tasks for checkpoint cleanup and MCP health monitoring
- **Multi-Agent Architecture**: Support for both single and multi-MCP agent configurations
- **Flexible Configuration**: Environment-based configuration supporting LAB, NONPROD, and PROD environments

## Audience (User Personas) - Who should use this App?

This app is designed for:

- **Network Engineers**: Who need AI assistance for network operations, troubleshooting, and automation
- **DevOps Engineers**: Looking to integrate AI capabilities into their infrastructure management workflows
- **Site Reliability Engineers (SREs)**: Requiring intelligent assistance for monitoring and incident response
- **Nautobot Administrators**: Who want to extend Nautobot with AI-powered features
- **Infrastructure Teams**: Seeking to leverage AI for operational insights and automation

## Authors and Maintainers

- **Primary Author**: Kevin Campos (kevin.campos@aa.com)
- **Organization**: American Airlines - Infrastructure Automation Team

## Nautobot Features Used

The AI Ops App leverages the following Nautobot features and capabilities:

### Models

The app introduces five primary models:

- **LLMProvider**: Manages LLM provider configurations (Ollama, OpenAI, Azure AI, Anthropic, HuggingFace, Custom)
- **LLMModel**: Manages LLM model configurations including API keys, endpoints, and parameters for any supported provider
- **MiddlewareType**: Defines middleware types (built-in LangChain or custom) that can be applied to models
- **LLMMiddleware**: Configures middleware instances for specific models with priority-based execution
- **MCPServer**: Manages Model Context Protocol server configurations for extended agent capabilities

### Extras

- **Custom Links**: Available on all model objects
- **Custom Validators**: Validation rules for all model configurations
- **Export Templates**: Data export capabilities for all models
- **GraphQL**: Full GraphQL API support for all models
- **Statuses**: Status tracking for MCP servers (Active, Failed, Maintenance)
- **Webhooks**: Event notifications for all model and server changes
- **Secrets Management**: Integration with Nautobot Secrets for API key storage

### Jobs

- **Cleanup Old Checkpoints**: Scheduled job to maintain conversation history by removing old checkpoints from Redis
- **MCP Server Health Check**: Automated health monitoring for HTTP MCP servers with retry logic and cache invalidation
- **Middleware Cache Invalidation**: Automatic cache clearing when middleware configurations change
- **Default Model Cache Warming**: Pre-loads middleware for newly set default models

### User Interface

- **Navigation Menu**: "AI Platform" tab with sections for:
    - Chat & Assistance: AI Chat Assistant interface
    - Configuration: LLM Providers, LLM Models, Middleware Types, LLM Middleware, and MCP Servers management
- **List Views**: Comprehensive list views with filtering and sorting for all models
- **Detail Views**: Rich detail pages using Nautobot's UI Component Framework
- **Forms**: Create, update, and bulk edit forms for all models

### API Endpoints

- **REST API**: Full REST API for all models via NautobotModelViewSet
  - `/api/plugins/ai-ops/llm-providers/`
  - `/api/plugins/ai-ops/llm-models/`
  - `/api/plugins/ai-ops/middleware-types/`
  - `/api/plugins/ai-ops/llm-middleware/`
  - `/api/plugins/ai-ops/mcp-servers/`
- **Chat API**: POST endpoint for processing chat messages through the AI agent
- **Filtering**: Advanced filtering capabilities using Django Filter
- **Serialization**: Custom serializers for LangGraph-specific data types

### Integration Points

- **Django ORM**: Full database integration with PostgreSQL/MySQL
- **Redis**: Conversation checkpointing, middleware caching, and MCP client caching
- **Celery**: Asynchronous task processing for background jobs
- **Secrets**: Secure API key storage using Nautobot Secrets
- **Multiple LLM Providers**: Extensible provider system with handler classes
