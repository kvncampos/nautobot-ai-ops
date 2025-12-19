"""Helper Functions."""

import re
import socket
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from nautobot.extras.choices import SecretsGroupAccessTypeChoices, SecretsGroupSecretTypeChoices
from nautobot.extras.models import Secret, SecretsGroup

from ai_ops.helpers.common.apihandler import ApiHandler, JSONDict
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
    """Get Apigee Token Headers."""
    return {
        "Accept": "application/json; indent=4",
        "Content-Type": "application/json",
    }


def get_apigee_credentials() -> tuple[str, str]:
    """Get Apigee Credentials."""
    secrets_group = SecretsGroup.objects.get(name__exact=NautobotSecretsGroups.P42_API_TOKEN_CREDS)
    key = secrets_group.get_secret_value(
        access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
        secret_type=SecretsGroupSecretTypeChoices.TYPE_KEY,
    )
    secret = secrets_group.get_secret_value(
        access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
        secret_type=SecretsGroupSecretTypeChoices.TYPE_SECRET,
    )
    return key, secret


def get_apigee_payload(key: str, secret: str) -> dict[str, str]:
    """Get Apigee Payload."""
    return {"client_id": key, "client_secret": secret, "grant_type": "client_credentials"}


def get_p42_apigee_token(apihandler: ApiHandler, endpoint: str, payload: dict[str, str]) -> str:
    """Get P42 Apigee Token."""
    response = apihandler.post(endpoint=endpoint, data=payload)
    if not response:
        raise CredentialsError("Failed to get response")
    if "error" in response:
        raise CredentialsError(f"Error in response: {response}")
    if "token" not in response:
        raise CredentialsError(f"Token not found in response: {response}")
    if not isinstance(response["token"], str):
        raise CredentialsError(f"Token is not a string in response: {response}")
    return response["token"]


def apigee_factory() -> str:
    """Apigee Factory."""
    key, secret = get_apigee_credentials()
    headers = get_json_headers()
    payload = get_apigee_payload(key, secret)
    endpoint = Secret.objects.get(name=Urls.APIGEE_URL).get_value()
    apihandler = ApiHandler(headers=headers)
    apigee_token = get_p42_apigee_token(apihandler=apihandler, endpoint=endpoint, payload=payload)
    return apigee_token


def get_fastapi_utility_url() -> str:
    """Get FastAPI Utility URL based on environment."""
    env = get_environment()
    if env == NautobotEnvironment.NONPROD:
        return Urls.FASTAPI_UTILITY_EXTERNAL_URL_NONPROD
    else:
        return Urls.FASTAPI_UTILITY_EXTERNAL_URL


def get_email_subject_with_environment(subject: str) -> str:
    """
    Prefix email subject with environment (NONPROD, LAB, or PROD).

    Args:
        subject (str): The base email subject text.

    Returns:
        str: The subject prefixed with the environment identifier.
    """
    env = get_environment()

    if env == NautobotEnvironment.LAB:
        return f"LAB - {subject}"
    elif env == NautobotEnvironment.NONPROD:
        return f"NONPROD - {subject}"
    elif env == NautobotEnvironment.PROD:
        return f"PROD - {subject}"
    else:
        return f"LocalDEV - {subject}"


@dataclass(kw_only=True)
class Email(ABC):
    """Email Abstract Base Class."""

    url: str = field(default_factory=get_fastapi_utility_url)
    endpoint: str = field(default="/sendEmail")
    emailto: list[str]
    emailsubject: str
    emailtitle: str
    emailmessage: str
    emailcc: list[str] = field(default_factory=list)

    @property
    def headers(self) -> dict[str, str]:
        """Get Headers."""
        token = apigee_factory()
        return {
            "Accept": "application/json; indent=4",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }

    @property
    def apihandler(self) -> ApiHandler:
        """ApiHandler property."""
        return ApiHandler(headers=self.headers, url=self.url)

    @property
    @abstractmethod
    def payload(self) -> dict[str, str | list[str] | int]:
        """Email API Payload."""
        ...

    def send(self) -> JSONDict:
        """Response Property."""
        return self.apihandler.post(endpoint=self.endpoint, data=self.payload)


@dataclass
class PlainTextEmail(Email):
    """Plaintext Email Concrete Class."""

    template: int = field(default=0)

    @property
    def payload(self) -> dict[str, str | list[str] | int]:
        """Email API Payload."""
        return {
            "emailto": self.emailto,
            "emailcc": self.emailcc,
            "emailsubject": self.emailsubject,
            "emailtitle": self.emailtitle,
            "emailmessage": self.emailmessage,
            "template": self.template,
        }


@dataclass
class HtmlEmail(Email):
    """HTML Email Concrete Class."""

    emailrequester: str
    emailmodule: str
    changedetail: str
    cherwell_id: Optional[str] = None
    template: int = field(default=1)

    @property
    def payload(self) -> dict[str, str | list[str] | int]:
        """Email API Payload."""
        payload = {
            "emailto": self.emailto,
            "emailcc": self.emailcc,
            "emailsubject": self.emailsubject,
            "emailtitle": self.emailtitle,
            "emailmessage": self.emailmessage,
            "template": self.template,
            "emailrequester": self.emailrequester,
            "emailmodule": self.emailmodule,
            "changedetail": self.changedetail,
        }
        if self.cherwell_id:
            payload["cherwell_id"] = self.cherwell_id
        return payload
