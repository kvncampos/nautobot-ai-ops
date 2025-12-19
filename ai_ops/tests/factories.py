"""Test factories for AI Ops models."""

from nautobot.extras.models import Status

from ai_ops.models import (
    LLMMiddleware,
    LLMModel,
    LLMProvider,
    LLMProviderChoice,
    MCPServer,
    MiddlewareType,
)


class LLMProviderFactory:
    """Factory for creating LLMProvider instances."""

    @staticmethod
    def create_ollama(name="ollama", description="Test Ollama provider", is_enabled=True):
        """Create or get Ollama provider."""
        provider, created = LLMProvider.objects.get_or_create(
            name=LLMProviderChoice.OLLAMA,
            defaults={
                "description": description,
                "is_enabled": is_enabled,
            },
        )
        return provider, created

    @staticmethod
    def create_openai(name="openai", description="Test OpenAI provider", is_enabled=False):
        """Create or get OpenAI provider."""
        provider, created = LLMProvider.objects.get_or_create(
            name=LLMProviderChoice.OPENAI,
            defaults={
                "description": description,
                "is_enabled": is_enabled,
            },
        )
        return provider, created

    @staticmethod
    def create_azure_ai(name="azure_ai", description="Test Azure AI provider", is_enabled=True):
        """Create or get Azure AI provider."""
        provider, created = LLMProvider.objects.get_or_create(
            name=LLMProviderChoice.AZURE_AI,
            defaults={
                "description": description,
                "is_enabled": is_enabled,
            },
        )
        return provider, created

    @staticmethod
    def create_anthropic(name="anthropic", description="Test Anthropic provider", is_enabled=True):
        """Create or get Anthropic provider."""
        provider, created = LLMProvider.objects.get_or_create(
            name=LLMProviderChoice.ANTHROPIC,
            defaults={
                "description": description,
                "is_enabled": is_enabled,
            },
        )
        return provider, created

    @staticmethod
    def create_huggingface(name="huggingface", description="Test HuggingFace provider", is_enabled=True):
        """Create or get HuggingFace provider."""
        provider, created = LLMProvider.objects.get_or_create(
            name=LLMProviderChoice.HUGGINGFACE,
            defaults={
                "description": description,
                "is_enabled": is_enabled,
            },
        )
        return provider, created


class LLMModelFactory:
    """Factory for creating LLMModel instances."""

    @staticmethod
    def create_llama2(provider=None, name="llama2", description="Test Llama2 model", temperature=0.7, is_default=True):
        """Create or get Llama2 model."""
        if provider is None:
            provider, _ = LLMProviderFactory.create_ollama()

        model, created = LLMModel.objects.get_or_create(
            llm_provider=provider,
            name=name,
            defaults={
                "description": description,
                "temperature": temperature,
                "is_default": is_default,
            },
        )
        return model, created

    @staticmethod
    def create_mistral(
        provider=None, name="mistral", description="Test Mistral model", temperature=0.5, is_default=False
    ):
        """Create or get Mistral model."""
        if provider is None:
            provider, _ = LLMProviderFactory.create_ollama()

        model, created = LLMModel.objects.get_or_create(
            llm_provider=provider,
            name=name,
            defaults={
                "description": description,
                "temperature": temperature,
                "is_default": is_default,
            },
        )
        return model, created

    @staticmethod
    def create_gpt4(provider=None, name="gpt-4", description="Test GPT-4 model", temperature=0.3, is_default=False):
        """Create or get GPT-4 model."""
        if provider is None:
            provider, _ = LLMProviderFactory.create_openai()

        model, created = LLMModel.objects.get_or_create(
            llm_provider=provider,
            name=name,
            defaults={
                "description": description,
                "temperature": temperature,
                "is_default": is_default,
            },
        )
        return model, created


class MCPServerFactory:
    """Factory for creating MCPServer instances."""

    @staticmethod
    def create_http_server(
        name="test-server",
        protocol="http",
        url="http://localhost:8000",
        mcp_endpoint="/mcp",
        health_check="/health",
        mcp_type="internal",
        test_data_mixin=None,
    ):
        """Create or get HTTP MCP server."""
        # Get status - either from provided mixin or create a basic one
        if test_data_mixin:
            status = test_data_mixin.get_or_create_test_status(MCPServer)
        else:
            from nautobot.extras.models import Status

            status = Status.objects.get_for_model(MCPServer).first()
            if not status:
                from django.contrib.contenttypes.models import ContentType

                content_type = ContentType.objects.get_for_model(MCPServer)
                status, _ = Status.objects.get_or_create(
                    name="Active", defaults={"description": "Active status", "color": "4caf50"}
                )
                status.content_types.add(content_type)

        server, created = MCPServer.objects.get_or_create(
            name=name,
            defaults={
                "status": status,
                "protocol": protocol,
                "url": url,
                "mcp_endpoint": mcp_endpoint,
                "health_check": health_check,
                "mcp_type": mcp_type,
            },
        )
        return server, created

    @staticmethod
    def create_stdio_server(
        name="stdio-server", protocol="stdio", url="http://localhost:9000", mcp_type="external", test_data_mixin=None
    ):
        """Create or get STDIO MCP server."""
        # Get status - either from provided mixin or create a basic one
        if test_data_mixin:
            status = test_data_mixin.get_or_create_test_status(MCPServer)
        else:
            from nautobot.extras.models import Status

            status = Status.objects.get_for_model(MCPServer).first()
            if not status:
                from django.contrib.contenttypes.models import ContentType

                content_type = ContentType.objects.get_for_model(MCPServer)
                status, _ = Status.objects.get_or_create(
                    name="Active", defaults={"description": "Active status", "color": "4caf50"}
                )
                status.content_types.add(content_type)

        server, created = MCPServer.objects.get_or_create(
            name=name,
            defaults={
                "status": status,
                "protocol": protocol,
                "url": url,
                "mcp_type": mcp_type,
            },
        )
        return server, created


