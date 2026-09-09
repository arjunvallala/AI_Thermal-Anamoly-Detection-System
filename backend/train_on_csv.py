# IndusFire AI - Train model on your labeled CSV
# Usage: python train_on_csv.py --csv your_data.csv
import argparse
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

parser = argparse.ArgumentParser(description='Train the classifier on your labeled CSV data')
parser.add_argument('--csv', required=True, help='Path to your labeled CSV file')
parser.add_argument('--label-col', default='label', help='Name of the label column (default: label)')
args = parser.parse_args()

print(f"Loading data from: {args.csv}")
df = pd.read_csv(args.csv)
print(f"Loaded {len(df)} rows")
print(f"Columns: {list(df.columns)}")
print(f"Label distribution:")
print(df[args.label_col].value_counts())

from classifier import train_model
print("\nTraining XGBoost model...")
train_model(df=df, label_col=args.label_col)
print("Model saved to models/classifier.pkl")
print("Restart the backend server to use the new model.")
