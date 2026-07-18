from typing import Any

from app.integrations.base import HttpConnector


class GitHubConnector(HttpConnector):
    """GitHub REST v3 adapter. Repository is always supplied as `owner/name`."""

    def __init__(self, token: str, base_url: str = "https://api.github.com", **kwargs: Any) -> None:
        super().__init__("github", base_url, {
            "Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }, **kwargs)

    @property
    def health_path(self) -> str:
        return "/user"

    async def query(self, operation: str, **parameters: Any) -> dict[str, Any]:
        repository = parameters.get("repository")
        if not repository:
            raise ValueError("GitHub operations require repository as owner/name")
        route, params = self._route(operation, repository, parameters)
        response = await self._request("GET", route, params=params)
        return {"provider": self.provider, "operation": operation, "data": response.json()}

    def _route(self, operation: str, repository: str, parameters: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        base = f"/repos/{repository}"
        per_page = int(parameters.get("per_page", 30))
        if operation == "workflow_jobs":
            return f"{base}/actions/runs/{parameters['run_id']}/jobs", {"per_page": per_page}
        if operation == "actions_log":
            return f"{base}/actions/jobs/{parameters['job_id']}/logs", {}
        if operation == "commit_diff":
            return f"{base}/commits/{parameters['sha']}", {}
        routes: dict[str, tuple[str, dict[str, Any]]] = {
            "repository": (base, {}), "pull_requests": (f"{base}/pulls", {"state": "all", "per_page": per_page}),
            "commits": (f"{base}/commits", {"per_page": per_page}), "branches": (f"{base}/branches", {"per_page": per_page}),
            "releases": (f"{base}/releases", {"per_page": per_page}),
            "workflow_runs": (f"{base}/actions/runs", {"per_page": per_page}),
        }
        if operation == "repository_risk":
            return routes["commits"]
        if operation not in routes:
            raise ValueError(f"Unsupported GitHub operation: {operation}")
        return routes[operation]
