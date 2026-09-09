import os
from dotenv import load_dotenv, find_dotenv

# Load environment variables from .env file with override
env_file = find_dotenv()
if not env_file:
    env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")

load_dotenv(env_file, override=True)

# Configuration Variables
FIRMS_API_KEY = os.getenv("FIRMS_API_KEY", "92678cc9ec8ec3c1167e7afcf451fc05")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "AIzaSyD5pn6XXtGkEh9q3be78WLLC1hKFepcy0w")

# Other global configs
DATABASE_URL = "sqlite:///./data/fire_monitor.db"
MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "classifier.pkl")

