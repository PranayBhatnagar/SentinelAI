from typing import Any

from app.integrations.base import HttpConnector


class GrafanaConnector(HttpConnector):
    def __init__(self, base_url: str, token: str, **kwargs: Any) -> None:
        super().__init__("grafana", base_url, {"Authorization": f"Bearer {token}"}, **kwargs)

    @property
    def health_path(self) -> str:
        return "/api/health"

    async def query(self, operation: str, **parameters: Any) -> dict[str, Any]:
        if operation == "dashboards":
            response = await self._request("GET", "/api/search", params={"query": parameters.get("query", "")})
        elif operation == "datasource_query":
            datasource_uid = parameters["datasource_uid"]
            response = await self._request("POST", "/api/ds/query", json={
                "from": parameters["from"], "to": parameters["to"], "queries": parameters["queries"],
                "datasource": {"uid": datasource_uid},
            })
        else:
            raise ValueError(f"Unsupported Grafana operation: {operation}")
        return {"provider": self.provider, "operation": operation, "data": response.json()}
