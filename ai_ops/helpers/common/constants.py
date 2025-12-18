"""Constants."""


class Urls:
    """Urls."""

    APIGEE_URL = "Apigee URL"
    PROJECT42_URL = "Project42 URL"
    BASE_URL: str = "https://nautobot-lab.aa.com/api"
    NONPROD_URL: str = "https://nautobot-nonprod.aa.com"
    PROD_URL: str = "https://nautobot.aa.com"
    FASTAPI_UTILITY_EXTERNAL_URL = "http://fastapi-utility.project42-prod.svc.cluster.local:8001/api/utility_internal"
    FASTAPI_UTILITY_EXTERNAL_URL_NONPROD = (
        "http://fastapi-utility.project42-dev.svc.cluster.local:8001/api/utility_internal"
    )


class NautobotSecretsGroups:
    """Secret Groups."""

    NAUTOBOT_AA_ISE = "Nautobot AA ISE"
    P42_API_TOKEN_CREDS = "P42_API_Token_Creds"  # noqa: S105
