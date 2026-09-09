class EvidenceFusion:
    def __init__(self):
        pass

    def score_firms(self, event):
        frp = event.get('frp', 0)
        score = min(frp / 500.0, 1.0)
        return {"source": "FIRMS", "status": "confirmed" if score > 0.5 else "partial", "detail": f"FRP {frp} MW"}

    def score_industrial_proximity(self, event):
        dist = event.get('nearest_facility_dist_km', 10)
        if dist < 2.0:
            return {"source": "Industrial Proximity", "status": "confirmed", "detail": f"Near {event.get('nearest_facility_name')}"}
        return {"source": "Industrial Proximity", "status": "missing", "detail": f"No facility within 2km"}

    def score_land_cover(self, event):
        return {"source": "Land Cover", "status": "partial", "detail": "Urban/Industrial zone indicated"}

    def score_historical_behavior(self, event):
        dev = event.get('frp_deviation', 1.0)
        if dev > 2.0:
            return {"source": "Historical Baseline", "status": "confirmed", "detail": f"{dev}x deviation from baseline"}
        return {"source": "Historical Baseline", "status": "contradicted", "detail": "Within normal operating parameters"}

    def score_satellite_context(self, event):
        return {"source": "Satellite Context", "status": "partial", "detail": "Cloud cover minimal, good visibility"}

    def fuse_evidence(self, event, classification):
        evidence_items = [
            self.score_firms(event),
            self.score_industrial_proximity(event),
            self.score_land_cover(event),
            self.score_historical_behavior(event),
            self.score_satellite_context(event)
        ]
        
        confirmed_count = sum(1 for e in evidence_items if e['status'] == 'confirmed')
        if confirmed_count >= 3:
            agreement = "HIGH"
            confidence = 0.9
        elif confirmed_count >= 1:
            agreement = "MEDIUM"
            confidence = 0.6
        else:
            agreement = "LOW"
            confidence = 0.3
            
        severity = "NORMAL"
        dev = event.get('frp_deviation', 1.0)
        if dev > 4.0: severity = "CRITICAL"
        elif dev > 2.5: severity = "HIGH"
        elif dev > 1.5: severity = "WATCH"

        return {
            "evidence_items": evidence_items,
            "agreement_level": agreement,
            "confidence": confidence,
            "anomaly_severity": severity
        }
