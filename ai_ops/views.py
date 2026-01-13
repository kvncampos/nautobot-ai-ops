"""Views for ai_ops."""

import logging

from asgiref.sync import sync_to_async
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from nautobot.apps.config import get_app_settings_or_config
from nautobot.apps.ui import (
    Button,
    ButtonColorChoices,
    ObjectDetailContent,
    ObjectFieldsPanel,
    ObjectTextPanel,
    SectionChoices,
)
from nautobot.apps.views import GenericView, NautobotUIViewSet

from ai_ops import filters, forms, models, tables
from ai_ops.agents.multi_mcp_agent import process_message
from ai_ops.api import serializers
from ai_ops.helpers.common.constants import ErrorMessages
from ai_ops.helpers.common.enums import NautobotEnvironment
from ai_ops.helpers.common.helpers import get_environment

logger = logging.getLogger(__name__)


class LLMProviderUIViewSet(NautobotUIViewSet):
    """ViewSet for Provider views."""

    bulk_update_form_class = forms.LLMProviderBulkEditForm
    filterset_class = filters.LLMProviderFilterSet
    filterset_form_class = forms.LLMProviderFilterForm
    form_class = forms.LLMProviderForm
    lookup_field = "pk"
    queryset = models.LLMProvider.objects.all()
    serializer_class = serializers.LLMProviderSerializer
    table_class = tables.LLMProviderTable
    object_detail_content = ObjectDetailContent(
        panels=[
            ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields="__all__",
            ),
        ],
    )


class LLMModelUIViewSet(NautobotUIViewSet):
    """ViewSet for LLMModel views."""

    bulk_update_form_class = forms.LLMModelBulkEditForm
    filterset_class = filters.LLMModelFilterSet
    filterset_form_class = forms.LLMModelFilterForm
    form_class = forms.LLMModelForm
    lookup_field = "pk"
    queryset = models.LLMModel.objects.all()
    serializer_class = serializers.LLMModelSerializer
    table_class = tables.LLMModelTable

    # Here is an example of using the UI  Component Framework for the detail view.
    # More information can be found in the Nautobot documentation:
    # https://docs.nautobot.com/projects/core/en/stable/development/core/ui-component-framework/
    object_detail_content = ObjectDetailContent(
        panels=[
            ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields="__all__",
                # Alternatively, you can specify a list of field names:
                # fields=[
                #     "name",
                #     "description",
                # ],
                # Some fields may require additional configuration, we can use value_transforms
                # value_transforms={
                #     "name": [helpers.bettertitle]
                # },
            ),
            # If there is a ForeignKey or M2M with this model we can use ObjectsTablePanel
            # to display them in a table format.
            # ObjectsTablePanel(
            # weight=200,
            # section=SectionChoices.RIGHT_HALF,
            # table_class=tables.AIModelsTable,
            # You will want to filter the table using the related_name
            # filter="aimodelss",
            # ),
        ],
    )


class MiddlewareTypeUIViewSet(NautobotUIViewSet):
    """ViewSet for MiddlewareType views."""

    bulk_update_form_class = forms.MiddlewareTypeBulkEditForm
    filterset_class = filters.MiddlewareTypeFilterSet
    filterset_form_class = forms.MiddlewareTypeFilterForm
    form_class = forms.MiddlewareTypeForm
    lookup_field = "pk"
    queryset = models.MiddlewareType.objects.all()
    serializer_class = serializers.MiddlewareTypeSerializer
    table_class = tables.MiddlewareTypeTable

    object_detail_content = ObjectDetailContent(
        panels=[
            ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields="__all__",
            ),
        ],
    )


class LLMMiddlewareUIViewSet(NautobotUIViewSet):
    """ViewSet for LLMMiddleware views."""

    bulk_update_form_class = forms.LLMMiddlewareBulkEditForm
    filterset_class = filters.LLMMiddlewareFilterSet
    filterset_form_class = forms.LLMMiddlewareFilterForm
    form_class = forms.LLMMiddlewareForm
    lookup_field = "pk"
    queryset = models.LLMMiddleware.objects.all()
    serializer_class = serializers.LLMMiddlewareSerializer
    table_class = tables.LLMMiddlewareTable

    # Custom templates with JavaScript for dynamic config population
    create_template_name = "ai_ops/llmmiddleware_create.html"
    update_template_name = "ai_ops/llmmiddleware_edit.html"

    object_detail_content = ObjectDetailContent(
        panels=[
            ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields="__all__",
            ),
        ],
    )


