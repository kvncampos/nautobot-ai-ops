"""Template rendering system for prompts with Jinja2 support.

This module provides a flexible, scalable approach to rendering prompts
using Jinja2 templates with support for:
- Dynamic variable injection (dates, timezones, model info)
- Component-based prompt architecture
- Configurable date/time formats
- Tool inventory auto-generation
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape

logger = logging.getLogger(__name__)


class PromptTemplateRenderer:
    """Renders prompt templates using Jinja2 with dynamic context injection."""

    def __init__(self, template_dir: Optional[Path] = None):
        """Initialize the template renderer.

        Args:
            template_dir: Directory containing prompt templates.
                         Defaults to ai_ops/prompts/templates/
        """
        if template_dir is None:
            # Default to prompts/templates directory
            template_dir = Path(__file__).parent / "templates"

        self.template_dir = template_dir
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(enabled_extensions=[]),  # Disable escaping for prompts
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

        # Add custom filters
        self.env.filters["format_datetime"] = self._format_datetime_filter

    def render(
        self,
        template_name: str,
        context: Optional[Dict[str, Any]] = None,
        model_name: Optional[str] = None,
        timezone: str = "UTC",
        date_format: str = "%B %d, %Y",
        **kwargs,
    ) -> str:
        """Render a prompt template with dynamic context.

        Args:
            template_name: Name of the template file (e.g., "multi_mcp_system_prompt.md")
            context: Additional context variables to inject
            model_name: LLM model name for the prompt
            timezone: Timezone for date rendering (default: UTC)
            date_format: strftime format for dates (default: "%B %d, %Y")
            **kwargs: Additional keyword arguments to merge into context

        Returns:
            Rendered prompt as a string

        Raises:
            TemplateNotFound: If the template file doesn't exist
        """
        try:
            template = self.env.get_template(template_name)
        except TemplateNotFound:
            logger.error(f"Template not found: {template_name}")
            raise

        # Build the rendering context
        render_context = self._build_context(
            model_name=model_name,
            timezone=timezone,
            date_format=date_format,
        )

        # Merge user-provided context
        if context:
            render_context.update(context)
        render_context.update(kwargs)

        logger.debug(f"Rendering template '{template_name}' with context keys: {list(render_context.keys())}")

        return template.render(render_context)

    def _build_context(
        self,
        model_name: Optional[str] = None,
        timezone: str = "UTC",
        date_format: str = "%B %d, %Y",
    ) -> Dict[str, Any]:
        """Build the default context for template rendering.

        Args:
            model_name: LLM model name
            timezone: Timezone for date rendering
            date_format: strftime format for dates

        Returns:
            Dictionary of context variables
        """
        # Get current datetime
        # Note: For now using system time, but could be extended with pytz for timezone support
        now = datetime.now()

        context = {
            # Model information
            "model_name": model_name or "Unknown",
            # Date/time variables
            "current_date": now.strftime(date_format),
            "current_datetime": now,
            "current_year": now.year,
            "timezone": timezone,
            # Configuration
            "date_format": date_format,
        }

        return context

    def _format_datetime_filter(self, dt: datetime, format_string: str = "%B %d, %Y") -> str:
        """Jinja2 filter for formatting datetime objects.

        Usage in templates: {{ current_datetime|format_datetime("%Y-%m-%d") }}

        Args:
            dt: Datetime object to format
            format_string: strftime format string

        Returns:
            Formatted date string
        """
        if not isinstance(dt, datetime):
            return str(dt)
        return dt.strftime(format_string)

    def validate_template(self, template_name: str) -> bool:
        """Validate that a template exists and can be parsed.

        Args:
            template_name: Name of the template file

        Returns:
            True if template is valid, False otherwise
        """
        try:
            self.env.get_template(template_name)
            return True
        except TemplateNotFound:
            logger.error(f"Template not found: {template_name}")
            return False
        except Exception as e:
            logger.error(f"Template validation failed for {template_name}: {e}")
            return False

    def list_available_templates(self) -> list[str]:
        """List all available template files.

        Returns:
            List of template filenames
        """
        if not self.template_dir.exists():
            return []

        return [str(p.relative_to(self.template_dir)) for p in self.template_dir.rglob("*.md")]


# Global renderer instance
_renderer = None


def get_renderer() -> PromptTemplateRenderer:
    """Get or create the global template renderer instance.

    Returns:
        PromptTemplateRenderer instance
    """
    global _renderer
    if _renderer is None:
        _renderer = PromptTemplateRenderer()
    return _renderer


def render_template(
    template_name: str,
    context: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> str:
    """Convenience function to render a template.

    Args:
        template_name: Name of the template file
        context: Context variables
        **kwargs: Additional context variables

    Returns:
        Rendered prompt string
    """
    renderer = get_renderer()
    return renderer.render(template_name, context=context, **kwargs)
