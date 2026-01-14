"""Helper functions for loading system prompts."""

import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def get_active_prompt(llm_model) -> str:
    """Load the active system prompt for an LLM model.

    Retrieves the prompt using the following fallback hierarchy:
    1. Model's assigned SystemPrompt (if status is 'Approved')
    2. Global default SystemPrompt (is_file_based=True, status='Approved')
    3. Code-based fallback: get_prompt()

    For file-based prompts, dynamically imports and calls the prompt function.
    For database prompts, renders runtime variables in prompt_text.

    Args:
        llm_model: The LLMModel instance to get the prompt for.

    Returns:
        str: The rendered system prompt content.
    """
    from ai_ops.models import SystemPrompt

    prompt_obj = None
    model_name = llm_model.name if llm_model else "Unknown"

    logger.debug(f"Loading system prompt for model: {model_name}")

    # 1. Check if model has an assigned prompt with Approved status
    if llm_model and hasattr(llm_model, "system_prompt") and llm_model.system_prompt:
        prompt_obj = llm_model.system_prompt
        logger.debug(
            f"Found prompt '{prompt_obj.name}' with status '{prompt_obj.status.name if prompt_obj.status else 'None'}'"
        )
        if prompt_obj.status and prompt_obj.status.name != "Approved":
            logger.debug(
                f"System prompt '{prompt_obj.name}' has status '{prompt_obj.status.name}', not 'Approved'. Falling back."
            )
            prompt_obj = None
    else:
        logger.debug(f"No system_prompt assigned to model '{model_name}'")

    # 2. If no model-specific prompt, try to find a global approved prompt
    if not prompt_obj:
        prompt_obj = (
            SystemPrompt.objects.filter(status__name="Approved", is_file_based=True).order_by("-version").first()
        )
        logger.debug(f"Using global fallback prompt: {prompt_obj.name if prompt_obj else 'None'}")

    # 3. If we have a valid prompt object, load it
    if prompt_obj:
        logger.info(f"Using system prompt: {prompt_obj.name} (model={model_name})")
        return _load_prompt_content(prompt_obj, model_name)

    # 4. Ultimate fallback to code-based prompt
    logger.info(f"Using code fallback prompt for model '{model_name}'")
    return _get_fallback_prompt(model_name)


def _load_prompt_content(prompt_obj, model_name: str) -> str:
    """Load prompt content from either file or database.

    Args:
        prompt_obj: SystemPrompt instance.
        model_name: Name of the LLM model (for variable substitution).

    Returns:
        str: The rendered prompt content.
    """
    if prompt_obj.is_file_based and prompt_obj.prompt_file_name:
        # Check if there's a .md template
        template_path = Path(__file__).parent.parent / "prompts" / "templates" / f"{prompt_obj.prompt_file_name}.md"

        if template_path.exists():
            # Use template rendering
            logger.debug(f"Loading template-based prompt: {prompt_obj.prompt_file_name}.md")
            return _render_template(prompt_obj.prompt_file_name, model_name, prompt_obj)
        else:
            logger.error(f"Template file not found: {template_path}")
            return _get_fallback_prompt(model_name)
    else:
        # Render variables in prompt_text at runtime
        logger.debug(f"Loading database prompt: {prompt_obj.name} v{prompt_obj.version}")
        return _render_prompt_variables(prompt_obj.prompt_text, model_name)


def _render_prompt_variables(prompt_text: str, model_name: str) -> str:
    """Render runtime variables in prompt text.

    Supported variables:
    - {current_date}: Current date in "Month DD, YYYY" format
    - {model_name}: Name of the LLM model

    Args:
        prompt_text: Raw prompt text with variable placeholders.
        model_name: Name of the LLM model.

    Returns:
        str: Prompt text with variables substituted.
    """
    current_date = datetime.now().strftime("%B %d, %Y")  # e.g., "January 14, 2026"

    try:
        return prompt_text.format(
            current_date=current_date,
            model_name=model_name,
        )
    except KeyError as e:
        logger.warning(f"Unknown variable in prompt text: {e}. Returning raw text.")
        return prompt_text


def _render_template(prompt_file_name: str, model_name: str, prompt_obj=None) -> str:
    """Render a Jinja2 template with dynamic context.

    Args:
        prompt_file_name: Name of the template file (without .md extension)
        model_name: Name of the LLM model
        prompt_obj: Optional SystemPrompt object for additional config

    Returns:
        str: Rendered prompt content
    """
    try:
        from ai_ops.prompts.template_renderer import get_renderer

        renderer = get_renderer()

        # Build context from prompt_obj if available
        context = {}
        timezone = "UTC"
        date_format = "%B %d, %Y"

        if prompt_obj and hasattr(prompt_obj, "additional_kwargs") and prompt_obj.additional_kwargs:
            config = prompt_obj.additional_kwargs
            timezone = config.get("timezone", timezone)
            date_format = config.get("date_format", date_format)
            # Add any additional custom variables from additional_kwargs
            context.update(config.get("template_vars", {}))

        return renderer.render(
            template_name=f"{prompt_file_name}.md",
            model_name=model_name,
            timezone=timezone,
            date_format=date_format,
            context=context,
        )
    except Exception as e:
        logger.error(f"Failed to render template '{prompt_file_name}.md': {e}")
        return _get_fallback_prompt(model_name)


def _get_fallback_prompt(model_name: str) -> str:
    """Get the hardcoded fallback prompt as last resort.

    Args:
        model_name: Name of the LLM model.

    Returns:
        str: A basic fallback system prompt.
    """
    current_date = datetime.now().strftime("%B %d, %Y")

    return f"""You are an AI assistant with access to specialized tools.

MODEL NAME: {model_name}
CURRENT DATE: {current_date}

Use the available tools to help users accomplish their goals. Always:
- Call discovery/search tools before data retrieval tools
- Provide comprehensive, well-formatted responses
- Never fabricate information
- Handle errors gracefully
"""
