import csv
import io
import requests
from sklearn.cluster import DBSCAN
import numpy as np

def fetch_india_firms(api_key, days=1):
    """
    Fetches FIRMS NRT data for India.
    Falls back to empty list if API key is not valid or request fails.
    """
    if not api_key or api_key == 'YOUR_NASA_FIRMS_KEY_HERE':
        print("No valid FIRMS API key provided, skipping real data fetch.")
        return []
    
    # India bounding box: west=68, south=8, east=97, north=37
    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{api_key}/VIIRS_SNPP_NRT/68,8,97,37/{days}"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        csv_data = response.text
        reader = csv.DictReader(io.StringIO(csv_data))
        return list(reader)
    except Exception as e:
        print(f"Failed to fetch FIRMS data: {e}")
        return []

def cluster_firms_points(firms_points, eps_km=2.0):
    """
    Clusters FIRMS points using DBSCAN based on spatial proximity.
    """
    if not firms_points:
        return []
        
    # Convert lat/lon to radians for Haversine distance
    coords = []
    for p in firms_points:
        try:
            coords.append([float(p['latitude']), float(p['longitude'])])
        except (KeyError, ValueError):
            continue
            
    if not coords:
        return []
        
    coords = np.array(coords)
    # Haversine distance setup
    kms_per_radian = 6371.0088
    epsilon = eps_km / kms_per_radian
    
    db = DBSCAN(eps=epsilon, min_samples=1, algorithm='ball_tree', metric='haversine').fit(np.radians(coords))
    labels = db.labels_
    
    clusters = {}
    for i, label in enumerate(labels):
        if label not in clusters:
            clusters[label] = []
        clusters[label].append(firms_points[i])
        
    result_events = []
    for label, points in clusters.items():
        frps = [float(p.get('frp', 0)) for p in points if 'frp' in p]
        brightnesses = [float(p.get('bright_ti4', 0)) for p in points if 'bright_ti4' in p]
        lats = [float(p.get('latitude', 0)) for p in points if 'latitude' in p]
        lons = [float(p.get('longitude', 0)) for p in points if 'longitude' in p]
        
        event = {
            'centroid_lat': np.mean(lats) if lats else 0,
            'centroid_lon': np.mean(lons) if lons else 0,
            'max_frp': max(frps) if frps else 0,
            'mean_brightness': np.mean(brightnesses) if brightnesses else 0,
            'cluster_size': len(points),
            'points': points
        }
        result_events.append(event)
        
    return result_events
