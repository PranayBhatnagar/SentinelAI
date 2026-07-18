from datetime import datetime, timedelta, timezone
from typing import Any

from app.integrations.base import HttpConnector


class PrometheusConnector(HttpConnector):
    @property
    def health_path(self) -> str:
        return "/-/healthy"

    def __init__(self, base_url: str, **kwargs: Any) -> None:
        super().__init__("prometheus", base_url, **kwargs)

    async def query(self, operation: str, **parameters: Any) -> dict[str, Any]:
        query = parameters.get("promql") or self._promql(operation, parameters.get("service"))
        end = datetime.now(timezone.utc)
        start = end - timedelta(minutes=int(parameters.get("time_range_minutes", 60)))
        response = await self._request("GET", "/api/v1/query_range", params={
            "query": query, "start": start.timestamp(), "end": end.timestamp(), "step": parameters.get("step", "60s"),
        })
        payload = response.json()
        if payload.get("status") != "success":
            raise ConnectionError(f"Prometheus query failed: {payload}")
        return {"provider": self.provider, "operation": operation, "promql": query, "data": payload["data"]}

    @staticmethod
    def _promql(operation: str, service: str | None) -> str:
        labels = f'service="{service}"' if service else ""
        selector = f"{{{labels}}}"
        error_labels = f'{labels},status=~"5.."' if labels else 'status=~"5.."'
        queries = {
            "cpu": f"sum(rate(container_cpu_usage_seconds_total{selector}[5m])) by (pod)",
            "memory": f"sum(container_memory_working_set_bytes{selector}) by (pod)",
            "latency": f"histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{selector}[5m])) by (le))",
            "error_rate": f"sum(rate(http_requests_total{{{error_labels}}}[5m])) / sum(rate(http_requests_total{selector}[5m]))",
            "metrics_anomalies": f"sum(rate(http_requests_total{selector}[5m])) by (status)",
        }
        return queries.get(operation, queries["metrics_anomalies"])
