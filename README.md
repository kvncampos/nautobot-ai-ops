# AI Ops

<!--
Developer Note - Remove Me!

The README will have certain links/images broken until the PR is merged into `main`. Update the GitHub links with whichever branch you're using if different.

The logo of the project is a placeholder (docs/images/icon-ai-ops.png) - please replace it with your app icon, making sure it's at least 200x200px and has a transparent background!

To avoid extra work and temporary links, make sure that publishing docs (or merging a PR) is done at the same time as setting up the docs site on RTD, then test everything.
-->

<p align="center">
  <img src="https://raw.githubusercontent.com/kvncampos/nautobot-ai-ops/main/docs/images/icon-ai-ops.png" class="logo" height="200px">
  <br>
  <a href="https://github.com/kvncampos/nautobot-ai-ops/actions/workflows/ci.yml"><img src="https://github.com/kvncampos/nautobot-ai-ops/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI Status"></a>
  <a href="https://github.com/kvncampos/nautobot-ai-ops/actions/workflows/deploy-docs.yml"><img src="https://github.com/kvncampos/nautobot-ai-ops/actions/workflows/deploy-docs.yml/badge.svg?branch=main" alt="Docs Deploy Status"></a>
  <a href="https://pypi.org/project/nautobot-ai-ops/"><img src="https://img.shields.io/pypi/v/nautobot-ai-ops" alt="PyPI Version"></a>
  <a href="https://pypi.org/project/nautobot-ai-ops/"><img src="https://img.shields.io/pypi/pyversions/nautobot-ai-ops" alt="Python Versions"></a>
  <br>
  <a href="https://kvncampos.github.io/nautobot-ai-ops/"><img src="https://img.shields.io/badge/docs-live-brightgreen" alt="GitHub Pages"></a>
  <a href="https://pypi.org/project/nautobot-ai-ops/"><img src="https://img.shields.io/pypi/dm/nautobot-ai-ops" alt="PyPI Downloads"></a>
  <a href="https://github.com/kvncampos/nautobot-ai-ops/blob/main/LICENSE"><img src="https://img.shields.io/pypi/l/nautobot-ai-ops" alt="License"></a>
  <br>
  An <a href="https://networktocode.com/nautobot-apps/">App</a> for <a href="https://nautobot.com/">Nautobot</a>.
</p>

## Overview

The AI Ops app brings advanced artificial intelligence capabilities to Nautobot through a flexible multi-provider architecture and the Model Context Protocol (MCP). This app provides an intelligent chat assistant that can interact with your Nautobot environment, external MCP servers, and other integrated systems to help automate operational tasks, answer questions, and provide insights based on your network infrastructure data.

At its core, AI Ops leverages LangGraph and LangChain to orchestrate conversations with Large Language Models (LLMs) from multiple providers (Ollama, OpenAI, Azure AI, Anthropic, HuggingFace, and custom providers), maintaining conversation context through checkpointed sessions stored in Redis. The app supports flexible LLM provider and model management, allowing administrators to define multiple providers and models for various use cases. A powerful middleware system enables request/response processing with features like caching, logging, validation, and retry logic. The multi-MCP server architecture enables the AI assistant to connect to both internal and external MCP servers, providing extensible tool access for network automation, data retrieval, and operational workflows. Production-ready features include automated health monitoring for MCP servers, middleware cache management, automatic status tracking, conversation persistence, and scheduled maintenance tasks to maintain optimal performance.

> **Note**: This project is actively evolving. We're continuously adding new features, providers, and capabilities. Check the [Release Notes](https://kvncampos.github.io/nautobot-ai-ops/admin/release_notes/) for the latest updates and the [GitHub Issues](https://github.com/kvncampos/nautobot-ai-ops/issues) for upcoming features.

### Key Features

