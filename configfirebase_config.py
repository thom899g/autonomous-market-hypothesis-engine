"""
Firebase configuration and initialization
Handles secure connection to Firebase services with error handling
"""
import os
import logging
from pathlib import Path
from typing import Optional
from google.cloud import firestore
from google.oauth2 import service_account
import firebase_admin
from firebase_admin import credentials, firestore, auth

logger = logging.getLogger(__name__)

class FirebaseManager:
    """Secure Firebase connection manager with error handling"""
    
    def __init__(self, credentials_path: Optional[str] = None):
        self.credentials_path = credentials_path or self._find_credentials()
        self.app = None
        self.db = None
        self._initialize()
    
    def _find_credentials(self) -> str:
        """Locate Firebase credentials file"""
        possible_paths = [
            Path("config/firebase_credentials.json"),
            Path("firebase_credentials.json"),
            Path(os.getenv("FIREBASE_CREDENTIALS_PATH", "")),
            Path.home() / ".config" / "firebase_credentials.json"
        ]
        
        for path in possible_paths:
            if path.exists():
                logger.info(f"Found credentials at: {path}")
                return str(path)
        
        raise FileNotFoundError(
            "Firebase credentials not found. Please create config/firebase_credentials.json "
            "or set FIREBASE_CREDENTIALS_PATH environment variable"
        )
    
    def _initialize(self):
        """Initialize Firebase app with error handling"""
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate(self.credentials_path)
                self.app = firebase_admin.initialize_app(cred)
                logger.info("Firebase app initialized successfully")
            else:
                self.app = firebase_admin.get_app()
                logger.info("Using existing Firebase app")
            
            # Initialize Firestore client
            self.db = firestore.client()
            logger.info("Firestore client initialized")
            
            # Test connection
            test_ref = self.db.collection('system_health').document('connection_test')
            test_ref.set({'timestamp': firestore.SERVER_TIMESTAMP}, merge=True)
            logger.debug("Firebase connection test successful")
            
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {str(e)}")
            raise
    
    def get_db(self) -> firestore.Client:
        """Get Firestore database client"""
        if not self.db:
            raise RuntimeError("Firebase not initialized")
        return self.db
    
    def get_auth(self):
        """Get Firebase Auth client"""
        return auth
    
    def cleanup(self):
        """Cleanup Firebase resources"""
        try:
            firebase_admin.delete_app(self.app)
            logger.info("Firebase app cleaned up")
        except Exception as e:
            logger.warning(f"Error during Firebase cleanup: {e}")

# Singleton instance
firebase_manager: Optional[FirebaseManager] = None

def get_firebase() -> FirebaseManager:
    """Get or create Firebase manager instance"""
    global firebase_manager
    if firebase_manager is None:
        firebase_manager = FirebaseManager()
    return firebase_manager