class MiddlewareTypeFactory:
    """Factory for creating MiddlewareType instances."""

    @staticmethod
    def create_auth_middleware(name="auth", description="Authentication middleware"):
        """Create or get auth middleware type."""
        middleware_type, created = MiddlewareType.objects.get_or_create(
            name=name,
            defaults={
                "description": description,
            },
        )
        return middleware_type, created

    @staticmethod
    def create_logging_middleware(name="logging", description="Logging middleware"):
        """Create or get logging middleware type."""
        middleware_type, created = MiddlewareType.objects.get_or_create(
            name=name,
            defaults={
                "description": description,
            },
        )
        return middleware_type, created


class LLMMiddlewareFactory:
    """Factory for creating LLMMiddleware instances."""

    @staticmethod
    def create_test_middleware(
        llm_model=None, middleware_type=None, config_data=None, priority=10, is_active=True, is_critical=False
    ):
        """Create or get test middleware."""
        if middleware_type is None:
            middleware_type, _ = MiddlewareTypeFactory.create_auth_middleware()

        if llm_model is None:
            llm_model, _ = LLMModelFactory.create_llama2()

        if config_data is None:
            config_data = {"key": "value"}

        # Use the actual field names for LLMMiddleware
        middleware, created = LLMMiddleware.objects.get_or_create(
            llm_model=llm_model,
            middleware=middleware_type,
            defaults={
                "config": config_data,
                "priority": priority,
                "is_active": is_active,
                "is_critical": is_critical,
            },
        )
        return middleware, created


class TestDataMixin:
    """Mixin to provide common test data setup and teardown."""

    def setup_test_data(self):
        """Set up common test data using factories."""
        # Create providers
        self.ollama_provider, _ = LLMProviderFactory.create_ollama()
        self.openai_provider, _ = LLMProviderFactory.create_openai()

        # Create models
        self.llama2_model, _ = LLMModelFactory.create_llama2(provider=self.ollama_provider)
        self.mistral_model, _ = LLMModelFactory.create_mistral(provider=self.ollama_provider)

        # Create MCP servers (pass self to enable proper status creation)
        self.http_server, _ = MCPServerFactory.create_http_server(test_data_mixin=self)
        self.stdio_server, _ = MCPServerFactory.create_stdio_server(test_data_mixin=self)
        self.auth_middleware_type, _ = MiddlewareTypeFactory.create_auth_middleware()
        self.logging_middleware_type, _ = MiddlewareTypeFactory.create_logging_middleware()

    def teardown_test_data(self):
        """Clean up test data if needed."""
        # Note: With get_or_create, we typically don't need to clean up
        # unless we want to reset state for specific tests
        pass

    def reset_test_data(self):
        """Reset test data to clean state."""
        # Delete created objects if they exist
        model_classes = [LLMMiddleware, LLMModel, MCPServer, MiddlewareType, LLMProvider]

        for model_class in model_classes:
            model_class.objects.all().delete()

        # Recreate base test data
        self.setup_test_data()

    def tearDown(self):
        """Standard tearDown method for test cleanup."""
        self.teardown_test_data()
        # Call parent tearDown if it exists
        if hasattr(super(), "tearDown"):
            super().tearDown()

    def create_test_user_with_permissions(self, username="testuser", permissions=None):
        """Create a test user with specific permissions."""
        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType

        user_model = get_user_model()
        user, created = user_model.objects.get_or_create(
            username=username,
            defaults={
                "email": f"{username}@example.com",
                "is_active": True,
                "is_staff": True,
            },
        )

        if permissions:
            # Add specific permissions
            for model_class, perm_list in permissions.items():
                content_type = ContentType.objects.get_for_model(model_class)
                for perm_codename in perm_list:
                    perm = Permission.objects.get(codename=perm_codename, content_type=content_type)
                    user.user_permissions.add(perm)
        else:
            # Add all permissions for AI Ops models
            ai_ops_models = [LLMProvider, LLMModel, MCPServer, MiddlewareType, LLMMiddleware]
            for model_class in ai_ops_models:
                content_type = ContentType.objects.get_for_model(model_class)
                permissions = Permission.objects.filter(content_type=content_type)
                user.user_permissions.add(*permissions)

        return user

    def assert_object_created(self, model_class, **filter_kwargs):
        """Assert that an object was created with the given criteria."""
        try:
            obj = model_class.objects.get(**filter_kwargs)
            return obj
        except model_class.DoesNotExist:
            self.fail(f"No {model_class.__name__} object found with criteria: {filter_kwargs}")
        except model_class.MultipleObjectsReturned:
            self.fail(f"Multiple {model_class.__name__} objects found with criteria: {filter_kwargs}")

    def assert_object_not_exists(self, model_class, **filter_kwargs):
        """Assert that no object exists with the given criteria."""
        exists = model_class.objects.filter(**filter_kwargs).exists()
        if exists:
            self.fail(f"{model_class.__name__} object found with criteria: {filter_kwargs}")

    def get_or_create_test_status(self, model_class):
        """Get or create a test status for the given model."""
        from django.contrib.contenttypes.models import ContentType

        content_type = ContentType.objects.get_for_model(model_class)

        # Try to get existing status for this model
        status = Status.objects.filter(content_types=content_type).first()

        if not status:
            # Create a default "Active" status for this content type
            status, _ = Status.objects.get_or_create(
                name="Active",
                defaults={
                    "description": f"Active status for {model_class.__name__}",
                    "color": "4caf50",  # Green color
                },
            )
            status.content_types.add(content_type)

        return status
