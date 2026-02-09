"""Management command to migrate deep agent env-based middleware to database."""

import os

from django.core.management.base import BaseCommand

from ai_ops.models import LLMMiddleware, LLMModel, MiddlewareType


class Command(BaseCommand):
    """Migrate deep_agent environment-based middleware configuration to database."""

    help = "Migrate deep_agent environment-based middleware to database"

    def handle(self, *args, **options):
        """Migrate middleware configuration."""
        # Get default model (deep agent uses default)
        try:
            default_model = LLMModel.get_default_model()
        except LLMModel.DoesNotExist:
            self.stdout.write(self.style.ERROR("No default LLM model found. Create one first."))
            return

        # Check if already configured
        existing_count = LLMMiddleware.objects.filter(llm_model=default_model).count()
        if existing_count > 0:
            self.stdout.write(
                self.style.WARNING(f"Model '{default_model.name}' already has {existing_count} middleware. Skipping.")
            )
            return

        created = 0

        # Migrate ToolErrorHandlerMiddleware (always added)
        mw_type, _ = MiddlewareType.objects.get_or_create(
            name="ToolErrorHandlerMiddleware",
            defaults={"description": "Automatic retry for transient tool errors", "is_custom": True},
        )

        config = {
            "max_retries": int(os.getenv("TOOL_MAX_RETRIES", "2")),
            "retry_delay": 1.0,
        }

        LLMMiddleware.objects.create(
            llm_model=default_model,
            middleware=mw_type,
            config=config,
            priority=20,
            is_active=True,
            is_critical=False,
        )
        created += 1
        self.stdout.write(self.style.SUCCESS(f"✓ Created ToolErrorHandlerMiddleware with config: {config}"))

        self.stdout.write(
            self.style.SUCCESS(f"\n✓ Migration complete! Created {created} middleware for model '{default_model.name}'")
        )
        self.stdout.write("You can now configure middleware via the Nautobot UI under AI Ops > LLM Middleware")
