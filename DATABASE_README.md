# Catalog Database and Image Storage

The app now supports three catalog backends:

- `json`: current default, reads `app/catalog.json`
- `sqlite`: free local database at `data/running_shoes.db`
- `supabase`: free hosted Postgres through Supabase REST

The recommender and Flask catalog use the same repository layer, so you can switch storage without changing recommendation code.

## Local SQLite

```bash
cp env.example .env
# edit .env
SHOE_CATALOG_BACKEND=sqlite
SHOE_SQLITE_PATH=data/running_shoes.db

python -m app.catalog_repository init --backend sqlite
python -m app.catalog_repository seed --backend sqlite --from-json app/catalog.json
python -m app.catalog_repository status --backend sqlite
```

Start the API and Flask app as usual. The catalog page is available at:

```text
http://localhost:3000/catalog
```

## Supabase Free-Tier Setup

1. Create a free Supabase project.
2. Open the SQL editor and run `db/supabase_schema.sql`.
3. Copy your project URL and API keys into `.env`.
4. Use the service role key only from your local/server environment for scraper writes.

```bash
SHOE_CATALOG_BACKEND=supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_SHOES_TABLE=running_shoes

python -m app.catalog_repository seed --backend supabase --from-json app/catalog.json
python -m app.catalog_repository status --backend supabase
```

Supabase Free currently fits this project well: the shoe records are tiny, and 20-30 compressed thumbnails at roughly 45 KB each stay far below the free database/storage quotas. Do not store full product images in Postgres; keep original `image_url` values and store only compressed thumbnails.

## Third-Party Scraping

List available source profiles:

```bash
python scrape_third_party_running.py --list-sources
```

Scrape a small REI sample to JSON:

```bash
python scrape_third_party_running.py \
  --source rei_mens_road \
  --max-products 10 \
  --out rei_catalog.json
```

Scrape all configured third-party sources, compress thumbnails, and store them:

```bash
SHOE_CATALOG_BACKEND=sqlite python scrape_third_party_running.py \
  --source all \
  --max-products 30 \
  --store \
  --compress-images \
  --throttle 1.5 \
  --out catalog_third_party.json
```

Configured sources:

- `roadrunner_mens`: Road Runner Sports men's running shoes
- `rei_mens_road`: REI men's road-running shoes
- `sports_basement_mens`: Sports Basement men's running shoes
- `runners_mind_footwear`: A Runner's Mind footwear catalog

Before running broad scrapes, review each site's terms and robots policy. Keep `--throttle` conservative and prefer small category snapshots for a recommendation catalog.
