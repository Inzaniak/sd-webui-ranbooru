import os
import json
from pathlib import Path

class CredentialsManager:
    def __init__(self, extension_root):
        self.extension_root = extension_root
        self.credentials_dir = os.path.join(extension_root, 'user', 'credentials')
        self.credentials_file = os.path.join(self.credentials_dir, 'credentials.json')
        
        # Create credentials directory if it doesn't exist
        os.makedirs(self.credentials_dir, exist_ok=True)
        
        # Initialize credentials file if it doesn't exist
        if not os.path.exists(self.credentials_file):
            self._save_credentials({})
    
    def _load_credentials(self):
        """Load credentials from the JSON file"""
        try:
            with open(self.credentials_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_credentials(self, credentials):
        """Save credentials to the JSON file"""
        with open(self.credentials_file, 'w') as f:
            json.dump(credentials, f, indent=2)
    
    def save_booru_credentials(self, booru_name, api_key, user_id=None):
        """Save API credentials for a specific booru"""
        credentials = self._load_credentials()
        
        if booru_name not in credentials:
            credentials[booru_name] = {}
        
        credentials[booru_name]['api_key'] = api_key
        if user_id is not None:
            credentials[booru_name]['user_id'] = user_id
        
        self._save_credentials(credentials)
    
    def get_booru_credentials(self, booru_name):
        """Get API credentials for a specific booru"""
        credentials = self._load_credentials()
        return credentials.get(booru_name, {})
    
    def has_credentials(self, booru_name):
        """Check if credentials exist for a specific booru"""
        credentials = self.get_booru_credentials(booru_name)
        return 'api_key' in credentials and credentials['api_key'].strip() != ''
    
    def clear_booru_credentials(self, booru_name):
        """Clear credentials for a specific booru"""
        credentials = self._load_credentials()
        if booru_name in credentials:
            del credentials[booru_name]
            self._save_credentials(credentials)
