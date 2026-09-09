import json
import uuid
import random
from datetime import datetime, timedelta

def get_demo_events():
    """Generates 15 diverse thermal events across India."""
    base_time = datetime.now()
    events = [
        {"lat": 22.4707, "lon": 70.0577, "class": "Industrial Fire", "frp": 450, "facility": "Jamnagar Refinery", "type": "refinery"},
        {"lat": 23.6693, "lon": 85.9612, "class": "Persistent Industrial Heat", "frp": 120, "facility": "Bokaro Steel", "type": "steel_mill"},
        {"lat": 24.1994, "lon": 82.6601, "class": "Gas Flare", "frp": 180, "facility": "Singrauli Power", "type": "power_plant"},
        {"lat": 21.9497, "lon": 89.1833, "class": "Wildfire", "frp": 320, "facility": "None", "type": "unknown"},
        {"lat": 30.7333, "lon": 76.7794, "class": "Agricultural Burning", "frp": 40, "facility": "None", "type": "unknown"},
        {"lat": 17.6868, "lon": 83.2185, "class": "Industrial Fire", "frp": 380, "facility": "Vizag Refinery", "type": "refinery"},
        {"lat": 22.3595, "lon": 82.7501, "class": "Persistent Industrial Heat", "frp": 150, "facility": "Korba Power", "type": "power_plant"},
        {"lat": 21.6263, "lon": 72.9960, "class": "Gas Flare", "frp": 90, "facility": "Ankleshwar Industrial", "type": "chemical_plant"},
        {"lat": 30.0668, "lon": 79.0193, "class": "Wildfire", "frp": 250, "facility": "None", "type": "unknown"},
        {"lat": 26.2989, "lon": 71.4189, "class": "Gas Flare", "frp": 110, "facility": "Barmer Oilfield", "type": "refinery"},
        {"lat": 23.7957, "lon": 86.4304, "class": "Industrial Fire", "frp": 290, "facility": "Dhanbad Coal", "type": "coal_mine"},
        {"lat": 21.1458, "lon": 79.0882, "class": "Agricultural Burning", "frp": 60, "facility": "None", "type": "unknown"},
        {"lat": 29.3909, "lon": 76.9635, "class": "Industrial Fire", "frp": 750, "facility": "Panipat Refinery", "type": "refinery"},
        {"lat": 19.0760, "lon": 72.8777, "class": "Unknown", "frp": 130, "facility": "Mumbai Harbor Area", "type": "unknown"},
        {"lat": 22.2604, "lon": 84.8536, "class": "Persistent Industrial Heat", "frp": 180, "facility": "Rourkela Steel", "type": "steel_mill"}
    ]

    generated = []
    for i, e in enumerate(events):
        event_id = f"EVENT-IND-{i+1:03d}"
        deviation = round(random.uniform(1.0, 5.2), 2)
        if e['class'] == 'Industrial Fire': deviation = round(random.uniform(2.5, 5.2), 2)
        duration = round(random.uniform(1.0, 48.0), 1)
        
        # Recalculate basic emissions directly for demo realism
        co2 = round((e['frp'] * 0.37 * duration * 3.6) / 1000.0, 2)
        
        if e['class'] in ['Industrial Fire', 'Wildfire']:
            severity = "CRITICAL"
        elif e['frp'] >= 100:
            severity = "HIGH"
        elif e['frp'] >= 30:
            severity = "WATCH"
        else:
            severity = "NORMAL"

        prob = round(random.uniform(0.65, 0.99), 2)

        generated.append({
            "id": event_id,
            "lat": e['lat'],
            "lon": e['lon'],
            "frp": e['frp'],
            "brightness": e['frp'] + 300,
            "firms_confidence": "high" if e['frp'] > 100 else "nominal",
            "classification": e['class'],
            "ml_probability": prob,
            "severity": severity,
            "evidence_score": round(random.uniform(0.5, 1.0), 2),
            "frp_deviation": deviation,
            "cluster_size": random.randint(1, 15),
            "duration_hours": duration,
            "affected_area_km2": round(random.uniform(0.5, 45.0), 2),
            "co2_estimate": co2,
            "likely_chemicals": "CO2, PM2.5", # Placeholder, proper calculation via emissions.py could be done
            "nearest_facility_name": e['facility'],
            "nearest_facility_type": e['type'],
            "nearest_facility_dist_km": round(random.uniform(0.1, 5.0), 2),
            "public_risk_score": random.randint(10, 95),
            "nearest_responders": json.dumps({"fire": "Local Fire HQ", "hospital": "City Gen Hospital"}),
            "timestamp": (base_time - timedelta(hours=random.randint(0, 24))).isoformat(),
            "status": "NEW",
            "analyst_note": ""
        })
    return generated

def get_demo_alerts(events):
    alerts = []
    priorities = ['P1', 'P2', 'P3']
    for i in range(5):
        event = events[i]
        alert = {
            "id": str(uuid.uuid4()),
            "event_id": event["id"],
            "priority": priorities[i % 3],
            "alert_type": "FIRE_EMERGENCY" if priorities[i % 3] in ['P1', 'P2'] else "INDUSTRIAL_INVESTIGATION",
            "message": f"Alert for {event['classification']} near {event['nearest_facility_name']}",
            "created_at": event["timestamp"],
            "acknowledged": 0
        }
        alerts.append(alert)
    return alerts
