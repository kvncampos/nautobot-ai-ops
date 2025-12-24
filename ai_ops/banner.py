"""Banner function for AI Ops app."""

from django.urls import reverse
from django.utils.html import format_html
from nautobot.apps.ui import Banner, BannerClassChoices

from ai_ops import models


def banner(context, *args, **kwargs):
    """Display a warning banner on the chat page if no default LLM model is configured.

    Args:
        context: Django request context for the current page.
        *args: Additional positional arguments (unused).
        **kwargs: Additional keyword arguments (unused).

    Returns:
        Banner object if on chat page without default model, None otherwise.
    """
    # Only show banner on the chat widget page
    if context.request.path != reverse("plugins:ai_ops:chat"):
        return None

    # Check if there's a default LLM model configured
    has_default_model = models.LLMModel.objects.filter(is_default=True).exists()

    if not has_default_model:
        # Show warning banner with link to LLM models configuration
        llm_models_url = reverse("plugins:ai_ops:llmmodel_list")
        return Banner(
            content=format_html(
                "<strong>Configuration Required:</strong> No default LLM model is configured. "
                'Please configure a default LLM model in the <a href="{}">LLM Models</a> section '
                "to enable the AI Chat Agent.",
                llm_models_url,
            ),
            banner_class=BannerClassChoices.CLASS_WARNING,
        )

    return None
