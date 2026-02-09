"""Management command to register ToolResultCacheMiddleware in the database."""

from django.core.management.base import BaseCommand

from ai_ops.models import LLMMiddleware, LLMModel, MiddlewareType


class Command(BaseCommand):
    """Register ToolResultCacheMiddleware for the default LLM model."""

    help = "Register ToolResultCacheMiddleware in the database for the default LLM model"

    def handle(self, *args, **options):
        """Register middleware configuration."""
        # Get default model
        try:
            default_model = LLMModel.get_default_model()
        except LLMModel.DoesNotExist:
            self.stdout.write(self.style.ERROR("No default LLM model found. Create one first."))
            return

        # Check if already registered
        mw_type, created = MiddlewareType.objects.get_or_create(
            name="ToolResultCacheMiddleware",
            defaults={
                "description": "Redis-backed cache for tool call results with per-tool TTL",
                "is_custom": True,
            },
        )

        if not created:
            # Check if LLMMiddleware instance already exists
            if LLMMiddleware.objects.filter(llm_model=default_model, middleware=mw_type).exists():
                self.stdout.write(
                    self.style.WARNING(
                        f"ToolResultCacheMiddleware already configured for model '{default_model.name}'. Skipping."
                    )
                )
                return

        config = {
            "tool_cache_config": {
                "mcp_nautobot_openapi_api_request_schema": {"ttl": 600},
                "mcp_nautobot_dynamic_api_request": {"ttl": 60, "skip_methods": ["POST", "PUT", "DELETE", "PATCH"]},
            },
        }

        LLMMiddleware.objects.create(
            llm_model=default_model,
            middleware=mw_type,
            config=config,
            priority=15,  # Runs before ToolErrorHandler (priority=20)
            is_active=True,
            is_critical=False,
        )

        self.stdout.write(self.style.SUCCESS(f"✓ Created ToolResultCacheMiddleware with config:"))
        self.stdout.write(f"  Schema tool (mcp_nautobot_openapi_api_request_schema): TTL=600s")
        self.stdout.write(f"  API tool (mcp_nautobot_dynamic_api_request): TTL=60s, skip POST/PUT/DELETE/PATCH")
        self.stdout.write(f"  Priority: 15 (runs before ToolErrorHandler)")
        self.stdout.write(
            self.style.SUCCESS(f"\n✓ Registered for model '{default_model.name}'")
        )
        self.stdout.write("Configure via Nautobot UI under AI Ops > LLM Middleware")
