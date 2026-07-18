from typing import Any

from app.integrations.github.connector import GitHubConnector


class GitHubActionsConnector(GitHubConnector):
    """Actions-focused façade retaining the GitHub REST authentication contract."""

    provider = "github_actions"

    def __init__(self, token: str, **kwargs: Any) -> None:
        super().__init__(token, **kwargs)
        self.provider = "github_actions"

    async def query(self, operation: str, **parameters: Any) -> dict[str, Any]:
        if operation == "pipeline_failures":
            operation = "workflow_runs"
        return await super().query(operation, **parameters)