class AIChatBotGenericView(GenericView):
    """View for displaying LLMChatBot."""

    template_name = "ai_ops/chat_widget.html"

    async def get(self, request, *args, **kwargs):
        """Render the chat widget template."""
        try:
            # Check if there's a default LLM model configured
            has_default_model = await sync_to_async(models.LLMModel.objects.filter(is_default=True).exists)()

            # Check if there are any healthy MCP servers
            has_healthy_mcp = await sync_to_async(models.MCPServer.objects.filter(status__name="Healthy").exists)()

            # Check if there are any MCP servers at all
            has_any_mcp = await sync_to_async(models.MCPServer.objects.exists)()

            # Get chat session TTL from Constance config (in minutes)
            chat_session_ttl_minutes = await sync_to_async(get_app_settings_or_config)(
                "ai_ops", "chat_session_ttl_minutes"
            )

            # Chat is enabled only if we have a default model (MCP server no longer required)
            chat_enabled = has_default_model

            # Get list of enabled providers for admin provider selection
            # Only staff users can select providers; normal users use default
            enabled_providers = []
            is_admin = request.user.is_staff
            if is_admin:
                providers = await sync_to_async(list)(models.LLMProvider.objects.filter(is_enabled=True))
                # get_name_display() is a Django auto-generated method for CharField with choices
                enabled_providers = [
                    {"name": provider.name, "get_name_display": provider.get_name_display()}  # type: ignore[attr-defined]
                    for provider in providers
                ]

            # You can pass any context data needed for your chatbot template
            context = {
                "title": "LLM ChatBot",
                "chat_enabled": chat_enabled,
                "has_default_model": has_default_model,
                "has_healthy_mcp": has_healthy_mcp,
                "has_any_mcp": has_any_mcp,
                "is_admin": is_admin,
                "enabled_providers": enabled_providers,
                "chat_session_ttl_minutes": chat_session_ttl_minutes,
                # Add other context variables as needed
            }
            return await sync_to_async(render)(request, self.template_name, context)

        except RuntimeError as e:
            if "cannot schedule new futures after interpreter shutdown" in str(e):
                logger.warning(f"Cannot render chat view during interpreter shutdown: {e}")
                # Return a simple error page instead of trying to render the full template
                return HttpResponse(
                    "<html><body><h1>Service Unavailable</h1>"
                    "<p>The application is currently shutting down. Please try again in a moment.</p>"
                    "</body></html>",
                    status=503,
                )
            else:
                raise


# ============================================================================
# Chat API Endpoints
# ============================================================================


