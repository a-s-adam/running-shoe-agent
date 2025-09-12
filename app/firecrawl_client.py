from __future__ import annotations
import os
from typing import List, Dict, Optional
import httpx


class FirecrawlClient:
    """
    Minimal Firecrawl HTTP client to search and extract web content.
    Uses FIRECRAWL_API_KEY from env.
    """

    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.firecrawl.dev/v1"):
        self.api_key = api_key or os.getenv("FIRECRAWL_API_KEY")
        self.base_url = base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
            "Content-Type": "application/json",
        }

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def search(self, query: str, limit: int = 3, timeout_s: float = 8.0) -> List[Dict]:
        if not self.is_configured():
            return []
        url = f"{self.base_url}/search"
        payload = {"query": query, "limit": limit}
        try:
            with httpx.Client(timeout=timeout_s) as client:
                resp = client.post(url, headers=self._headers, json=payload)
                resp.raise_for_status()
                data = resp.json() or {}
                return data.get("data", []) or data.get("results", []) or []
        except Exception:
            return []

    def extract(self, url_to_extract: str, timeout_s: float = 10.0) -> Dict:
        if not self.is_configured():
            return {}
        url = f"{self.base_url}/crawl/extract"
        payload = {"url": url_to_extract}
        try:
            with httpx.Client(timeout=timeout_s) as client:
                resp = client.post(url, headers=self._headers, json=payload)
                resp.raise_for_status()
                return resp.json() or {}
        except Exception:
            return {}

    def get_shoe_web_context(self, brand: str, model: str, limit: int = 1) -> Dict:
        """
        Search the web for brand+model running shoe and extract brief context
        from a couple of top sources. Returns a dict with summaries and sources.
        """
        query = f"{brand} {model} running shoe review 2024"
        results = self.search(query, limit=limit)
        summaries: List[str] = []
        sources: List[str] = []

        for r in results[:limit]:
            src_url = r.get("url") or r.get("link")
            if not src_url:
                continue
            data = self.extract(src_url)
            content = (
                data.get("markdown")
                or data.get("text")
                or data.get("content")
                or ""
            )
            if content:
                snippet = content.strip().replace("\n", " ")
                # Keep a short, dense snippet
                summaries.append(snippet[:600])
                sources.append(src_url)

        return {"summaries": summaries, "sources": sources}
