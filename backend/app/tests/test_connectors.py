import httpx
import pytest

from app.integrations.github.connector import GitHubConnector
from app.integrations.loki.connector import LokiConnector
from app.integrations.prometheus.connector import PrometheusConnector


def client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://example.test")


@pytest.mark.asyncio
async def test_github_connector_fetches_repository_commits() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/repos/acme/checkout/commits"
        assert request.headers["authorization"] == "Bearer token"
        return httpx.Response(200, json=[{"sha": "abc"}])

    connector = GitHubConnector("token", "https://example.test", client=client(handler))
    result = await connector.query("commits", repository="acme/checkout")
    assert result["data"][0]["sha"] == "abc"


@pytest.mark.asyncio
async def test_prometheus_connector_builds_service_scoped_query() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert 'service="checkout"' in request.url.params["query"]
        return httpx.Response(200, json={"status": "success", "data": {"result": []}})

    connector = PrometheusConnector("https://example.test", client=client(handler))
    result = await connector.query("error_rate", service="checkout")
    assert result["data"] == {"result": []}


@pytest.mark.asyncio
async def test_loki_connector_uses_time_range_api() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/loki/api/v1/query_range"
        assert request.url.params["query"].startswith('{service="checkout"}')
        return httpx.Response(200, json={"status": "success", "data": {"result": []}})

    connector = LokiConnector("https://example.test", client=client(handler))
    result = await connector.query("search_errors", service="checkout")
    assert result["provider"] == "loki"