class ChatMessageView(GenericView):
    """Handle chat message processing via agent with checkpointed conversation history."""

    async def post(self, request, *args, **kwargs):
        """Process user message through LangGraph agent with PostgreSQL checkpointing.

        Conversation history is automatically managed by LangGraph's checkpointer.
        Each session gets a unique thread_id for conversation isolation.

        Query Parameters:
            message (str): User's message to process
            provider (str, optional): Provider name override (only for admin users)
                                     If not provided, uses default provider

        Returns JSON with agent response or error.
        """
        try:
            # Get user message
            user_message = request.POST.get("message", "").strip()
            if not user_message:
                return JsonResponse({"error": "No message provided"}, status=400)

            # Get optional provider override (only allow admins to select provider)
            provider_override = None
            if request.user.is_staff:
                provider_override = request.POST.get("llm_provider", "").strip()
                # Validate provider exists and is enabled if specified
                if provider_override:
                    provider_exists = await sync_to_async(
                        models.LLMProvider.objects.filter(name=provider_override, is_enabled=True).exists
                    )()
                    if not provider_exists:
                        return JsonResponse(
                            {"error": f"Provider '{provider_override}' not found or is disabled"}, status=400
                        )
                    logger.debug(f"Admin {request.user.username} selected provider: {provider_override}")
            elif request.POST.get("llm_provider"):
                # Non-admin users cannot select provider
                logger.warning(
                    f"Non-admin user {request.user.username} attempted to select provider: "
                    f"{request.POST.get('llm_provider')}"
                )
                return JsonResponse({"error": "Only administrators can select a specific provider"}, status=403)

            # Ensure session exists
            if not request.session.session_key:
                await request.session.acreate()

            # Use session key as thread_id for conversation isolation
            thread_id = request.session.session_key

            # Get username for logging (use 'anonymous' if not authenticated)
            username = request.user.username if request.user.is_authenticated else None

            # Process message through checkpointed agent with optional provider override
            # Checkpointer automatically loads/saves conversation history
            response_text = await process_message(
                user_message, thread_id, provider=provider_override, username=username
            )

            return JsonResponse({"response": response_text, "error": None})

        except Exception as e:
            # Log full traceback for debugging
            import traceback

            logger.error(f"Chat message error: {e!s}\n{traceback.format_exc()}")

            # Only expose exception details in LOCAL environment for security
            env = get_environment()
            if env == NautobotEnvironment.LOCAL:
                error_message = f"Error processing message: {e!s}"
            else:
                error_message = ErrorMessages.CHAT_ERROR

            return JsonResponse({"response": None, "error": error_message}, status=500)


class ChatClearView(GenericView):
    """Clear chat conversation history from checkpointer."""

    def post(self, request, *args, **kwargs):
        """Clear the conversation checkpoint for this session.

        This clears the conversation history for the current session thread,
        allowing the user to start a fresh conversation.

        Note: This is a sync view to avoid asgiref RuntimeError during
        interpreter shutdown. Uses async_to_sync internally.
        """
        try:
            # Get the session thread_id
            thread_id = request.session.session_key

            if not thread_id:
                return JsonResponse({"success": False, "message": "No active session to clear"}, status=400)

            # Import here to avoid circular dependencies
            from asgiref.sync import async_to_sync

            from ai_ops.checkpointer import clear_checkpointer_for_thread

            # Clear the conversation history for this thread
            # Use async_to_sync to call the async function from sync context
            cleared = async_to_sync(clear_checkpointer_for_thread)(thread_id)

            if cleared:
                return JsonResponse({"success": True, "message": "Conversation history cleared successfully"})
            else:
                return JsonResponse({"success": True, "message": "No conversation history to clear"})

        except RuntimeError as e:
            # Handle interpreter shutdown gracefully
            if "cannot schedule new futures after interpreter shutdown" in str(e):
                logger.warning(f"Cannot clear conversation during shutdown: {str(e)}")
                return JsonResponse(
                    {"success": True, "message": "Server is shutting down, conversation will be cleared on restart"},
                    status=200,
                )
            else:
                logger.error(f"Runtime error clearing conversation: {str(e)}")
                # Only expose exception details in LOCAL environment for security
                env = get_environment()
                if env == NautobotEnvironment.LOCAL:
                    error_message = str(e)
                else:
                    error_message = ErrorMessages.CLEAR_CHAT_ERROR
                return JsonResponse({"success": False, "error": error_message}, status=500)
        except Exception as e:
            import traceback

            logger.error(f"Failed to clear conversation: {str(e)}\n{traceback.format_exc()}")

            # Only expose exception details in LOCAL environment for security
            env = get_environment()
            if env == NautobotEnvironment.LOCAL:
                error_message = str(e)
            else:
                error_message = ErrorMessages.CLEAR_CHAT_ERROR

            return JsonResponse({"success": False, "error": error_message}, status=500)


