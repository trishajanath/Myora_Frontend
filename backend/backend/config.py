import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # MongoDB
    MONGO_URI = os.getenv("MONGO_URI")
    
    # Google Gemini API
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    # Deepgram API (HIPAA Compliant Speech-to-Text)
    DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
    
    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG = os.getenv("DEBUG", "True") == "True"
    
    # HIPAA Compliance
    HIPAA_AUDIT_ENABLED = True
    HIPAA_BAA_SIGNED = os.getenv("HIPAA_BAA_SIGNED", "False") == "True"
    
    @classmethod
    def validate(cls):
        """Validate required configuration."""
        errors = []
        
        if not cls.GEMINI_API_KEY:
            errors.append("GEMINI_API_KEY not set")
        
        if not cls.DEEPGRAM_API_KEY:
            errors.append("DEEPGRAM_API_KEY not set")
        
        if not cls.MONGO_URI:
            errors.append("MONGO_URI not set")
        
        if errors:
            print("\nConfiguration Errors:")
            for error in errors:
                print(f"   - {error}")
            print("\nCreate a .env file with:")
            print("   GEMINI_API_KEY=your_key_here")
            print("   DEEPGRAM_API_KEY=your_key_here")
            print("   MONGO_URI=mongodb://localhost:27017/")
            print("   HIPAA_BAA_SIGNED=False  # Set True when BAA is signed\n")
            return False
        
        # Warn about HIPAA compliance
        if not cls.HIPAA_BAA_SIGNED:
            print("\nWARNING: HIPAA BAA not marked as signed!")
            print("   Do not use in production without signing BAA with Deepgram")
            print("   Contact: support@deepgram.com\n")
        
        return True