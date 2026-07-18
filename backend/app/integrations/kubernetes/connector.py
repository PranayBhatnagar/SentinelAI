from typing import Any

from kubernetes_asyncio import client, config

from app.core.interfaces import BaseConnector


class KubernetesConnector(BaseConnector):
    """Official async Kubernetes SDK adapter; credentials follow normal in/out-of-cluster rules."""

    provider = "kubernetes"

    def __init__(self, core_api: client.CoreV1Api | None = None, apps_api: client.AppsV1Api | None = None) -> None:
        self._core_api, self._apps_api = core_api, apps_api

    async def _ensure_clients(self) -> tuple[client.CoreV1Api, client.AppsV1Api]:
        if self._core_api is None or self._apps_api is None:
            try:
                await config.load_incluster_config()
            except config.ConfigException:
                await config.load_kube_config()
            api_client = client.ApiClient()
            self._core_api, self._apps_api = client.CoreV1Api(api_client), client.AppsV1Api(api_client)
        return self._core_api, self._apps_api

    async def health_check(self) -> bool:
        try:
            core, _ = await self._ensure_clients()
            await core.get_api_resources()
            return True
        except Exception:
            return False

    async def query(self, operation: str, **parameters: Any) -> dict[str, Any]:
        core, apps = await self._ensure_clients()
        namespace = parameters.get("namespace", "default")
        service = parameters.get("service")
        label_selector = parameters.get("label_selector") or (f"app={service}" if service else None)
        if operation in {"workload_health", "pods"}:
            pods = await core.list_namespaced_pod(namespace, label_selector=label_selector)
            return {"provider": self.provider, "operation": operation, "data": [self._pod(item) for item in pods.items]}
        if operation == "events":
            events = await core.list_namespaced_event(namespace, field_selector=parameters.get("field_selector"))
            return {"provider": self.provider, "operation": operation, "data": [self._event(item) for item in events.items]}
        if operation == "deployments":
            deployments = await apps.list_namespaced_deployment(namespace, label_selector=label_selector)
            return {"provider": self.provider, "operation": operation, "data": [item.to_dict() for item in deployments.items]}
        if operation == "replicasets":
            sets = await apps.list_namespaced_replica_set(namespace, label_selector=label_selector)
            return {"provider": self.provider, "operation": operation, "data": [item.to_dict() for item in sets.items]}
        if operation == "logs":
            logs = await core.read_namespaced_pod_log(parameters["pod"], namespace, container=parameters.get("container"), tail_lines=parameters.get("tail_lines", 500))
            return {"provider": self.provider, "operation": operation, "data": logs}
        raise ValueError(f"Unsupported Kubernetes operation: {operation}")

    @staticmethod
    def _pod(pod: Any) -> dict[str, Any]:
        statuses = pod.status.container_statuses or []
        return {"name": pod.metadata.name, "phase": pod.status.phase, "node": pod.spec.node_name,
                "restart_count": sum(item.restart_count for item in statuses),
                "waiting_reasons": [item.state.waiting.reason for item in statuses if item.state and item.state.waiting],
                "terminated_reasons": [item.state.terminated.reason for item in statuses if item.state and item.state.terminated]}

    @staticmethod
    def _event(event: Any) -> dict[str, Any]:
        return {"reason": event.reason, "message": event.message, "type": event.type,
                "last_timestamp": str(event.last_timestamp or event.event_time)}
