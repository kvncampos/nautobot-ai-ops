# App Overview

This document provides an overview of the AI Ops App including critical information and important considerations when applying it to your Nautobot environment.

!!! note
    Throughout this documentation, the terms "app" and "plugin" will be used interchangeably.

## Description

The AI Ops App is a comprehensive AI-powered operations assistant for Nautobot that integrates Large Language Models (LLMs) with the Model Context Protocol (MCP) to provide intelligent automation and assistance capabilities. The app leverages Azure OpenAI's GPT models through LangChain and LangGraph frameworks to create conversational AI agents that can interact with various MCP servers and perform complex operational tasks.

### Key Features

- **AI Chat Assistant**: Interactive chat interface powered by Azure OpenAI models for conversational interactions
- **LLM Model Management**: Configure and manage multiple Azure OpenAI models with different capabilities and settings
- **MCP Server Integration**: Connect to multiple Model Context Protocol servers for extended functionality
- **Conversation History**: Persistent conversation tracking using Redis-based checkpointing
- **Health Monitoring**: Automatic health checks for MCP servers with status management
- **Background Jobs**: Automated maintenance tasks for checkpoint cleanup
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

The app introduces two primary models:

- **LLMModel**: Manages Azure OpenAI model configurations including API keys, endpoints, and parameters
- **MCPServer**: Manages Model Context Protocol server configurations for extended agent capabilities

### Extras

- **Custom Links**: Available on LLMModel and MCPServer objects
- **Custom Validators**: Validation rules for model configurations
- **Export Templates**: Data export capabilities for models
- **GraphQL**: Full GraphQL API support for all models
- **Statuses**: Status tracking for MCP servers (Healthy, Failed, Maintenance)
- **Webhooks**: Event notifications for model and server changes
- **Secrets Management**: Integration with Nautobot Secrets for API key storage

### Jobs

- **Cleanup Old Checkpoints**: Scheduled job to maintain conversation history by removing old checkpoints from Redis

### User Interface

- **Navigation Menu**: "AI Platform" tab with sections for:
    - Chat & Assistance: AI Chat Assistant interface
    - Configuration: LLM Models and MCP Servers management
- **List Views**: Comprehensive list views with filtering and sorting
- **Detail Views**: Rich detail pages using Nautobot's UI Component Framework
- **Forms**: Create, update, and bulk edit forms for all models

### API Endpoints

- **REST API**: Full REST API for all models via NautobotModelViewSet
- **Chat API**: POST endpoint for processing chat messages through the AI agent
- **Filtering**: Advanced filtering capabilities using Django Filter
- **Serialization**: Custom serializers for LangGraph-specific data types

### Integration Points

- **Django ORM**: Full database integration with PostgreSQL/MySQL
- **Redis**: Conversation checkpointing and caching
- **Celery**: Asynchronous task processing for background jobs
- **Secrets**: Secure API key storage using Nautobot Secrets
