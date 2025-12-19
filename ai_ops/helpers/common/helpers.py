"""Helper Functions."""

import re
import socket

from nautobot.extras.choices import SecretsGroupAccessTypeChoices, SecretsGroupSecretTypeChoices
from nautobot.extras.models import SecretsGroup

from ai_ops.helpers.common.constants import NautobotSecretsGroups, Urls
from ai_ops.helpers.common.enums import NautobotEnvironment
from ai_ops.helpers.common.exceptions import CredentialsError


def get_hostname() -> str:
    """Get Hostname."""
    hostname = socket.gethostname()
    if not hostname:
        raise CredentialsError("Hostname could not be determined.")
    return hostname


def get_environment() -> NautobotEnvironment:
    """Get Environment."""
    hostname = get_hostname()
    if re.search(r"lab", hostname):
        env = NautobotEnvironment.LAB
    if re.search(r"nonprod", hostname):
        env = NautobotEnvironment.NONPROD
    elif re.search(r"prod", hostname):
        env = NautobotEnvironment.PROD
    else:
        env = NautobotEnvironment.LOCAL
    return env


def get_nautobot_url() -> str:
    """Get Nautobot URL based on environment."""
    env = get_environment()
    if env == NautobotEnvironment.LAB:
        return Urls.BASE_URL
    elif env == NautobotEnvironment.NONPROD:
        return Urls.NONPROD_URL
    elif env == NautobotEnvironment.PROD:
        return Urls.PROD_URL
    else:
        return "http://localhost:8080"


def get_json_headers() -> dict[str, str]:
    """Get JSON Headers."""
    return {
        "Accept": "application/json; indent=4",
        "Content-Type": "application/json",
    }


def get_credentials() -> tuple[str, str]:
    """Get Credentials."""
    secrets_group = SecretsGroup.objects.get(name__exact=NautobotSecretsGroups.EXAMPLE_GROUP)
    key = secrets_group.get_secret_value(
        access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
        secret_type=SecretsGroupSecretTypeChoices.TYPE_KEY,
    )
    secret = secrets_group.get_secret_value(
        access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
        secret_type=SecretsGroupSecretTypeChoices.TYPE_SECRET,
    )
    return key, secret
