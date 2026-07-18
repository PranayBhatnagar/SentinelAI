from typing import Any

import chromadb

from app.core.interfaces import BaseConnector


class ChromaIncidentConnector(BaseConnector):
    provider = "chromadb"

    def __init__(self, host: str = "localhost", port: int = 8000, collection: str = "sentinel_incidents") -> None:
        self._client = chromadb.HttpClient(host=host, port=port)
        self._collection = self._client.get_or_create_collection(collection)

    async def health_check(self) -> bool:
        try:
            self._client.heartbeat()
            return True
        except Exception:
            return False

    async def query(self, operation: str, **parameters: Any) -> dict[str, Any]:
        if operation != "similar_incidents":
            raise ValueError(f"Unsupported Chroma operation: {operation}")
        result = self._collection.query(query_texts=[parameters["query"]], n_results=parameters.get("top_k", 5), where=parameters.get("where"))
        return {"provider": self.provider, "operation": operation, "data": result}

    async def upsert_incident(self, incident_id: str, summary: str, metadata: dict[str, Any]) -> None:
        self._collection.upsert(ids=[incident_id], documents=[summary], metadatas=[metadata])