class ClearMCPCacheView(GenericView):
    """Clear MCP client cache (superuser only)."""

    @method_decorator(user_passes_test(lambda u: u.is_superuser))
    def dispatch(self, *args, **kwargs):
        """Ensure only superusers can access this view."""
        return super().dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        """Clear the MCP client application cache.

        Note: This is a sync view to avoid asgiref RuntimeError during
        interpreter shutdown. Uses async_to_sync internally.
        """
        try:
            # Import here to avoid circular dependencies
            from asgiref.sync import async_to_sync

            from ai_ops.agents.multi_mcp_agent import clear_mcp_cache

            # Clear the cache using async_to_sync
            cleared_count = async_to_sync(clear_mcp_cache)()

            # Log the action (system action, not an object change)
            logger.info(f"User {request.user.username} cleared MCP client cache for {cleared_count} healthy servers")

            return JsonResponse({"success": True, "cleared_count": cleared_count})

        except RuntimeError as e:
            # Handle interpreter shutdown gracefully
            if "cannot schedule new futures after interpreter shutdown" in str(e):
                logger.warning(f"Cannot clear MCP cache during shutdown: {str(e)}")
                return JsonResponse(
                    {"success": True, "message": "Server is shutting down, cache will be cleared on restart"},
                    status=200,
                )
            else:
                logger.error(f"Runtime error clearing MCP cache: {str(e)}")
                env = get_environment()
                if env == NautobotEnvironment.LOCAL:
                    error_message = f"Failed to clear cache: {str(e)}"
                else:
                    error_message = ErrorMessages.CACHE_CLEAR_ERROR
                return JsonResponse({"success": False, "error": error_message}, status=500)

        except Exception as e:
            import traceback

            logger.error(f"Failed to clear MCP cache: {str(e)}\n{traceback.format_exc()}")

            # Only expose exception details in LOCAL environment for security
            env = get_environment()
            if env == NautobotEnvironment.LOCAL:
                error_message = f"Failed to clear cache: {str(e)}"
            else:
                error_message = ErrorMessages.CACHE_CLEAR_ERROR

            return JsonResponse({"success": False, "error": error_message}, status=500)


# ============================================================================
# MCP Servers API Endpoints
# ============================================================================
class MCPServerUIViewSet(NautobotUIViewSet):
    """ViewSet for MCP Servers views."""

    bulk_update_form_class = forms.MCPServerBulkEditForm
    filterset_class = filters.MCPServerFilterSet
    filterset_form_class = forms.MCPServerFilterForm
    form_class = forms.MCPServerForm
    lookup_field = "pk"
    queryset = models.MCPServer.objects.all()
    serializer_class = serializers.MCPServerSerializer
    table_class = tables.MCPServerTable

    object_detail_content = ObjectDetailContent(
        panels=[
            ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields="__all__",
            ),
        ],
        extra_buttons=[
            Button(
                weight=100,
                label="Check Health",
                icon="mdi-heart-pulse",
                color=ButtonColorChoices.BLUE,
                template_path="ai_ops/components/button/mcp_health_check.html",
                javascript_template_path="ai_ops/extras/mcp_health_check_button.js",
                attributes={"onClick": "checkMCPHealth(event)"},
            ),
        ],
    )


# ============================================================================
# System Prompts API Endpoints
# ============================================================================
class SystemPromptUIViewSet(NautobotUIViewSet):
    """ViewSet for SystemPrompt views."""

    bulk_update_form_class = forms.SystemPromptBulkEditForm
    filterset_class = filters.SystemPromptFilterSet
    filterset_form_class = forms.SystemPromptFilterForm
    form_class = forms.SystemPromptForm
    lookup_field = "pk"
    queryset = models.SystemPrompt.objects.all()
    serializer_class = serializers.SystemPromptSerializer
    table_class = tables.SystemPromptTable

    # Custom template to include CSS for scrollable markdown preview
    retrieve_template_name = "ai_ops/systemprompt_retrieve.html"

    object_detail_content = ObjectDetailContent(
        panels=[
            ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields=[
                    "name",
                    "status",
                    "version",
                    "is_file_based",
                    "prompt_file_name",
                ],  # pyright: ignore[reportArgumentType]
            ),
            ObjectTextPanel(
                weight=200,
                section=SectionChoices.RIGHT_HALF,
                label="Prompt Preview (Rendered Markdown)",
                body_id="prompt-preview-panel",
                object_field="rendered_prompt",
                render_as=ObjectTextPanel.RenderOptions.MARKDOWN,
                render_placeholder=True,
            ),
        ],
    )
