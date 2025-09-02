# 🌐 Flask Web Interface

A beautiful, user-friendly web interface for the Running Shoe Recommendation Agent that replaces curl commands with an intuitive form.

## ✨ Features

- **Beautiful UI**: Modern, responsive design with gradients and smooth animations
- **Easy Form Input**: Checkboxes and dropdowns instead of JSON syntax
- **Real-time API Status**: Shows if the recommendation API is running
- **Detailed Results**: Beautiful cards showing all shoe information
- **Mobile Responsive**: Works great on all device sizes
- **Print Support**: Print your recommendations for reference

## 🚀 Quick Start

### 1. Install Dependencies
```bash
# Using uv (recommended)
uv pip install -r requirements.txt

# Or traditional pip
pip install -r requirements.txt
```

### 2. Start the Recommendation API
```bash
# Terminal 1: Start the FastAPI backend
./start.sh
# or
uvicorn app.main:app --reload --port 8000
```

### 3. Start the Flask Web Interface
```bash
# Terminal 2: Start the Flask frontend
./start_flask.sh
# or
python flask_app.py
```

### 4. Open Your Browser
Navigate to: http://localhost:3000

## 📱 How to Use

### Step 1: Fill Out the Form
1. **Brand Preferences**: Select your favorite brands or choose "Any" for all
2. **Intended Use**: Check what type of running you'll be doing
3. **Race Distances**: Select if you're training for specific races
4. **Budget**: Set your maximum price limit

### Step 2: Get Recommendations
- Click "🚀 Get Recommendations"
- The form sends your preferences to the API
- Results are displayed in beautiful cards

### Step 3: Review Results
Each shoe shows:
- **Score**: How well it matches your criteria (0-100%)
- **Specifications**: Price, plate type, drop, weight
- **Rule-based explanation**: Why it was selected
- **AI analysis**: LLM-generated insights

## 🏗️ Architecture

```
┌─────────────────┐    HTTP    ┌──────────────────┐
│   Flask Web     │ ──────────→ │  FastAPI Backend │
│   Interface     │             │  (Port 8000)    │
│   (Port 5000)   │             │                 │
└─────────────────┘             └──────────────────┘
         │                              │
         │                              │
         ▼                              ▼
┌─────────────────┐             ┌──────────────────┐
│   HTML Forms    │             │  Ollama LLM      │
│   & Results     │             │  (Port 11434)    │
└─────────────────┘             └──────────────────┘
```

## 🔧 Configuration

### Environment Variables
The Flask app reads from your `.env` file:
- `OLLAMA_HOST`: Ollama server address (default: localhost:11434)
- `OLLAMA_MODEL`: Model to use (default: llama3.1)

### API Endpoint
- **Form**: `POST /recommend` - Submit preferences
- **Health Check**: `GET /api/health` - Check API status
- **Main Page**: `GET /` - Input form

## 🎨 Customization

### Styling
- All CSS is inline in the HTML templates
- Easy to modify colors, fonts, and layout
- Responsive design with CSS Grid and Flexbox

### Form Fields
- Add new brand options in `flask_app.py`
- Modify race distances or categories
- Adjust budget ranges

### Templates
- `templates/index.html` - Main form page
- `templates/results.html` - Results display page

## 🐛 Troubleshooting

### Common Issues

**"Cannot connect to API"**
- Make sure the FastAPI backend is running on port 8000
- Check: `curl http://localhost:8000/`

**Flask won't start**
- Check if port 3000 is available
- Try: `python -m flask run --port 3001`

**Template errors**
- Ensure `templates/` directory exists
- Check file permissions

### Debug Mode
Flask runs in debug mode by default. To disable:
```python
app.run(debug=False, port=3000, host='0.0.0.0')
```

## 🔄 Alternative Startup Methods

### Using Flask CLI
```bash
export FLASK_APP=flask_app.py
export FLASK_ENV=development
flask run --port 3000
```

### Using Python Module
```bash
python -m flask --app flask_app run --port 3000
```

### Using uvicorn (if you prefer)
```bash
# Install asgi-flask
pip install asgi-flask

# Run with uvicorn
uvicorn asgi_flask:app --reload --port 3000
```

## 📊 Performance

- **Lightweight**: Minimal dependencies beyond Flask
- **Fast**: Direct API calls to FastAPI backend
- **Responsive**: Real-time API status checking
- **Scalable**: Easy to add caching or load balancing

## 🔒 Security Notes

- Change `app.secret_key` in production
- Consider adding CSRF protection
- Validate form inputs server-side
- Rate limiting for production use

## 🚀 Deployment

### Production Setup
```bash
# Install production WSGI server
pip install gunicorn

# Run with gunicorn
gunicorn -w 4 -b 0.0.0.0:3000 flask_app:app
```

### Docker (Optional)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 3000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:3000", "flask_app:app"]
```

## 🎯 Next Steps

- Add user accounts and save preferences
- Implement shoe comparison features
- Add filtering and sorting options
- Integrate with shopping APIs
- Add email notifications

---

**Happy Running! 🏃‍♂️** 

The Flask interface makes it easy to get personalized shoe recommendations without remembering curl commands.
