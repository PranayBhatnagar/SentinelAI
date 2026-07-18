from datetime import datetime, timedelta, timezone
from typing import Any

from app.integrations.base import HttpConnector


class LokiConnector(HttpConnector):
    @property
    def health_path(self) -> str:
        return "/ready"

    def __init__(self, base_url: str, **kwargs: Any) -> None:
        super().__init__("loki", base_url, **kwargs)

    async def query(self, operation: str, **parameters: Any) -> dict[str, Any]:
        if operation not in {"search_errors", "logs"}:
            raise ValueError(f"Unsupported Loki operation: {operation}")
        service = parameters.get("service")
        selector = parameters.get("selector") or (f'{{service="{service}"}}' if service else '{job=~".+"}')
        filter_expression = parameters.get("filter") or "|~ `(?i)(error|exception|timeout|oomkilled|authentication)`"
        end = datetime.now(timezone.utc)
        start = end - timedelta(minutes=int(parameters.get("time_range_minutes", 60)))
        response = await self._request("GET", "/loki/api/v1/query_range", params={
            "query": f"{selector} {filter_expression}", "start": int(start.timestamp() * 1e9),
            "end": int(end.timestamp() * 1e9), "limit": parameters.get("limit", 500), "direction": "BACKWARD",
        })
        payload = response.json()
        if payload.get("status") != "success":
            raise ConnectionError(f"Loki query failed: {payload}")
        return {"provider": self.provider, "operation": operation, "data": payload["data"]}
