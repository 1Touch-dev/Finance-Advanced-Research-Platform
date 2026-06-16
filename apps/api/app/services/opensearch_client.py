import os
from typing import Any, Dict, List, Optional


class OpenSearchClient:
    def __init__(self):
        self.url = os.getenv("OPENSEARCH_URL", "")
        self.index = os.getenv("OPENSEARCH_INDEX", "enterprise-docs")
        self._client = None
        if self.url:
            try:
                from opensearchpy import OpenSearch

                self._client = OpenSearch(
                    hosts=[self.url],
                    use_ssl=self.url.startswith("https"),
                    verify_certs=False,
                    ssl_show_warn=False,
                )
            except Exception:
                self._client = None

    def configured(self) -> bool:
        return self._client is not None

    def index_document(self, doc_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
        if not self._client:
            return {"ok": False, "reason": "not_configured"}
        self._client.index(index=self.index, id=doc_id, body=body, refresh=True)
        return {"ok": True, "id": doc_id}

    def bulk_index(self, docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not self._client:
            return {"ok": False, "count": 0}
        from opensearchpy.helpers import bulk

        actions = [{"_index": self.index, "_id": d["id"], "_source": d["body"]} for d in docs]
        success, _ = bulk(self._client, actions, refresh=True)
        return {"ok": True, "count": success}

    def search(self, query: str, size: int = 20, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self._client:
            return {"hits": []}
        must = [{"multi_match": {"query": query, "fields": ["title", "content", "excerpt", "name"]}}]
        if filters:
            for k, v in filters.items():
                must.append({"term": {k: v}})
        body = {"query": {"bool": {"must": must}}, "size": size}
        resp = self._client.search(index=self.index, body=body)
        hits = []
        for h in resp.get("hits", {}).get("hits", []):
            src = h.get("_source", {})
            hits.append({"id": h.get("_id"), "score": h.get("_score"), **src})
        return {"hits": hits, "total": resp.get("hits", {}).get("total", {}).get("value", 0)}
