from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import requests


# Central catalog access for the app. The recommender calls this module instead
# of knowing whether data came from JSON, local SQLite, or Supabase.
ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG_PATH = ROOT_DIR / "app" / "catalog.json"
DEFAULT_SQLITE_PATH = ROOT_DIR / "data" / "running_shoes.db"

LIST_FIELDS = {"category", "best_for_distances", "sources"}
EXTRA_FIELDS = {
    "sale_price_usd",
    "size_checked",
    "available_for_size",
    "regular_price_usd",
    "has_wide_options",
    "retailer_sku",
    "color",
    "url",
    "product_url",
}

EXCLUDED_FOOTWEAR_TERMS = {
    "recovery",
    "slide",
    "slides",
    "sandal",
    "sandals",
    "ora",
    "spike",
    "spikes",
    "cleat",
    "lifestyle",
}


SQLITE_SCHEMA = """
create table if not exists running_shoes (
    shoe_key text primary key,
    brand text not null,
    model text not null,
    category_json text not null default '[]',
    price_usd real not null default 0,
    plate text not null default 'none',
    drop_mm real,
    weight_g integer,
    cushioning_level text,
    support_type text,
    heel_stack_mm real,
    forefoot_stack_mm real,
    best_for_distances_json text,
    has_wide_options integer,
    description text,
    image_url text,
    image_thumbnail_data_uri text,
    image_mime_type text,
    source_url text,
    source_name text,
    popularity_score real,
    review_count integer,
    average_rating real,
    sources_json text,
    extra_json text,
    scraped_at text,
    updated_at text not null
);

create index if not exists idx_running_shoes_brand on running_shoes (brand);
create index if not exists idx_running_shoes_price on running_shoes (price_usd);
create index if not exists idx_running_shoes_source on running_shoes (source_name);
"""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def slugify(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return text or "unknown"


def shoe_key_for(brand: str, model: str) -> str:
    return f"{slugify(brand)}--{slugify(model)}"


def _as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item not in (None, "")]
    if isinstance(value, str):
        return [value] if value else []
    return [str(value)]


def _as_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    number = _as_float(value)
    if number is None:
        return default
    return int(round(number))


def _as_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "wide", "regular, wide"}:
            return True
        if lowered in {"false", "0", "no", "regular"}:
            return False
    return None


def is_excluded_footwear(raw: Dict[str, Any]) -> bool:
    """Exclude slides, sandals, spikes, and lifestyle shoes from run-shoe catalog data."""
    name = f"{raw.get('brand', '')} {raw.get('model', '')} {raw.get('title', '')}".lower()
    words = set(re.findall(r"[a-z0-9]+", name))
    return bool(words & EXCLUDED_FOOTWEAR_TERMS)


def _clean_categories(raw: Dict[str, Any], categories: List[str]) -> List[str]:
    """Normalize workout categories for actual running shoes."""
    cleaned = []
    for category in categories:
        normalized = str(category).lower().strip()
        if normalized in {"racing", "race day"}:
            normalized = "race"
        if normalized in {"trainer", "training"}:
            normalized = "daily"
        if normalized and normalized not in cleaned:
            cleaned.append(normalized)

    return cleaned or ["daily"]


