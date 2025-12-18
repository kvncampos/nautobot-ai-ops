# AI Ops

<!--
Developer Note - Remove Me!

The README will have certain links/images broken until the PR is merged into `develop`. Update the GitHub links with whichever branch you're using (main etc.) if different.

The logo of the project is a placeholder (docs/images/icon-ai-ops.png) - please replace it with your app icon, making sure it's at least 200x200px and has a transparent background!

To avoid extra work and temporary links, make sure that publishing docs (or merging a PR) is done at the same time as setting up the docs site on RTD, then test everything.
-->

<p align="center">
  <img src="https://raw.githubusercontent.com/AAInternal/project42_nautobot_ai_ops/develop/docs/images/icon-ai-ops.png" class="logo" height="200px">
  <br>
  <a href="https://github.com/AAInternal/project42_nautobot_ai_ops/actions"><img src="https://github.com/AAInternal/project42_nautobot_ai_ops/actions/workflows/ci.yml/badge.svg?branch=main"></a>
  <a href="https://nautobot-nonprod.aa.com/static/ai_ops/docs/index.html"><img src="https://readthedocs.org/projects/nautobot-app-ai-ops/badge/"></a>
  <br>
  An <a href="https://networktocode.com/nautobot-apps/">App</a> for <a href="https://nautobot.com/">Nautobot</a>.
</p>

## Overview

The AI Ops plugin brings advanced artificial intelligence capabilities to Nautobot through integration with Azure OpenAI and the Model Context Protocol (MCP). This app provides an intelligent chat assistant that can interact with your Nautobot environment, external MCP servers, and other integrated systems to help automate operational tasks, answer questions, and provide insights based on your network infrastructure data.

At its core, AI Ops leverages LangGraph and LangChain to orchestrate conversations with Large Language Models (LLMs), maintaining conversation context through checkpointed sessions stored in Redis. The plugin supports multiple LLM configurations with Azure OpenAI, allowing administrators to define and manage different AI models for various use cases. Additionally, it implements a multi-MCP server architecture that enables the AI assistant to connect to both internal and external MCP servers, providing extensible tool access for network automation, data retrieval, and operational workflows. The plugin includes enterprise features such as health monitoring for MCP servers, automatic status tracking, conversation persistence, and scheduled checkpoint cleanup to maintain optimal performance.

### Key Features

- **AI Chat Assistant**: Interactive chat interface powered by Azure OpenAI that understands and responds to natural language queries about your Nautobot environment
- **Multiple LLM Support**: Configure and manage multiple Azure OpenAI deployments (GPT-4o, GPT-4 Turbo, etc.) with different temperature settings and capabilities
- **MCP Server Integration**: Connect to internal and external Model Context Protocol servers to extend the AI assistant's capabilities with custom tools and integrations
- **Conversation Persistence**: Checkpoint-based conversation management using Redis ensures context is maintained across sessions
- **Health Monitoring**: Automatic health checks and status tracking for MCP servers with configurable endpoints
- **Secure Configuration**: API keys and sensitive credentials managed through Nautobot's Secret objects
- **Scheduled Tasks**: Background jobs for checkpoint cleanup and MCP server health monitoring
- **RESTful API**: Full API support for programmatic access to LLM models and MCP server configurations

More screenshots and detailed use cases can be found in the [Using the App](https://docs.nautobot.com/projects/ai-ops/en/latest/user/app_use_cases/) page in the documentation.

## Requirements

- Nautobot 2.4.22+
- Python 3.10 - 3.12
- Azure OpenAI API access
- Redis (for conversation checkpointing)
- Optional: MCP servers for extended functionality

## Documentation

Full documentation for this App can be found over on the [Nautobot Docs](https://docs.nautobot.com) website:

- [User Guide](https://docs.nautobot.com/projects/ai-ops/en/latest/user/app_overview/) - Overview, Using the App, Getting Started.
- [Administrator Guide](https://docs.nautobot.com/projects/ai-ops/en/latest/admin/install/) - How to Install, Configure, Upgrade, or Uninstall the App.
- [Developer Guide](https://docs.nautobot.com/projects/ai-ops/en/latest/dev/contributing/) - Extending the App, Code Reference, Contribution Guide.
- [Release Notes / Changelog](https://docs.nautobot.com/projects/ai-ops/en/latest/admin/release_notes/).
- [Frequently Asked Questions](https://docs.nautobot.com/projects/ai-ops/en/latest/user/faq/).

### Contributing to the Documentation

You can find all the Markdown source for the App documentation under the [`docs`](https://github.com/AAInternal/project42_nautobot_ai_ops/tree/develop/docs) folder in this repository. For simple edits, a Markdown capable editor is sufficient: clone the repository and edit away.

If you need to view the fully-generated documentation site, you can build it with [MkDocs](https://www.mkdocs.org/). A container hosting the documentation can be started using the `invoke` commands (details in the [Development Environment Guide](https://docs.nautobot.com/projects/ai-ops/en/latest/dev/dev_environment/#docker-development-environment)) on [http://localhost:8001](http://localhost:8001). Using this container, as your changes to the documentation are saved, they will be automatically rebuilt and any pages currently being viewed will be reloaded in your browser.

Any PRs with fixes or improvements are very welcome!

## Questions

For any questions or comments, please check the [FAQ](https://docs.nautobot.com/projects/ai-ops/en/latest/user/faq/) first. Feel free to also swing by the [Network to Code Slack](https://networktocode.slack.com/) (channel `#nautobot`), sign up [here](http://slack.networktocode.com/) if you don't have an account.
