#!/usr/bin/env python3
"""
Flask Web Interface for Running Shoe Recommendations
Provides a user-friendly form instead of curl commands
"""

from flask import Flask, render_template, request, jsonify, flash
import requests
import json
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this in production

# Configuration
API_URL = "http://localhost:8000"
DEFAULT_PORT = 3000

# Race distance options
RACE_DISTANCES = ["5k", "10k", "half_marathon", "marathon", "ultra"]

# Category options
CATEGORIES = ["easy_runs", "tempo_runs", "long_runs", "races", "trail"]

def load_catalog_data():
    """Load brand and price data from catalog.json"""
    try:
        catalog_path = os.path.join('app', 'catalog.json')
        with open(catalog_path, 'r') as f:
            catalog = json.load(f)
        
        # Extract unique brands
        brands = sorted(list(set(item['brand'] for item in catalog if item.get('brand'))))
        brands.append("Any")  # Add "Any" option
        
        # Find max price and add offset
        max_price = max(item.get('price_usd', 0) for item in catalog if item.get('price_usd'))
        max_price_with_offset = int(max_price + 50)
        
        return brands, max_price_with_offset
    except Exception as e:
        print(f"Error loading catalog: {e}")
        # Fallback to default values
        return ["Saucony", "Adidas", "Nike", "Hoka", "Brooks", "Any"], 500

def check_model_status():
    """Check if the Ollama model is available and responding"""
    try:
        # Check if the recommendation API is running
        response = requests.get(f"{API_URL}/", timeout=5)
        if response.status_code == 200:
            # Try to get a simple recommendation to test the model
            test_request = {
                "brand_preferences": ["Brooks"],
                "intended_use": {"easy_runs": True, "tempo_runs": False, "long_runs": False, "races": [], "trail": False},
                "cost_limiter": {"enabled": True, "max_usd": 200}
            }
            
            response = requests.post(f"{API_URL}/recommend", json=test_request, timeout=15)
            if response.status_code == 200:
                return "healthy", "✅ Model is working and responding to requests"
            else:
                return "warning", "⚠️ API is running but model may have issues"
        else:
            return "unhealthy", "❌ API is not responding properly"
    except requests.exceptions.ConnectionError:
        return "unhealthy", "❌ Cannot connect to recommendation API"
    except requests.exceptions.Timeout:
        return "warning", "⚠️ Model is responding but slowly (timeout)"
    except Exception as e:
        return "warning", f"⚠️ Model status unclear: {str(e)}"

@app.route('/')
def index():
    """Main form page"""
    brands, max_price = load_catalog_data()
    model_status, model_message = check_model_status()
    
    return render_template('index.html', 
                         brands=brands, 
                         race_distances=RACE_DISTANCES,
                         categories=CATEGORIES,
                         max_price=max_price,
                         model_status=model_status,
                         model_message=model_message)

@app.route('/recommend', methods=['POST'])
def recommend():
    """Handle form submission and call the API"""
    try:
        # Extract form data
        brand_preferences = request.form.getlist('brand_preferences')
        if 'Any' in brand_preferences:
            brand_preferences = None
        
        # Build intended use object
        intended_use = {
            "easy_runs": "easy_runs" in request.form,
            "tempo_runs": "tempo_runs" in request.form,
            "long_runs": "long_runs" in request.form,
            "races": request.form.getlist('races'),
            "trail": "trail" in request.form
        }
        
        # Build cost limiter
        cost_limiter = {
            "enabled": request.form.get('budget_enabled') == 'on',
            "max_usd": float(request.form.get('max_budget', 200))
        }
        
        # Get number of recommendations (default to 5)
        num_recommendations = int(request.form.get('num_recommendations', 5))
        
        # Prepare API request
        api_request = {
            "brand_preferences": brand_preferences,
            "intended_use": intended_use,
            "cost_limiter": cost_limiter,
            "num_recommendations": num_recommendations
        }
        
        # Call the recommendation API
        response = requests.post(f"{API_URL}/recommend", 
                               json=api_request, 
                               timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            return render_template('results.html', 
                                recommendations=result['shortlist'],
                                notes=result['notes'],
                                request_data=api_request)
        else:
            flash(f"API Error: {response.status_code} - {response.text}", "error")
            brands, max_price = load_catalog_data()
            return render_template('index.html', 
                                brands=brands, 
                                race_distances=RACE_DISTANCES,
                                categories=CATEGORIES,
                                max_price=max_price,
                                form_data=request.form)
            
    except requests.exceptions.ConnectionError:
        flash("Cannot connect to the recommendation API. Make sure it's running on localhost:8000", "error")
        brands, max_price = load_catalog_data()
        return render_template('index.html', 
                            brands=brands, 
                            race_distances=RACE_DISTANCES,
                            categories=CATEGORIES,
                            max_price=max_price,
                            form_data=request.form)
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
        brands, max_price = load_catalog_data()
        return render_template('index.html', 
                            brands=brands, 
                            race_distances=RACE_DISTANCES,
                            categories=CATEGORIES,
                            max_price=max_price,
                            form_data=request.form)

@app.route('/api/health')
def api_health():
    """Health check endpoint"""
    try:
        # Check if the recommendation API is running
        response = requests.get(f"{API_URL}/", timeout=5)
        if response.status_code == 200:
            return jsonify({"status": "healthy", "message": "API is running"})
        else:
            return jsonify({"status": "unhealthy", "message": "API is not responding properly"})
    except requests.exceptions.ConnectionError:
        return jsonify({"status": "unhealthy", "message": "Cannot connect to API"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/model-status')
def model_status():
    """Check model status and return detailed information"""
    status, message = check_model_status()
    return jsonify({"status": status, "message": message})

if __name__ == '__main__':
    print(f"🚀 Starting Flask app on port {DEFAULT_PORT}")
    print(f"📡 Recommendation API: {API_URL}")
    print("🔍 Loading catalog data...")
    brands, max_price = load_catalog_data()
    print(f"   Found {len(brands)-1} brands, max price: ${max_price}")
    print("🌐 Web interface will be available at: http://localhost:3000")
    
    app.run(host='0.0.0.0', port=DEFAULT_PORT, debug=True)
