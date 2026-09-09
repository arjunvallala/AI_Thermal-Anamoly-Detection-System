import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration Variables
FIRMS_API_KEY = os.getenv("FIRMS_API_KEY", "YOUR_FIRMS_KEY_HERE")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "YOUR_GOOGLE_MAPS_KEY_HERE")

# Other global configs
DATABASE_URL = "sqlite:///./data/fire_monitor.db"
MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "classifier.pkl")