def normalize_shoe(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Return one stable shoe record shape for JSON, SQLite, and Supabase."""
    if is_excluded_footwear(raw):
        raise ValueError(f"Excluded non-running footwear: {raw.get('brand')} {raw.get('model')}")

    brand = str(raw.get("brand") or raw.get("maker") or "").strip()
    model = str(raw.get("model") or raw.get("name") or "").strip()
    if not brand or not model:
        raise ValueError(f"Shoe records require brand and model: {raw!r}")

    source_url = raw.get("source_url") or raw.get("product_url") or raw.get("url")
    sources = _as_list(raw.get("sources"))
    if source_url and source_url not in sources:
        sources.append(str(source_url))

    categories = _clean_categories(raw, _as_list(raw.get("category")) or ["daily"])

    normalized = {
        "shoe_key": raw.get("shoe_key") or shoe_key_for(brand, model),
        "brand": brand,
        "model": model,
        "category": categories,
        "price_usd": _as_float(raw.get("price_usd"), 0.0) or 0.0,
        "plate": str(raw.get("plate") or "none").lower(),
        "drop_mm": _as_float(raw.get("drop_mm")),
        "weight_g": _as_int(raw.get("weight_g")),
        "cushioning_level": raw.get("cushioning_level"),
        "support_type": raw.get("support_type"),
        "heel_stack_mm": _as_float(raw.get("heel_stack_mm")),
        "forefoot_stack_mm": _as_float(raw.get("forefoot_stack_mm")),
        "best_for_distances": _as_list(raw.get("best_for_distances")),
        "has_wide_options": _as_bool(raw.get("has_wide_options")),
        "description": None,
        "image_url": raw.get("image_url"),
        "image_thumbnail_data_uri": raw.get("image_thumbnail_data_uri") or raw.get("thumbnail_data_uri"),
        "image_mime_type": raw.get("image_mime_type"),
        "source_url": source_url,
        "source_name": raw.get("source_name") or raw.get("retailer"),
        "popularity_score": _as_float(raw.get("popularity_score")),
        "review_count": _as_int(raw.get("review_count")),
        "average_rating": _as_float(raw.get("average_rating")),
        "sources": sources,
        "scraped_at": raw.get("scraped_at"),
        "updated_at": raw.get("updated_at") or _utc_now(),
    }

    extra = dict(raw.get("extra") or {})
    for key in EXTRA_FIELDS:
        if key in raw and raw[key] is not None:
            extra[key] = raw[key]
    if extra:
        normalized["extra"] = extra

    return normalized


def load_catalog_json(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    catalog_path = path or DEFAULT_CATALOG_PATH
    with catalog_path.open("r", encoding="utf-8") as f:
        raw_items = json.load(f)
    return [normalize_shoe(item) for item in raw_items if not is_excluded_footwear(item)]


class CatalogRepository:
    """Read and write shoe catalog data through the configured backend."""

    def __init__(self, backend: Optional[str] = None, catalog_path: Optional[Path] = None):
        self._load_dotenv()
        self.catalog_path = catalog_path or DEFAULT_CATALOG_PATH
        self.backend = (backend or self._detect_backend()).lower()
        self.sqlite_path = Path(os.getenv("SHOE_SQLITE_PATH", str(DEFAULT_SQLITE_PATH)))
        self.supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self.supabase_key = (
            os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            or os.getenv("SUPABASE_ANON_KEY")
            or os.getenv("SUPABASE_KEY")
            or ""
        )
        self.supabase_table = os.getenv("SUPABASE_SHOES_TABLE", "running_shoes")

    def _load_dotenv(self) -> None:
        """Load local secrets for CLI/Flask entry points without requiring shell exports."""
        try:
            from dotenv import load_dotenv
        except ImportError:
            return
        load_dotenv(ROOT_DIR / ".env")

    def _detect_backend(self) -> str:
        """Choose a backend from env vars while keeping JSON as the safe default."""
        explicit = os.getenv("SHOE_CATALOG_BACKEND")
        if explicit:
            return explicit
        if os.getenv("SUPABASE_URL") and (
            os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
        ):
            return "supabase"
        if os.getenv("SHOE_SQLITE_PATH"):
            return "sqlite"
        return "json"

    @property
    def backend_name(self) -> str:
        return self.backend

    def initialize(self) -> None:
        if self.backend == "sqlite":
            self._init_sqlite()

    def load_catalog(self) -> List[Dict[str, Any]]:
        """Load shoes for recommendations, falling back to JSON if a service is empty/down."""
        try:
            if self.backend == "sqlite":
                rows = self._fetch_sqlite()
                return rows or load_catalog_json(self.catalog_path)
            if self.backend == "supabase":
                rows = self._fetch_supabase()
                return rows or load_catalog_json(self.catalog_path)
            return load_catalog_json(self.catalog_path)
        except Exception as exc:
            print(f"Catalog repository falling back to JSON after {self.backend} error: {exc}")
            return load_catalog_json(self.catalog_path)

    def list_shoes(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Return a filtered browse view for the website catalog page."""
        shoes = self.load_catalog()
        if category:
            needle = category.lower()
            shoes = [shoe for shoe in shoes if needle in {cat.lower() for cat in shoe.get("category", [])}]
        if search:
            needle = search.lower()
            shoes = [
                shoe for shoe in shoes
                if needle in f"{shoe.get('brand', '')} {shoe.get('model', '')}".lower()
            ]
        shoes.sort(key=lambda item: (
            item.get("popularity_score") or 0,
            item.get("review_count") or 0,
            item.get("price_usd") or 0,
        ), reverse=True)
        return shoes[:limit] if limit else shoes

    def brands(self) -> List[str]:
        return sorted({shoe["brand"] for shoe in self.load_catalog() if shoe.get("brand")})

    def max_price(self, default: int = 500) -> int:
        prices = [shoe.get("price_usd") or 0 for shoe in self.load_catalog()]
        return int(max(prices) + 50) if prices else default

    def upsert_many(self, shoes: Iterable[Dict[str, Any]]) -> int:
        """Store normalized scrape results in SQLite or Supabase."""
        normalized = [normalize_shoe(shoe) for shoe in shoes if not is_excluded_footwear(shoe)]
        if not normalized:
            return 0
        if self.backend == "sqlite":
            self._upsert_sqlite(normalized)
            return len(normalized)
        if self.backend == "supabase":
            self._upsert_supabase(normalized)
            return len(normalized)
        raise RuntimeError("Set SHOE_CATALOG_BACKEND=sqlite or Supabase env vars before storing shoes.")

    def _connect_sqlite(self) -> sqlite3.Connection:
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_sqlite(self) -> None:
        with self._connect_sqlite() as conn:
            conn.executescript(SQLITE_SCHEMA)

    def _fetch_sqlite(self) -> List[Dict[str, Any]]:
        self._init_sqlite()
        with self._connect_sqlite() as conn:
            rows = conn.execute("select * from running_shoes order by updated_at desc").fetchall()
        return [self._row_to_shoe(row) for row in rows if not is_excluded_footwear(dict(row))]

    def _upsert_sqlite(self, shoes: List[Dict[str, Any]]) -> None:
        self._init_sqlite()
        sql = """
        insert into running_shoes (
            shoe_key, brand, model, category_json, price_usd, plate, drop_mm, weight_g,
            cushioning_level, support_type, heel_stack_mm, forefoot_stack_mm,
            best_for_distances_json, has_wide_options, description, image_url,
            image_thumbnail_data_uri, image_mime_type, source_url, source_name,
            popularity_score, review_count, average_rating, sources_json, extra_json,
            scraped_at, updated_at
        ) values (
            :shoe_key, :brand, :model, :category_json, :price_usd, :plate, :drop_mm, :weight_g,
            :cushioning_level, :support_type, :heel_stack_mm, :forefoot_stack_mm,
            :best_for_distances_json, :has_wide_options, :description, :image_url,
            :image_thumbnail_data_uri, :image_mime_type, :source_url, :source_name,
            :popularity_score, :review_count, :average_rating, :sources_json, :extra_json,
            :scraped_at, :updated_at
        )
        on conflict(shoe_key) do update set
            brand=excluded.brand,
            model=excluded.model,
            category_json=excluded.category_json,
            price_usd=excluded.price_usd,
            plate=excluded.plate,
            drop_mm=excluded.drop_mm,
            weight_g=excluded.weight_g,
            cushioning_level=excluded.cushioning_level,
            support_type=excluded.support_type,
            heel_stack_mm=excluded.heel_stack_mm,
            forefoot_stack_mm=excluded.forefoot_stack_mm,
            best_for_distances_json=excluded.best_for_distances_json,
            has_wide_options=excluded.has_wide_options,
            description=coalesce(excluded.description, running_shoes.description),
            image_url=coalesce(excluded.image_url, running_shoes.image_url),
            image_thumbnail_data_uri=coalesce(excluded.image_thumbnail_data_uri, running_shoes.image_thumbnail_data_uri),
            image_mime_type=coalesce(excluded.image_mime_type, running_shoes.image_mime_type),
            source_url=coalesce(excluded.source_url, running_shoes.source_url),
            source_name=coalesce(excluded.source_name, running_shoes.source_name),
            popularity_score=coalesce(excluded.popularity_score, running_shoes.popularity_score),
            review_count=coalesce(excluded.review_count, running_shoes.review_count),
            average_rating=coalesce(excluded.average_rating, running_shoes.average_rating),
            sources_json=excluded.sources_json,
            extra_json=excluded.extra_json,
            scraped_at=coalesce(excluded.scraped_at, running_shoes.scraped_at),
            updated_at=excluded.updated_at
        """
        with self._connect_sqlite() as conn:
            conn.executemany(sql, [self._shoe_to_sqlite_params(shoe) for shoe in shoes])

    def _shoe_to_sqlite_params(self, shoe: Dict[str, Any]) -> Dict[str, Any]:
        params = dict(shoe)
        params["category_json"] = json.dumps(shoe.get("category") or [])
        params["best_for_distances_json"] = json.dumps(shoe.get("best_for_distances") or [])
        params["sources_json"] = json.dumps(shoe.get("sources") or [])
        params["extra_json"] = json.dumps(shoe.get("extra") or {})
        wide = shoe.get("has_wide_options")
        params["has_wide_options"] = None if wide is None else int(bool(wide))
        return params

    def _row_to_shoe(self, row: sqlite3.Row) -> Dict[str, Any]:
        item = dict(row)
        item["category"] = json.loads(item.pop("category_json") or "[]")
        item["best_for_distances"] = json.loads(item.pop("best_for_distances_json") or "[]")
        item["sources"] = json.loads(item.pop("sources_json") or "[]")
        item["extra"] = json.loads(item.pop("extra_json") or "{}")
        if item.get("has_wide_options") is not None:
            item["has_wide_options"] = bool(item["has_wide_options"])
        return normalize_shoe(item)

    def _supabase_headers(self) -> Dict[str, str]:
        if not self.supabase_url or not self.supabase_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY/SUPABASE_ANON_KEY are required.")
        return {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json",
        }

    def _fetch_supabase(self) -> List[Dict[str, Any]]:
        url = f"{self.supabase_url}/rest/v1/{self.supabase_table}"
        response = requests.get(
            url,
            headers=self._supabase_headers(),
            params={"select": "*", "order": "updated_at.desc"},
            timeout=20,
        )
        response.raise_for_status()
        return [
            normalize_shoe(self._supabase_row_to_shoe(row))
            for row in response.json()
            if not is_excluded_footwear(row)
        ]

    def _upsert_supabase(self, shoes: List[Dict[str, Any]]) -> None:
        url = f"{self.supabase_url}/rest/v1/{self.supabase_table}"
        headers = self._supabase_headers()
        headers["Prefer"] = "resolution=merge-duplicates,return=minimal"
        response = requests.post(
            url,
            headers=headers,
            params={"on_conflict": "shoe_key"},
            json=[self._shoe_to_supabase_row(shoe) for shoe in shoes],
            timeout=30,
        )
        response.raise_for_status()

    def _shoe_to_supabase_row(self, shoe: Dict[str, Any]) -> Dict[str, Any]:
        row = dict(shoe)
        row["extra"] = row.get("extra") or {}
        return row

    def _supabase_row_to_shoe(self, row: Dict[str, Any]) -> Dict[str, Any]:
        item = dict(row)
        for field in LIST_FIELDS:
            if item.get(field) is None:
                item[field] = []
        return item


def load_catalog_items() -> List[Dict[str, Any]]:
    return CatalogRepository().load_catalog()


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize, seed, and export running shoe catalog storage.")
    parser.add_argument("command", choices=["init", "seed", "export", "status"])
    parser.add_argument("--backend", choices=["json", "sqlite", "supabase"], default=None)
    parser.add_argument("--from-json", default=str(DEFAULT_CATALOG_PATH), dest="from_json")
    parser.add_argument("--out", default="catalog_export.json")
    args = parser.parse_args()

    repo = CatalogRepository(backend=args.backend)

    if args.command == "init":
        repo.initialize()
        print(f"Initialized catalog backend: {repo.backend_name}")
    elif args.command == "seed":
        shoes = load_catalog_json(Path(args.from_json))
        count = repo.upsert_many(shoes)
        print(f"Seeded {count} shoes into {repo.backend_name}")
    elif args.command == "export":
        shoes = repo.load_catalog()
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(shoes, f, ensure_ascii=False, indent=2)
        print(f"Exported {len(shoes)} shoes to {args.out}")
    elif args.command == "status":
        shoes = repo.load_catalog()
        print(json.dumps({
            "backend": repo.backend_name,
            "shoe_count": len(shoes),
            "brand_count": len({shoe.get("brand") for shoe in shoes}),
            "max_price": repo.max_price(),
        }, indent=2))


if __name__ == "__main__":
    main()
