"""Constants."""


class ErrorMessages:
    """User-facing error messages for production environments."""

    CHAT_ERROR = "Unable to process your message at this time. Please try again or contact your administrator if the issue persists."
    CLEAR_CHAT_ERROR = (
        "Failed to clear conversation history. Please try again or contact your administrator if the issue persists."
    )
    CACHE_CLEAR_ERROR = (
        "Failed to clear MCP cache. Please check the logs or contact your administrator if the issue persists."
    )


class Urls:
    """Urls."""

    APIGEE_URL = "Apigee URL"
    BASE_URL: str = "https://nautobot-lab.example.com/api"
    NONPROD_URL: str = "https://nautobot-nonprod.example.com"
    PROD_URL: str = "https://nautobot.example.com"


class NautobotSecretsGroups:
    """Secret Groups."""

    EXAMPLE_GROUP: str = "Example Secrets Group"
