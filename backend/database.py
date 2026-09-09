import sqlite3
import os
from config import DATABASE_URL

def get_db_connection():
    # Extract path from sqlite:///./data/fire_monitor.db
    db_path = DATABASE_URL.replace("sqlite:///", "")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create events table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            lat REAL,
            lon REAL,
            frp REAL,
            brightness REAL,
            firms_confidence TEXT,
            classification TEXT,
            ml_probability REAL,
            severity TEXT,
            evidence_score REAL,
            frp_deviation REAL,
            cluster_size INT,
            duration_hours REAL,
            affected_area_km2 REAL,
            co2_estimate REAL,
            likely_chemicals TEXT,
            nearest_facility_name TEXT,
            nearest_facility_type TEXT,
            nearest_facility_dist_km REAL,
            public_risk_score REAL,
            nearest_responders TEXT,
            timestamp TEXT,
            status TEXT,
            analyst_note TEXT
        )
    """)
    
    # Create alerts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id TEXT PRIMARY KEY,
            event_id TEXT,
            priority TEXT,
            alert_type TEXT,
            message TEXT,
            created_at TEXT,
            acknowledged INT DEFAULT 0
        )
    """)
    
    # Create historical_baseline table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historical_baseline (
            facility_id TEXT,
            lat REAL,
            lon REAL,
            avg_frp REAL,
            min_frp REAL,
            max_frp REAL,
            observation_count INT
        )
    """)
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
