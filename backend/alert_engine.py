import uuid
from datetime import datetime

class AlertEngine:
    def __init__(self):
        self.responders_db = {
            "Delhi": {"fire": "Fire HQ Connaught Place", "hospital": "AIIMS Emergency", "police": "Crime Branch HQ"},
            "Mumbai": {"fire": "Fire Brigade HQ Byculla", "hospital": "KEM Hospital", "police": "Mumbai Police HQ"},
            "Kolkata": {"fire": "Fire Services HQ", "hospital": "SSKM Hospital", "police": "Lalbazar Police HQ"},
            "Chennai": {"fire": "Fire Station Anna Salai", "hospital": "Government General Hospital", "police": "Commissionerate"},
            "Hyderabad": {"fire": "Fire Station Abids", "hospital": "Osmania Hospital", "police": "Police Commissioner Office"},
            "Jamnagar": {"fire": "Fire Station Jamnagar", "hospital": "GG Hospital", "police": "SP Office"},
            "Vizag": {"fire": "Fire Station MVP Colony", "hospital": "KGH Hospital", "police": "CP Office"},
            "Bokaro": {"fire": "Fire Station Bokaro", "hospital": "Steel City Hospital", "police": "SP Office"},
        }
        self.default_responders = {"fire": "Local Fire HQ", "hospital": "District Gen Hospital", "police": "Local Police Station"}

    def determine_alert_type(self, event):
        severity = event.get("severity")
        if severity in ["HIGH", "CRITICAL"]:
            return "FIRE_EMERGENCY"
        if event.get("frp_deviation", 1.0) >= 2.5:
            return "INDUSTRIAL_INVESTIGATION"
        return "MONITORING"

    def determine_priority(self, event):
        severity = event.get("severity")
        frp = event.get("frp", 0)
        classification = event.get("classification", "")

        if severity == "CRITICAL" or classification in ["Industrial Fire", "Wildfire"]:
            return "P1"
        if severity == "HIGH" or frp >= 100:
            return "P2"
        if severity == "WATCH" or frp >= 30:
            return "P3"
        return "P4"

    def get_nearest_responders(self, lat, lon):
        # Simplified logic for demo, returning based on simple heuristics
        if lat > 28 and lon < 78:
            return self.responders_db["Delhi"]
        elif lat > 18 and lat < 20 and lon < 73:
            return self.responders_db["Mumbai"]
        elif lat > 22 and lat < 23 and lon < 71:
            return self.responders_db["Jamnagar"]
        return self.default_responders

    def generate_alert_message(self, event, alert_type):
        return f"[{alert_type}] High confidence ({event.get('ml_probability')}) {event.get('classification')} detected near {event.get('nearest_facility_name')}. FRP: {event.get('frp')} MW."

    def process_event(self, event):
        priority = self.determine_priority(event)
        if priority in ["P4", "P5"]:
            return None # Don't alert for low priority
            
        alert_type = self.determine_alert_type(event)
        message = self.generate_alert_message(event, alert_type)
        
        return {
            "id": str(uuid.uuid4()),
            "event_id": event.get("id"),
            "priority": priority,
            "alert_type": alert_type,
            "message": message,
            "created_at": datetime.now().isoformat(),
            "acknowledged": 0
        }
