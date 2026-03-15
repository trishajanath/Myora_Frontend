from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from config import Config
import sys

try:
    client = MongoClient(
        Config.MONGO_URI,
        serverSelectionTimeoutMS=5000  # 5 second timeout
    )
    
    # Test connection
    client.admin.command('ping')
    print("✅ MongoDB connected successfully")
    
except ServerSelectionTimeoutError as e:
    print(f"❌ MongoDB connection failed: {e}")
    print("⚠️  Make sure MongoDB is running!")
    sys.exit(1)

# Database
db = client["imsr_db"]

# Collections
inpatients = db["inpatients"]
emr_collection = db["emr_records"]  # ✅ Collection for voice EMR structured notes
consultant_notes = db["consultant_notes"]  # ✅ Collection for consultant notes
users = db["users"]
