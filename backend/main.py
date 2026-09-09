from fastapi import FastAPI, HTTPException, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional
import json, uuid
from datetime import datetime

from database import init_db, get_db_connection
from classifier import load_or_train_model, classify_event
from demo_data import get_demo_events, get_demo_alerts
from report_generator import generate_report
from firms_client import fetch_india_firms, cluster_firms_points
from config import FIRMS_API_KEY
from emissions import estimate_co2, get_likely_chemicals, estimate_affected_area, estimate_duration, calculate_public_risk
from alert_engine import AlertEngine

app = FastAPI(title="Industrial Fire Monitor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VerificationRequest(BaseModel):
    action: str
    note: str
    new_class: Optional[str] = None

@app.on_event("startup")
def startup_event():
    init_db()
    load_or_train_model()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM events")
    if cursor.fetchone()[0] == 0:
        events = get_demo_events()
        alerts = get_demo_alerts(events)
        
        for e in events:
            cursor.execute("""
                INSERT INTO events (id, lat, lon, frp, brightness, firms_confidence, classification, ml_probability, severity, evidence_score, frp_deviation, cluster_size, duration_hours, affected_area_km2, co2_estimate, likely_chemicals, nearest_facility_name, nearest_facility_type, nearest_facility_dist_km, public_risk_score, nearest_responders, timestamp, status, analyst_note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (e['id'], e['lat'], e['lon'], e['frp'], e['brightness'], e['firms_confidence'], e['classification'], e['ml_probability'], e['severity'], e['evidence_score'], e['frp_deviation'], e['cluster_size'], e['duration_hours'], e['affected_area_km2'], e['co2_estimate'], e['likely_chemicals'], e['nearest_facility_name'], e['nearest_facility_type'], e['nearest_facility_dist_km'], e['public_risk_score'], e['nearest_responders'], e['timestamp'], e['status'], e['analyst_note']))
            
        for a in alerts:
            cursor.execute("""
                INSERT INTO alerts (id, event_id, priority, alert_type, message, created_at, acknowledged)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (a['id'], a['event_id'], a['priority'], a['alert_type'], a['message'], a['created_at'], a['acknowledged']))
            
        conn.commit()
    conn.close()

@app.get("/")
def root():
    return RedirectResponse(url="/api/health")

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/api/events")
def get_events(classification: Optional[str] = None, severity: Optional[str] = None, limit: int = 50):
    conn = get_db_connection()
    query = "SELECT * FROM events WHERE 1=1"
    params = []
    
    if classification:
        query += " AND classification = ?"
        params.append(classification)
    if severity:
        query += " AND severity = ?"
        params.append(severity)
        
    query += f" ORDER BY timestamp DESC LIMIT {limit}"
    
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

@app.get("/api/events/{event_id}")
def get_event(event_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Event not found")
        
    event_dict = dict(row)
    if isinstance(event_dict.get('nearest_responders'), str):
        try:
            event_dict['nearest_responders'] = json.loads(event_dict['nearest_responders'])
        except:
            pass
    return event_dict

@app.post("/api/events/{event_id}/verify")
def verify_event(event_id: str, req: VerificationRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Event not found")
        
    status = "VERIFIED" if req.action == 'verify' else "REJECTED" if req.action == 'reject' else "RECLASSIFIED"
    
    if req.action == 'reclassify' and req.new_class:
        cursor.execute("UPDATE events SET status = ?, analyst_note = ?, classification = ? WHERE id = ?", (status, req.note, req.new_class, event_id))
    else:
        cursor.execute("UPDATE events SET status = ?, analyst_note = ? WHERE id = ?", (status, req.note, event_id))
        
    conn.commit()
    conn.close()
    return {"status": "success", "event_id": event_id}

@app.get("/api/alerts")
def get_alerts(priority: Optional[str] = None):
    conn = get_db_connection()
    query = "SELECT * FROM alerts"
    params = []
    if priority:
        query += " WHERE priority = ?"
        params.append(priority)
    query += " ORDER BY created_at DESC"
    
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.post("/api/alerts/{alert_id}/acknowledge")
def ack_alert(alert_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE alerts SET acknowledged = 1 WHERE id = ?", (alert_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.get("/api/events/{event_id}/report")
def get_report(event_id: str):
    event_dict = get_event(event_id)
    pdf_bytes = generate_report(event_dict)
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=report_{event_id}.pdf"})

@app.post("/api/ingest")
def ingest_data():
    """Fetch live FIRMS data for India, cluster points, classify events and store them."""
    try:
        import math

        alert_engine = AlertEngine()
        firms_points = fetch_india_firms(FIRMS_API_KEY, days=2)
        if not firms_points:
            return {"status": "demo_mode", "message": "No live FIRMS data (key missing or no detections). Demo data remains active.", "new_events": 0}

        # Known industrial facilities for proximity check
        FACILITIES = [
            {"name": "Jamnagar Refinery (Reliance)", "type": "refinery", "lat": 22.4707, "lon": 70.0577},
            {"name": "Bokaro Steel Plant", "type": "steel_mill", "lat": 23.6693, "lon": 85.9612},
            {"name": "Singrauli Super Thermal Power", "type": "power_plant", "lat": 24.1994, "lon": 82.6601},
            {"name": "Vizag Refinery (HPCL)", "type": "refinery", "lat": 17.6868, "lon": 83.2185},
            {"name": "Korba Super Thermal Power", "type": "power_plant", "lat": 22.3595, "lon": 82.7501},
            {"name": "Ankleshwar Chemical Complex", "type": "chemical_plant", "lat": 21.6263, "lon": 72.9960},
            {"name": "Barmer Oil Field (Cairn)", "type": "gas_plant", "lat": 26.2989, "lon": 71.4189},
            {"name": "Dhanbad Coalfields", "type": "coal_mine", "lat": 23.7957, "lon": 86.4304},
            {"name": "Panipat Refinery (IOCL)", "type": "refinery", "lat": 29.3909, "lon": 76.9635},
            {"name": "Rourkela Steel Plant (SAIL)", "type": "steel_mill", "lat": 22.2604, "lon": 84.8536},
            {"name": "Mundra UMPP (Adani)", "type": "power_plant", "lat": 22.8390, "lon": 69.6720},
            {"name": "Haldia Petrochemicals", "type": "chemical_plant", "lat": 22.0596, "lon": 88.0686},
            {"name": "Talcher Thermal Power", "type": "power_plant", "lat": 20.9500, "lon": 85.2300},
            {"name": "Bhatinda Refinery (HPCL)", "type": "refinery", "lat": 30.2071, "lon": 74.9455},
            {"name": "Paradip Refinery (IOCL)", "type": "refinery", "lat": 20.3164, "lon": 86.6081},
        ]

        def haversine_km(lat1, lon1, lat2, lon2):
            R = 6371.0
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
            return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        def find_nearest_facility(lat, lon):
            best_dist = float('inf')
            best_fac = None
            for fac in FACILITIES:
                d = haversine_km(lat, lon, fac["lat"], fac["lon"])
                if d < best_dist:
                    best_dist = d
                    best_fac = fac
            return best_fac, round(best_dist, 2)

        # Known forested regions in India (approximate bounding boxes)
        FOREST_REGIONS = [
            (28.0, 30.5, 78.0, 80.5),   # Uttarakhand forests
            (21.0, 23.5, 80.0, 82.5),   # Central India (Madhya Pradesh)
            (14.0, 16.0, 74.5, 76.5),   # Western Ghats (Karnataka)
            (10.0, 12.5, 76.0, 77.5),   # Western Ghats (Kerala/TN)
            (22.0, 24.0, 85.0, 87.5),   # Jharkhand forests
            (18.0, 21.0, 82.0, 84.5),   # Odisha/Chhattisgarh forests
            (25.5, 27.5, 93.0, 95.5),   # Northeast India forests
            (11.5, 13.0, 74.5, 76.0),   # Western Ghats (Goa/Karnataka)
        ]

        def is_near_forest(lat, lon):
            for (lat_min, lat_max, lon_min, lon_max) in FOREST_REGIONS:
                if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
                    return 1
            return 0

        # Current month for monsoon check (June-September)
        current_month = datetime.utcnow().month
        is_monsoon = 1 if current_month in [6, 7, 8, 9] else 0

        clusters = cluster_firms_points(firms_points, eps_km=2.0)
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Clear previous live events so database reflects current satellite state
        cursor.execute("DELETE FROM events WHERE id LIKE 'LIVE-%'")
        conn.commit()

        new_count = 0

        for i, cluster in enumerate(clusters):
            event_id = f"LIVE-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
            lat = float(cluster["centroid_lat"])
            lon = float(cluster["centroid_lon"])
            frp = float(cluster["max_frp"])
            brightness = float(cluster["mean_brightness"])
            cluster_size = int(cluster["cluster_size"])

            # Compute proximity features
            nearest_fac, fac_dist = find_nearest_facility(lat, lon)
            near_industrial = 1 if fac_dist < 25.0 else 0  # within 25km of known facility
            near_forest = is_near_forest(lat, lon)
            fac_name = nearest_fac["name"] if fac_dist < 25.0 else "No nearby facility"
            fac_type = nearest_fac["type"] if fac_dist < 25.0 else "unknown"

            # Determine confidence from FIRMS data
            avg_confidence = "nominal"
            try:
                confs = [p.get('confidence', 'nominal') for p in cluster.get('points', [])]
                high_count = sum(1 for c in confs if c == 'high' or c == 'h')
                if high_count > len(confs) * 0.5:
                    avg_confidence = "high"
            except:
                pass

            # Estimate hour from FIRMS acquisition time if available
            hour_of_day = 12
            try:
                first_point = cluster.get('points', [{}])[0]
                acq_time = first_point.get('acq_time', '1200')
                hour_of_day = int(str(acq_time)[:2]) if acq_time else 12
            except:
                pass

            frp_deviation = round(max(1.0, frp / 80), 2)

            # Classify with proper features
            clf_result = classify_event({
                "frp": frp, "brightness": brightness,
                "firms_confidence": avg_confidence, "cluster_size": cluster_size,
                "near_industrial": near_industrial,
                "near_forest": near_forest,
                "frp_deviation": frp_deviation,
                "hour_of_day": hour_of_day,
                "is_monsoon_season": is_monsoon
            })
            classification = clf_result["class_name"]
            ml_prob = round(clf_result["probability"], 3)

            affected_area = round(estimate_affected_area(cluster_size, frp), 2)
            duration_hrs = 6.0
            co2 = round(estimate_co2(frp, duration_hrs), 2)
            chemicals = ", ".join(get_likely_chemicals(fac_type if near_industrial else "unknown")["compounds"][:4])
            public_risk = calculate_public_risk(lat, lon, frp, classification)["score"]

            # Severity Logic:
            # - Industrial Fire & Wildfire are always CRITICAL emergencies
            # - Other event types (Gas Flare, Agricultural, Persistent Heat) based on FRP intensity
            if classification in ["Industrial Fire", "Wildfire"]:
                severity = "CRITICAL"
            elif frp >= 100:
                severity = "HIGH"
            elif frp >= 30:
                severity = "WATCH"
            else:
                severity = "NORMAL"

            responders = json.dumps({
                "fire_station": "Nearest Fire Station (OSM)",
                "hospital": "Nearest Government Hospital",
                "police": "Nearest Police Station"
            })

            cursor.execute("""
                INSERT OR IGNORE INTO events
                (id, lat, lon, frp, brightness, firms_confidence, classification, ml_probability,
                 severity, evidence_score, frp_deviation, cluster_size, duration_hours,
                 affected_area_km2, co2_estimate, likely_chemicals, nearest_facility_name,
                 nearest_facility_type, nearest_facility_dist_km, public_risk_score,
                 nearest_responders, timestamp, status, analyst_note)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (event_id, lat, lon, frp, brightness, avg_confidence, classification, ml_prob,
                  severity, round(ml_prob, 2), frp_deviation, cluster_size, duration_hrs,
                  affected_area, co2, chemicals, fac_name, fac_type,
                  fac_dist, public_risk, responders,
                  datetime.utcnow().isoformat(), "active", ""))
            new_count += 1

        conn.commit()
        conn.close()
        return {"status": "success", "firms_points": len(firms_points), "clusters": len(clusters), "new_events": new_count}

    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/stats")
def get_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM events")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM events WHERE classification = 'Industrial Fire'")
    ind_fire = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM alerts WHERE priority = 'P1'")
    p1 = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM alerts WHERE priority = 'P2'")
    p2 = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM events WHERE severity IN ('HIGH','CRITICAL')")
    high_risk = cursor.fetchone()[0]
    conn.close()
    return {
        "total_events": total,
        "active_fires": ind_fire,
        "industrial_fires": ind_fire,
        "p1_alerts": p1,
        "p2_alerts": p2,
        "high_risk_areas": high_risk
    }


@app.get("/api/facilities")
def get_facilities():
    return [
        {"name": "Jamnagar Refinery (Reliance)", "type": "refinery", "lat": 22.4707, "lon": 70.0577},
        {"name": "Bokaro Steel Plant", "type": "steel_mill", "lat": 23.6693, "lon": 85.9612},
        {"name": "Singrauli Super Thermal Power", "type": "power_plant", "lat": 24.1994, "lon": 82.6601},
        {"name": "Vizag Refinery (HPCL)", "type": "refinery", "lat": 17.6868, "lon": 83.2185},
        {"name": "Korba Super Thermal Power", "type": "power_plant", "lat": 22.3595, "lon": 82.7501},
        {"name": "Ankleshwar Chemical Complex", "type": "chemical_plant", "lat": 21.6263, "lon": 72.9960},
        {"name": "Barmer Oil Field (Cairn)", "type": "gas_plant", "lat": 26.2989, "lon": 71.4189},
        {"name": "Dhanbad Coalfields", "type": "coal_mine", "lat": 23.7957, "lon": 86.4304},
        {"name": "Panipat Refinery (IOCL)", "type": "refinery", "lat": 29.3909, "lon": 76.9635},
        {"name": "Rourkela Steel Plant (SAIL)", "type": "steel_mill", "lat": 22.2604, "lon": 84.8536},
        {"name": "Mundra UMPP (Adani)", "type": "power_plant", "lat": 22.8390, "lon": 69.6720},
        {"name": "Haldia Petrochemicals", "type": "chemical_plant", "lat": 22.0596, "lon": 88.0686},
        {"name": "Talcher Thermal Power", "type": "power_plant", "lat": 20.9500, "lon": 85.2300},
        {"name": "Bhatinda Refinery (HPCL)", "type": "refinery", "lat": 30.2071, "lon": 74.9455},
        {"name": "Paradip Refinery (IOCL)", "type": "refinery", "lat": 20.3164, "lon": 86.6081},
    ]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
