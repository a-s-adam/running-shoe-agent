#!/usr/bin/env python3
"""Flask UI for running shoe recommendations (proxies to the FastAPI backend)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import requests
from flask import Flask, flash, jsonify, render_template, request

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-change-for-production")

_BASE_DIR = Path(__file__).resolve().parent
_CATALOG_PATH = _BASE_DIR / "app" / "catalog.json"

API_URL = os.environ.get("RECOMMEND_API_URL", "http://localhost:8000")
DEFAULT_PORT = int(os.environ.get("FLASK_PORT", "3000"))

RACE_DISTANCES = ["5k", "10k", "half_marathon", "marathon", "ultra"]
CATEGORIES = ["easy_runs", "tempo_runs", "long_runs", "races", "trail"]

_DEFAULT_BRANDS = ["Saucony", "Adidas", "Nike", "Hoka", "Brooks", "Any"]
_DEFAULT_MAX_PRICE = 500


def load_catalog_data():
    """Load brand list and a sensible max price from catalog.json."""
    try:
        with _CATALOG_PATH.open(encoding="utf-8") as f:
            catalog = json.load(f)
        brands = sorted({item["brand"] for item in catalog if item.get("brand")})
        brands.append("Any")
        prices = [item["price_usd"] for item in catalog if item.get("price_usd")]
        max_price = int(max(prices) + 50) if prices else _DEFAULT_MAX_PRICE
        return brands, max_price
    except OSError as e:
        print(f"Error loading catalog: {e}")
        return list(_DEFAULT_BRANDS), _DEFAULT_MAX_PRICE


def check_model_status():
    """Lightweight check that the FastAPI server answers on GET /."""
    try:
        response = requests.get(f"{API_URL}/", timeout=3)
        if response.status_code == 200:
            return "healthy", "Recommendation API is running."
        return "warning", "API returned a non-200 status."
    except requests.exceptions.ConnectionError:
        return "unhealthy", "Cannot connect to the recommendation API."
    except requests.exceptions.Timeout:
        return "warning", "API is responding slowly."
    except OSError as e:
        return "warning", f"Could not reach API: {e}"


def render_index():
    brands, max_price = load_catalog_data()
    model_status, model_message = check_model_status()
    return render_template(
        "index.html",
        brands=brands,
        race_distances=RACE_DISTANCES,
        categories=CATEGORIES,
        max_price=max_price,
        model_status=model_status,
        model_message=model_message,
    )


@app.route("/")
def index():
    return render_index()


@app.route("/recommend", methods=["POST"])
def recommend():
    try:
        brand_preferences = request.form.getlist("brand_preferences")
        if "Any" in brand_preferences:
            brand_preferences = None

        intended_use = {
            "easy_runs": "easy_runs" in request.form,
            "tempo_runs": "tempo_runs" in request.form,
            "long_runs": "long_runs" in request.form,
            "races": request.form.getlist("races"),
            "trail": "trail" in request.form,
        }

        cost_limiter = {
            "enabled": request.form.get("budget_enabled") == "on",
            "max_usd": float(request.form.get("max_budget", 200)),
        }

        num_recommendations = int(request.form.get("num_recommendations", 5))

        api_request = {
            "brand_preferences": brand_preferences,
            "intended_use": intended_use,
            "cost_limiter": cost_limiter,
            "num_recommendations": num_recommendations,
        }

        response = requests.post(
            f"{API_URL}/recommend",
            json=api_request,
            timeout=120,
        )

        if response.status_code == 200:
            result = response.json()
            return render_template(
                "results.html",
                recommendations=result["shortlist"],
                notes=result["notes"],
                request_data=api_request,
            )

        flash(f"API error: {response.status_code} — {response.text}", "error")
        return render_index()

    except requests.exceptions.ConnectionError:
        flash(
            "Cannot connect to the recommendation API. Start it on port 8000 "
            f"(or set RECOMMEND_API_URL; currently {API_URL}).",
            "error",
        )
        return render_index()
    except Exception as e:
        flash(str(e), "error")
        return render_index()


@app.route("/api/health")
def api_health():
    try:
        response = requests.get(f"{API_URL}/", timeout=5)
        if response.status_code == 200:
            return jsonify({"status": "healthy", "message": "API is running"})
        return jsonify({"status": "unhealthy", "message": "API is not responding properly"})
    except requests.exceptions.ConnectionError:
        return jsonify({"status": "unhealthy", "message": "Cannot connect to API"})
    except OSError as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route("/api/model-status")
def model_status_route():
    status, message = check_model_status()
    return jsonify({"status": status, "message": message})


if __name__ == "__main__":
    brands, max_price = load_catalog_data()
    print(f"Starting Flask on port {DEFAULT_PORT} (API: {API_URL})")
    print(f"Catalog: {len(brands) - 1} brands, budget cap hint ${max_price}")
    app.run(host="0.0.0.0", port=DEFAULT_PORT, debug=True)
