import subprocess
import time
import threading
from typing import Dict, Optional
import google.auth
import google.auth.transport.requests
from google.adk.agents.readonly_context import ReadonlyContext

class TokenManager:
    """Manages GCP access tokens with caching and fallback methods."""
    
    def __init__(self):
        self._token_cache: Optional[str] = None
        self._token_expiry: float = 0
        self._token_lock = threading.Lock()

    def _get_token_via_google_auth(self) -> Optional[str]:
        """Attempts to fetch token via google-auth library (Standard for Cloud Run / ADC)."""
        try:
            print("--- Attempting to fetch token via google-auth ---")
            credentials, _ = google.auth.default()
            auth_request = google.auth.transport.requests.Request()
            credentials.refresh(auth_request)
            return credentials.token
        except Exception as e:
            print(f"--- google-auth failed: {e} ---")
            return None

    def _get_token_via_gcloud_cli(self) -> Optional[str]:
        """Attempts to fetch token via gcloud CLI (Local Dev fallback)."""
        try:
            print("--- Attempting to fetch token via gcloud CLI ---")
            return subprocess.check_output(
                ["gcloud", "auth", "print-access-token"], 
                stderr=subprocess.DEVNULL
            ).decode("utf-8").strip()
        except Exception as e:
            print(f"--- gcloud CLI failed: {e} ---")
            return None

    def get_access_token(self) -> Optional[str]:
        """Helper to fetch access token (works for local dev and Cloud Run)"""
        # 10 minutes buffer (ensures at least 50 mins reuse for 1hr token)
        buffer = 600
        now = time.time()
        
        with self._token_lock:
            if self._token_cache and now < (self._token_expiry - buffer):
                print("--- Using Cached Access Token ---")
                return self._token_cache
                
            # Try Method 1: google-auth
            token = self._get_token_via_google_auth()
            
            # Try Method 2: gcloud CLI fallback
            if not token:
                token = self._get_token_via_gcloud_cli()
                
            if token:
                self._token_cache = token
                self._token_expiry = now + 3600 # Default lifetime
                return self._token_cache
                
            return None

    def get_auth_headers(self, context: ReadonlyContext) -> Dict[str, str]:
        """Header provider to fetch access token on demand"""
        token = self.get_access_token()
        return {"Authorization": f"Bearer {token}"} if token else {}

# Singleton instance
token_manager = TokenManager()
