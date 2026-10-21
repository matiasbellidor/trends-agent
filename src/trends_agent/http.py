"""Cliente HTTP mínimo. Las fuentes dependen de esta interfaz, no de requests."""
from __future__ import annotations

from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEFAULT_UA = (
    "trends-agent/0.1 (digest personal de tendencias; "
    "https://github.com/matiasbellidor/trends-agent)"
)


class Http:
    def __init__(self, user_agent: str = DEFAULT_UA, timeout: float = 20.0) -> None:
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers["User-Agent"] = user_agent
        retry = Retry(
            total=2,
            backoff_factor=1.5,
            status_forcelist=(500, 502, 503, 504),
            allowed_methods=("GET",),
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        self.session.mount("http://", HTTPAdapter(max_retries=retry))

    def _get(self, url: str, params: dict | None, headers: dict | None) -> requests.Response:
        resp = self.session.get(url, params=params, headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        return resp

    def get_json(self, url: str, params: dict | None = None, headers: dict | None = None) -> Any:
        return self._get(url, params, headers).json()

    def get_text(self, url: str, params: dict | None = None, headers: dict | None = None) -> str:
        return self._get(url, params, headers).text


def describe_error(exc: Exception) -> str:
    """Mensaje corto y sin datos sensibles para mostrar en el digest."""
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        return f"HTTP {exc.response.status_code}"
    return type(exc).__name__
