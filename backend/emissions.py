import math

# Chemical lookup by facility type
FACILITY_CHEMICALS = {
    'refinery': {'compounds': ['CO2', 'SO2', 'NOx', 'H2S', 'VOCs', 'PAHs', 'Benzene'], 'risk_level': 'HIGH'},
    'power_plant': {'compounds': ['CO2', 'SO2', 'NOx', 'PM2.5', 'Mercury', 'Fly Ash'], 'risk_level': 'MEDIUM'},
    'chemical_plant': {'compounds': ['CO2', 'HCl', 'NH3', 'NOx', 'Various VOCs', 'Dioxins'], 'risk_level': 'VERY HIGH'},
    'steel_mill': {'compounds': ['CO', 'CO2', 'NOx', 'PM2.5', 'Dioxins', 'Furans'], 'risk_level': 'HIGH'},
    'cement_plant': {'compounds': ['CO2', 'NOx', 'SO2', 'PM10', 'PM2.5', 'Heavy Metals'], 'risk_level': 'MEDIUM'},
    'coal_mine': {'compounds': ['CO2', 'CH4', 'CO', 'PM2.5', 'SO2'], 'risk_level': 'MEDIUM'},
    'gas_plant': {'compounds': ['CO2', 'CH4', 'NOx', 'NMVOC'], 'risk_level': 'MEDIUM'},
    'unknown': {'compounds': ['CO2', 'CO', 'PM2.5', 'NOx'], 'risk_level': 'UNKNOWN'},
}

def estimate_co2(frp_mw: float, duration_hours: float, fuel_type: str = 'mixed') -> float:
    """Estimates CO2 emissions in tonnes based on Fire Radiative Power."""
    # formula: frp * 0.37 * duration * 3.6 / 1000
    return (frp_mw * 0.37 * duration_hours * 3.6) / 1000.0

def estimate_black_carbon(frp_mw: float, duration_hours: float) -> float:
    """Estimates Black Carbon emissions in tonnes."""
    # formula: frp * 0.005 * duration * 3.6 / 1000
    return (frp_mw * 0.005 * duration_hours * 3.6) / 1000.0

def get_likely_chemicals(facility_type: str) -> dict:
    """Returns likely chemical compounds and risk level for a given facility type."""
    return FACILITY_CHEMICALS.get(facility_type.lower(), FACILITY_CHEMICALS['unknown'])

def estimate_affected_area(cluster_size: int, frp_mw: float) -> float:
    """Estimates the affected area in square kilometers."""
    # formula: pi * (0.5 + frp/500)^2 capped at 100
    radius = 0.5 + (frp_mw / 500.0)
    area = math.pi * (radius ** 2)
    return min(area, 100.0)

def estimate_duration(frp_mw: float, facility_type: str, historical_deviation: float) -> dict:
    """Estimates the duration of the event in days."""
    if facility_type in ['refinery', 'power_plant', 'steel_mill']:
        if historical_deviation > 2.0:
            return {'min_days': 1.0, 'max_days': 7.0, 'basis': 'High deviation industrial event'}
        return {'min_days': 0.1, 'max_days': 1.0, 'basis': 'Normal industrial operations'}
    
    if frp_mw > 200:
        return {'min_days': 2.0, 'max_days': 14.0, 'basis': 'High intensity thermal anomaly'}
    
    return {'min_days': 0.5, 'max_days': 3.0, 'basis': 'Standard thermal anomaly'}

def calculate_public_risk(lat: float, lon: float, frp_mw: float, classification: str) -> dict:
    """Calculates a public risk score from 0-100."""
    score = 0.0
    explanation = []
    
    # FRP contribution
    if frp_mw > 500:
        score += 40
        explanation.append("Extreme heat output detected.")
    elif frp_mw > 100:
        score += 20
        explanation.append("Significant heat output.")
        
    # Classification contribution
    if classification == "Industrial Fire":
        score += 50
        explanation.append("Industrial fires carry high risk of toxic emissions.")
    elif classification == "Wildfire":
        score += 30
        explanation.append("Wildfire smoke impacts air quality.")
    elif classification == "Gas Flare":
        score += 10
        explanation.append("Routine flaring, localized impact.")
        
    score = min(max(score, 0), 100)
    
    return {
        'score': round(score, 2),
        'explanation': " ".join(explanation) if explanation else "Low immediate risk detected."
    }
