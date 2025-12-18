"""API Handler utilities for making HTTP requests."""

import json
from dataclasses import dataclass, field
from typing import Any, Optional, TypeAlias

from requests import Response, Session
from requests.exceptions import RequestException

JSONDict: TypeAlias = dict[str, str | int | float | bool | None]


@dataclass
class ApiHandler:
    """Api Handler Class."""

    headers: dict[str, str]
    url: Optional[str] = None
    token: Optional[str] = field(default=None, repr=False)
    timeout: int = 30
    verify: bool = False

    def __post_init__(self):
        """Post Init."""
        self.__client = self.__get_client()

    def __get_client(self):
        """Get HTTP API Client."""
        session = Session()
        session.headers.update(self.headers)
        # requests does not have base_url, so handle in each request
        return session

    def process_list_response(self, response: Response) -> list[JSONDict]:
        """Process the response from a list endpoint."""
        try:
            response.raise_for_status()
            r = response.json()
            if "results" in r:
                return r["results"]
            return r
        except RequestException as e:
            return [{"error": response.text, "exception": str(e)}]
        except json.JSONDecodeError as e:
            return [{"error": response.text, "exception": str(e)}]

    def process_response(self, response: Response) -> JSONDict:
        """Process the response from a single endpoint."""
        try:
            response.raise_for_status()
            r = response.json()
            if "results" in r:
                return r["results"]
            return r
        except RequestException as e:
            return {"error": response.text, "exception": str(e)}
        except json.JSONDecodeError as e:
            return {"error": response.text, "exception": str(e)}

    def _full_url(self, endpoint: str) -> str:
        if self.url:
            return self.url.rstrip("/") + "/" + endpoint.lstrip("/")
        return endpoint

    def delete(self, endpoint: str, params: Optional[dict[str, Any]] = None) -> JSONDict:
        """Delete Method."""
        response = self.__client.delete(
            self._full_url(endpoint), params=params, timeout=self.timeout, verify=self.verify
        )
        return self.process_response(response)

    def get(self, endpoint: str, params: Optional[dict[str, Any]] = None) -> JSONDict:
        """Get Method."""
        response = self.__client.get(self._full_url(endpoint), params=params, timeout=self.timeout, verify=self.verify)
        return self.process_response(response)

    def get_file(self, endpoint: str) -> Response:
        """Get File Method."""
        try:
            response = self.__client.get(self._full_url(endpoint), timeout=self.timeout, verify=self.verify)
            response.raise_for_status()
            return response
        except RequestException as e:
            raise e

    def get_all(self, endpoint: str, params: Optional[dict[str, Any]] = None) -> list[JSONDict]:
        """Get All Method."""
        response = self.__client.get(self._full_url(endpoint), params=params, timeout=self.timeout, verify=self.verify)
        return self.process_list_response(response)

    def post(self, endpoint: str, data: dict[str, Any], params: Optional[dict[str, Any]] = None) -> JSONDict:
        """Post Method."""
        response = self.__client.post(
            self._full_url(endpoint), json=data, params=params, timeout=self.timeout, verify=self.verify
        )
        return self.process_response(response)

    def post_all(
        self, endpoint: str, data: list[dict[str, Any]], params: Optional[dict[str, Any]] = None
    ) -> list[JSONDict]:
        """Post All Method."""
        response = self.__client.post(
            self._full_url(endpoint), json=data, params=params, timeout=self.timeout, verify=self.verify
        )
        return self.process_list_response(response)

    def patch(self, endpoint: str, data: dict[str, Any], params: Optional[dict[str, Any]] = None) -> JSONDict:
        """Patch Method."""
        response = self.__client.patch(
            self._full_url(endpoint), json=data, params=params, timeout=self.timeout, verify=self.verify
        )
        return self.process_response(response)

    def patch_all(
        self, endpoint: str, data: list[dict[str, Any]], params: Optional[dict[str, Any]] = None
    ) -> list[JSONDict]:
        """Patch All Method."""
        response = self.__client.patch(
            self._full_url(endpoint), json=data, params=params, timeout=self.timeout, verify=self.verify
        )
        return self.process_list_response(response)

    def put(self, endpoint: str, data: dict[str, Any], params: Optional[dict[str, Any]] = None) -> JSONDict:
        """Put Method."""
        response = self.__client.put(
            self._full_url(endpoint), json=data, params=params, timeout=self.timeout, verify=self.verify
        )
        return self.process_response(response)

    def put_all(
        self, endpoint: str, data: list[dict[str, Any]], params: Optional[dict[str, Any]] = None
    ) -> list[JSONDict]:
        """Put All Method."""
        response = self.__client.put(
            self._full_url(endpoint), json=data, params=params, timeout=self.timeout, verify=self.verify
        )
        return self.process_list_response(response)
