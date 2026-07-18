from abc import abstractmethod
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.interfaces import BaseConnector


class UnavailableConnector(BaseConnector):
    """Explicit safe default used until an organization configures a provider."""

    def __init__(self, provider: str) -> None:
        self.provider = provider

    async def health_check(self) -> bool:
        return False

    async def query(self, operation: str, **parameters: Any) -> dict[str, Any]:
        raise ConnectionError(f"{self.provider} connector is not configured for operation {operation}")


class HttpConnector(BaseConnector):
    """Reusable resilient HTTP transport for provider-specific connector adapters."""

    def __init__(self, provider: str, base_url: str, headers: dict[str, str] | None = None,
                 client: httpx.AsyncClient | None = None) -> None:
        self.provider = provider
        self.base_url = base_url.rstrip("/")
        self._headers = headers or {}
        self._client = client or httpx.AsyncClient(timeout=httpx.Timeout(20.0))
        self._owns_client = client is None

    async def health_check(self) -> bool:
        try:
            response = await self._request("GET", self.health_path)
            return response.is_success
        except (httpx.HTTPError, ConnectionError):
            return False

    @property
    @abstractmethod
    def health_path(self) -> str:
        raise NotImplementedError

    @retry(retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
           wait=wait_exponential(min=0.2, max=3), stop=stop_after_attempt(3), reraise=True)
    async def _request(self, method: str, path: str, *, params: dict[str, Any] | None = None,
                       json: dict[str, Any] | None = None) -> httpx.Response:
        response = await self._client.request(method, f"{self.base_url}{path}", headers=self._headers,
                                              params=params, json=json)
        response.raise_for_status()
        return response

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
