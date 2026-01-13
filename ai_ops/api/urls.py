"""Django API urlpatterns declaration for ai_ops app."""

from nautobot.apps.api import OrderedDefaultRouter

from ai_ops.api import views

router = OrderedDefaultRouter()
# add the name of your api endpoint, usually hyphenated model name in plural, e.g. "my-model-classes"
router.register("llm-providers", views.LLMProviderViewSet)
router.register("llm-models", views.LLMModelViewSet)
router.register("middleware-types", views.MiddlewareTypeViewSet)
router.register("llm-middleware", views.LLMMiddlewareViewSet)
router.register("mcp-servers", views.MCPServerViewSet)
router.register("system-prompts", views.SystemPromptViewSet)

app_name = "ai_ops-api"
urlpatterns = router.urls