- **Multi-Provider LLM Support**: Use models from Ollama (local), OpenAI, Azure AI, Anthropic, HuggingFace, or implement custom providers
- **LLM Provider Management**: Configure and manage multiple LLM providers with provider-specific settings and handler classes
- **LLM Model Management**: Configure multiple models from different providers with varying capabilities, temperature settings, and configurations
- **Middleware System**: Apply middleware chains to models for caching, logging, validation, retry logic, rate limiting, and custom processing
- **Priority-Based Middleware Execution**: Control middleware execution order (1-100) with pre and post-processing phases
- **AI Chat Assistant**: Interactive chat interface that understands and responds to natural language queries about your Nautobot environment
- **MCP Server Integration**: Connect to internal and external Model Context Protocol servers to extend capabilities with custom tools
- **Automated Health Monitoring**: Scheduled health checks for MCP servers with retry logic and automatic cache invalidation
- **Conversation Persistence**: Checkpoint-based conversation management using Redis ensures context is maintained across sessions
- **Secure Configuration**: API keys and credentials managed through Nautobot's Secret objects, never stored directly
- **Scheduled Tasks**: Background jobs for checkpoint cleanup, MCP server health monitoring, and middleware cache management
- **RESTful API**: Full API support for programmatic access to all models (providers, models, middleware, MCP servers)
- **Environment-Aware**: Supports LAB (local development with Ollama), NONPROD, and PROD environments

More screenshots and detailed use cases can be found in the [Using the App](https://kvncampos.github.io/nautobot-ai-ops/user/app_use_cases/) page in the documentation.

## Requirements

- Nautobot 2.4.22+
- Python 3.10 - 3.12
- Redis (for conversation checkpointing and caching)
- At least one LLM provider:
  - **Ollama** (local, free): For development and testing
  - **OpenAI API**: For OpenAI models (requires API key)
  - **Azure OpenAI**: For Azure-hosted models (requires subscription)
  - **Anthropic API**: For Claude models (requires API key)
  - **HuggingFace**: For HuggingFace models (requires API key)
  - **Custom**: Implement your own provider handler
- Optional: MCP servers for extended functionality

## Documentation

Full documentation for this App can be found at [kvncampos.github.io/nautobot-ai-ops](https://kvncampos.github.io/nautobot-ai-ops/):

- [User Guide](https://kvncampos.github.io/nautobot-ai-ops/user/app_overview/) - Overview, Using the App, Getting Started.
- [Administrator Guide](https://kvncampos.github.io/nautobot-ai-ops/admin/install/) - How to Install, Configure, Upgrade, or Uninstall the App.
- [Developer Guide](https://kvncampos.github.io/nautobot-ai-ops/dev/contributing/) - Extending the App, Code Reference, Contribution Guide.
- [Release Notes / Changelog](https://kvncampos.github.io/nautobot-ai-ops/admin/release_notes/).
- [Frequently Asked Questions](https://kvncampos.github.io/nautobot-ai-ops/user/faq/).

### Contributing to the Documentation

You can find all the Markdown source for the App documentation under the [`docs`](https://github.com/kvncampos/nautobot-ai-ops/tree/main/docs) folder in this repository. For simple edits, a Markdown capable editor is sufficient: clone the repository and edit away.

If you need to view the fully-generated documentation site, you can build it with [MkDocs](https://www.mkdocs.org/). A container hosting the documentation can be started using the `invoke` commands (details in the [Development Environment Guide](https://kvncampos.github.io/nautobot-ai-ops/dev/dev_environment/#docker-development-environment)) on [http://localhost:8001](http://localhost:8001). Using this container, as your changes to the documentation are saved, they will be automatically rebuilt and any pages currently being viewed will be reloaded in your browser.

Any PRs with fixes or improvements are very welcome!

## Questions

For any questions or comments, please check the [FAQ](https://kvncampos.github.io/nautobot-ai-ops/user/faq/) first. Feel free to also swing by the [Network to Code Slack](https://networktocode.slack.com/) (channel `#nautobot`), sign up [here](http://slack.networktocode.com/) if you don't have an account.
