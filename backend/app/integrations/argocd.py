from typing import Any

from app.integrations.base import HttpConnector


class ArgoCDConnector(HttpConnector):
    def __init__(self, base_url: str, token: str, **kwargs: Any) -> None:
        super().__init__("argocd", base_url, {"Authorization": f"Bearer {token}"}, **kwargs)

    @property
    def health_path(self) -> str:
        return "/healthz"

    async def query(self, operation: str, **parameters: Any) -> dict[str, Any]:
        application = parameters.get("application") or parameters.get("service")
        if not application:
            raise ValueError("Argo CD operations require application or service")
        response = await self._request("GET", f"/api/v1/applications/{application}")
        app = response.json()
        if operation not in {"deployment_history", "application_health", "sync_status"}:
            raise ValueError(f"Unsupported Argo CD operation: {operation}")
        return {"provider": self.provider, "operation": operation, "data": app}
