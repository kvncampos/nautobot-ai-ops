"""Django urlpatterns declaration for ai_ops app."""

from django.templatetags.static import static
from django.urls import path
from django.views.generic import RedirectView
from nautobot.apps.urls import NautobotUIViewSetRouter

from ai_ops import views

app_name = "ai_ops"

router = NautobotUIViewSetRouter()

router.register("llm-providers", views.LLMProviderUIViewSet)
router.register("llm-models", views.LLMModelUIViewSet)
router.register("middleware-types", views.MiddlewareTypeUIViewSet)
router.register("llm-middleware", views.LLMMiddlewareUIViewSet)
router.register("mcp-servers", views.MCPServerUIViewSet)


urlpatterns = [
    path(
        "docs/",
        RedirectView.as_view(url=static("ai_ops/docs/index.html")),
        name="docs",
    ),
    path("chat/", views.AIChatBotGenericView.as_view(), name="chat"),
    path("chat/message/", views.ChatMessageView.as_view(), name="chat_message"),
    path("chat/clear/", views.ChatClearView.as_view(), name="chat_clear"),
    path("mcp/clear-cache/", views.ClearMCPCacheView.as_view(), name="clear_mcp_cache"),
]

urlpatterns += router.urls
