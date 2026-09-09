# IndusFire AI
## AI-Based Detection, Classification & Monitoring of Industrial Fires and Persistent Thermal Sources

A complete AI-powered geospatial industrial thermal intelligence platform for India.

---

## Quick Start (2 Steps)

### Step 1: Add Your API Keys
Edit the .env file:
`
FIRMS_API_KEY=your_actual_nasa_firms_key
GOOGLE_MAPS_API_KEY=your_actual_google_maps_key
`

Edit rontend/index.html line 376 - replace GOOGLE_MAPS_KEY_PLACEHOLDER with your Google Maps key.

### Step 2: Launch
Double-click START.bat OR run in PowerShell:
`powershell
.\start.ps1
`

That's it! The dashboard opens automatically at rontend/index.html.

---

## Project Structure

`
industrial-fire-monitor/
├── .env                    # Your API keys (fill this in)
├── START.bat               # One-click launcher (Windows)
├── start.ps1               # PowerShell launcher
├── backend/
│   ├── main.py             # FastAPI app (port 8000)
│   ├── classifier.py       # XGBoost ML classifier
│   ├── firms_client.py     # NASA FIRMS API client
│   ├── evidence_fusion.py  # Multi-source evidence scoring
│   ├── alert_engine.py     # P1-P5 alert routing
│   ├── emissions.py        # CO2, chemicals, area, risk
│   ├── report_generator.py # PDF incident report
│   ├── demo_data.py        # 15 India thermal events
│   ├── database.py         # SQLite database
│   ├── train_on_csv.py     # Train on your labeled CSV
│   ├── models/
│   │   └── classifier.pkl  # Trained XGBoost model
│   └── data/
│       └── fire_monitor.db # SQLite database
└── frontend/
    ├── index.html          # Main dashboard (open this)
    ├── style.css           # Dark theme styles
    └── app.js              # All frontend logic + Google Maps
`

---

## API Endpoints

| Endpoint | Description |
|---|---|
| GET /api/health | Health check |
| GET /api/events | All thermal events (supports ?classification=&severity=) |
| GET /api/events/{id} | Single event intelligence card |
| GET /api/alerts | All alerts (P1-P5) |
| GET /api/stats | Dashboard statistics |
| GET /api/facilities | Industrial facilities in India |
| POST /api/ingest | Trigger fresh FIRMS data fetch |
| GET /api/events/{id}/report | Download PDF incident report |
| POST /api/events/{id}/verify | Human analyst verification |

**Swagger UI:** http://localhost:8000/docs

---

## ML Classification Classes

| Class | Description |
|---|---|
| Industrial Fire | High-probability active fire at industrial facility |
| Gas Flare | Routine/abnormal gas flaring |
| Wildfire | Forest/natural fire |
| Agricultural Burning | Crop/stubble burning |
| Persistent Industrial Heat (Normal) | Known recurring thermal source within baseline |
| Unknown | Insufficient evidence — requires human review |

---

## Train on Your Own Data

Once you have your labeled CSV:
`powershell
cd backend
python train_on_csv.py --csv "C:\path\to\your_data.csv" --label-col "label"
`
Then restart the backend — it will use your trained model.

---

## Features

### Core
- Live thermal event map (India-wide)
- ML classification with probability scores
- Multi-source evidence fusion
- Historical baseline comparison
- P1–P5 alert routing
- Human-in-the-loop analyst review

### Extra
- Nearest fire station / hospital / police alerts
- CO2 & black carbon emission estimates
- Likely chemicals by facility type
- Affected land area estimate  
- Estimated fire duration
- Public risk score
- Downloadable PDF incident reports

---

## API Keys Needed

| Key | Where to Get |
|---|---|
| NASA FIRMS | https://firms.modaps.eosdis.nasa.gov/api/area/ |
| Google Maps | https://console.cloud.google.com (enable Maps JavaScript API) |

Both are FREE for demo/hackathon use.
