"""Navigation menu items for AI Platform."""

from nautobot.apps.ui import NavMenuAddButton, NavMenuGroup, NavMenuItem, NavMenuTab

# User-facing features
chat_and_assistance_items = (
    NavMenuItem(
        link="plugins:ai_ops:chat",
        name="AI Chat Assistant",
        permissions=["ai_ops.view_mcpserver"],
    ),
    # TODO: Add Conversation History view when implemented
    # NavMenuItem(
    #     link="plugins:ai_ops:conversation_history",
    #     name="Chat History",
    #     permissions=["ai_ops.view_conversationhistory"],
    # ),
)


# LLM Model configuration
llm_configuration_items = (
    NavMenuItem(
        link="plugins:ai_ops:llmprovider_list",
        name="LLM Providers",
        permissions=["ai_ops.view_llmprovider"],
        buttons=(
            NavMenuAddButton(
                link="plugins:ai_ops:llmprovider_add",
                permissions=["ai_ops.add_llmprovider"],
            ),
        ),
    ),
    NavMenuItem(
        link="plugins:ai_ops:llmmodel_list",
        name="LLM Models",
        permissions=["ai_ops.view_llmmodel"],
        buttons=(
            NavMenuAddButton(
                link="plugins:ai_ops:llmmodel_add",
                permissions=["ai_ops.add_llmmodel"],
            ),
        ),
    ),
)

# Middleware configuration
middleware_items = (
    NavMenuItem(
        link="plugins:ai_ops:middlewaretype_list",
        name="Middleware Types",
        permissions=["ai_ops.view_middlewaretype"],
        buttons=(
            NavMenuAddButton(
                link="plugins:ai_ops:middlewaretype_add",
                permissions=["ai_ops.add_middlewaretype"],
            ),
        ),
    ),
    NavMenuItem(
        link="plugins:ai_ops:llmmiddleware_list",
        name="LLM Middleware",
        permissions=["ai_ops.view_llmmiddleware"],
        buttons=(
            NavMenuAddButton(
                link="plugins:ai_ops:llmmiddleware_add",
                permissions=["ai_ops.add_llmmiddleware"],
            ),
        ),
    ),
)

# MCP Server configuration
mcp_items = (
    NavMenuItem(
        link="plugins:ai_ops:mcpserver_list",
        name="MCP Servers",
        permissions=["ai_ops.view_mcpserver"],
        buttons=(
            NavMenuAddButton(
                link="plugins:ai_ops:mcpserver_add",
                permissions=["ai_ops.add_mcpserver"],
            ),
        ),
    ),
)

menu_items = (
    NavMenuTab(
        name="AI Platform",
        groups=(
            NavMenuGroup(
                name="Chat & Assistance",
                weight=100,
                items=chat_and_assistance_items,
            ),
            NavMenuGroup(
                name="LLM",
                weight=200,
                items=llm_configuration_items,
            ),
            NavMenuGroup(
                name="Middleware",
                weight=300,
                items=middleware_items,
            ),
            NavMenuGroup(
                name="MCP Servers",
                weight=400,
                items=mcp_items,
            ),
        ),
    ),
)
