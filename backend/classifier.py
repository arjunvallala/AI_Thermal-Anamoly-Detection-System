import os
import random
import pickle
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from config import MODEL_PATH

CLASSES = {
    0: "Industrial Fire",
    1: "Gas Flare",
    2: "Wildfire",
    3: "Agricultural Burning",
    4: "Persistent Industrial Heat",
    5: "Unknown"
}

def generate_training_data(n_samples=500):
    np.random.seed(42)
    data = []
    
    for _ in range(n_samples):
        class_idx = np.random.randint(0, 5)
        
        if class_idx == 0:  # Industrial Fire
            frp = np.random.uniform(200, 800)
            near_ind = 1
            near_for = 0
            dev = np.random.uniform(2.0, 6.0)
        elif class_idx == 1:  # Gas Flare
            frp = np.random.uniform(50, 300)
            near_ind = 1
            near_for = 0
            dev = np.random.uniform(0.8, 1.5)
        elif class_idx == 2:  # Wildfire
            frp = np.random.uniform(20, 500)
            near_ind = 0
            near_for = 1
            dev = np.random.uniform(1.0, 3.0)
        elif class_idx == 3:  # Agricultural
            frp = np.random.uniform(10, 150)
            near_ind = 0
            near_for = 0
            dev = np.random.uniform(1.0, 2.0)
        else:  # Persistent Industrial Heat
            frp = np.random.uniform(50, 200)
            near_ind = 1
            near_for = 0
            dev = np.random.uniform(0.9, 1.2)
            
        data.append({
            'frp': frp,
            'brightness': frp + 300,
            'firms_confidence': np.random.randint(0, 3),
            'cluster_size': np.random.randint(1, 15),
            'near_industrial': near_ind,
            'near_forest': near_for,
            'frp_deviation': dev,
            'hour_of_day': np.random.randint(0, 24),
            'is_monsoon_season': np.random.choice([0, 1], p=[0.7, 0.3]),
            'label': class_idx
        })
        
    return pd.DataFrame(data)

def train_model(df=None):
    if df is None:
        df = generate_training_data()
        
    X = df.drop('label', axis=1)
    y = df['label']
    
    model = xgb.XGBClassifier(
        objective='multi:softprob',
        num_class=6,
        eval_metric='mlogloss',
        seed=42
    )
    
    model.fit(X, y)
    
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(model, f)
        
    return model

def load_or_train_model():
    if os.path.exists(MODEL_PATH):
        try:
            with open(MODEL_PATH, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            print(f"Error loading model: {e}. Retraining...")
    return train_model()

def classify_event(event_dict):
    model = load_or_train_model()
    
    # Extract features matching training data
    # Use near_industrial/near_forest from caller if provided, otherwise derive
    if 'near_industrial' in event_dict:
        near_ind = int(event_dict['near_industrial'])
    else:
        near_ind = 1 if event_dict.get('nearest_facility_type') not in ['unknown', None] else 0
    
    if 'near_forest' in event_dict:
        near_for = int(event_dict['near_forest'])
    else:
        near_for = 0

    features = {
        'frp': event_dict.get('frp', 50),
        'brightness': event_dict.get('brightness', 350),
        'firms_confidence': 2 if event_dict.get('firms_confidence') == 'high' else (1 if event_dict.get('firms_confidence') == 'nominal' else 0),
        'cluster_size': event_dict.get('cluster_size', 1),
        'near_industrial': near_ind,
        'near_forest': near_for,
        'frp_deviation': event_dict.get('frp_deviation', 1.0),
        'hour_of_day': event_dict.get('hour_of_day', 12),
        'is_monsoon_season': event_dict.get('is_monsoon_season', 0)
    }
    
    df = pd.DataFrame([features])
    probs = model.predict_proba(df)[0]
    pred_idx = int(np.argmax(probs))
    
    return {
        'class_name': CLASSES.get(pred_idx, "Unknown"),
        'probability': float(probs[pred_idx]),
        'all_class_probs': {CLASSES[i]: float(probs[i]) for i in range(len(probs))}
    }
