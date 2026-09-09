# IndusFire AI - Train model on raw or labeled NASA FIRMS CSV
# Usage: python train_on_csv.py --csv your_nasa_firms_data.csv
import argparse
import pandas as pd
import numpy as np
import math
import sys
import os
from sklearn.preprocessing import LabelEncoder

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

parser = argparse.ArgumentParser(description='Train the classifier on NASA FIRMS CSV data with geospatial feature enrichment')
parser.add_argument('--csv', required=True, help='Path to your NASA FIRMS CSV file')
parser.add_argument('--label-col', default='label', help='Name of the label column (default: label)')
args = parser.parse_args()

print(f"Loading NASA FIRMS data from: {args.csv}")
df = pd.read_csv(args.csv)
print(f"Loaded {len(df)} rows")
print(f"Columns found: {list(df.columns)}")

# 1. Known Industrial Facilities for Geospatial Distance Matching
FACILITIES = [
    {"lat": 22.4707, "lon": 70.0577}, # Jamnagar Refinery
    {"lat": 23.6693, "lon": 85.9612}, # Bokaro Steel
    {"lat": 24.1994, "lon": 82.6601}, # Singrauli Power
    {"lat": 17.6868, "lon": 83.2185}, # Vizag Refinery
    {"lat": 22.3595, "lon": 82.7501}, # Korba Power
    {"lat": 21.6263, "lon": 72.9960}, # Ankleshwar Chemical
    {"lat": 26.2989, "lon": 71.4189}, # Barmer Oilfield
    {"lat": 23.7957, "lon": 86.4304}, # Dhanbad Coalfields
    {"lat": 29.3909, "lon": 76.9635}, # Panipat Refinery
    {"lat": 22.2604, "lon": 84.8536}, # Rourkela Steel
]

# 2. Known Forest Bounding Regions
FOREST_REGIONS = [
    (28.0, 30.5, 78.0, 80.5),   # Uttarakhand
    (21.0, 23.5, 80.0, 82.5),   # Madhya Pradesh
    (14.0, 16.0, 74.5, 76.5),   # Western Ghats
    (10.0, 12.5, 76.0, 77.5),   # Kerala/TN
    (22.0, 24.0, 85.0, 87.5),   # Jharkhand
    (18.0, 21.0, 82.0, 84.5),   # Odisha/Chhattisgarh
]

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def min_facility_dist(lat, lon):
    return min(haversine(lat, lon, f["lat"], f["lon"]) for f in FACILITIES)

def check_forest(lat, lon):
    for (lat_min, lat_max, lon_min, lon_max) in FOREST_REGIONS:
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return 1
    return 0

# 3. Enrich DataFrame with Geospatial Features if raw NASA CSV
if 'latitude' in df.columns and 'longitude' in df.columns:
    print("\nEnriching raw NASA satellite records with Geospatial Proximity features...")
    df['near_industrial'] = df.apply(lambda row: 1 if min_facility_dist(row['latitude'], row['longitude']) < 25.0 else 0, axis=1)
    df['near_forest'] = df.apply(lambda row: 1 if check_forest(row['latitude'], row['longitude']) == 1 else 0, axis=1)

if 'frp' in df.columns:
    df['frp_deviation'] = df['frp'].apply(lambda x: round(max(1.0, float(x) / 80.0), 2))

if 'bright_ti4' in df.columns:
    df['brightness'] = df['bright_ti4']
elif 'brightness' not in df.columns:
    df['brightness'] = df['frp'] + 300

if 'confidence' in df.columns and 'firms_confidence' not in df.columns:
    df['firms_confidence'] = df['confidence'].apply(lambda c: 2 if str(c).lower() in ['h', 'high'] else (1 if str(c).lower() in ['n', 'nominal'] else 0))

if 'cluster_size' not in df.columns:
    df['cluster_size'] = 1

if 'hour_of_day' not in df.columns:
    if 'acq_time' in df.columns:
        df['hour_of_day'] = df['acq_time'].apply(lambda t: int(str(t).zfill(4)[:2]) if pd.notnull(t) else 12)
    else:
        df['hour_of_day'] = 12

if 'is_monsoon_season' not in df.columns:
    df['is_monsoon_season'] = 0

# Auto-assign baseline labels if label column is missing
if args.label_col not in df.columns:
    print(f"Assigning baseline anomaly labels based on physical rules...")
    def label_rule(row):
        near_ind = row.get('near_industrial', 0)
        near_for = row.get('near_forest', 0)
        frp = row.get('frp', 10)
        if near_ind == 1 and frp > 200: return 0  # Industrial Fire
        if near_ind == 1 and frp <= 200: return 1 # Gas Flare / Heat
        if near_for == 1: return 2                # Wildfire
        return 3                                  # Agricultural Burning
    df[args.label_col] = df.apply(label_rule, axis=1)

# Filter columns to only required numerical ML features + label
feature_cols = ['frp', 'brightness', 'firms_confidence', 'cluster_size', 'near_industrial', 'near_forest', 'frp_deviation', 'hour_of_day', 'is_monsoon_season']
train_df = df[feature_cols + [args.label_col]].copy()

# Encode label column to contiguous integers 0..N-1
le = LabelEncoder()
train_df[args.label_col] = le.fit_transform(train_df[args.label_col])

print("\nFinal Feature Matrix shape:", train_df.shape)
print("\nFinal Label Distribution:")
print(train_df[args.label_col].value_counts())

from classifier import train_model
print("\nTraining XGBoost model on enriched NASA dataset...")
train_model(df=train_df)
print("Model successfully trained and saved to models/classifier.pkl!")
