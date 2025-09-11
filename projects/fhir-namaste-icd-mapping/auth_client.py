#!/usr/bin/env python3
"""
Robust Authentication Client for FHIR NAMASTE-ICD Mapping Service

This script provides a robust authentication client that handles connection 
issues with unlimited retries and exponential backoff.
"""

import requests
import time
import json
import sys
from typing import Optional, Dict, Any
import urllib3

# Disable urllib3 warnings for cleaner output
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class RobustAuthClient:
    """
    Robust authentication client with unlimited retries and exponential backoff.
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.timeout = 30
        self.token = None
        
    def wait_with_backoff(self, attempt: int) -> None:
        """
        Exponential backoff with jitter, capped at 60 seconds.
        """
        base_delay = min(2 ** min(attempt, 6), 60)  # Cap at 60 seconds
        jitter = base_delay * 0.1  # 10% jitter
        delay = base_delay + (jitter * (hash(str(time.time())) % 100) / 100)
        print(f"⏳ Waiting {delay:.1f}s before retry {attempt + 1}...")
        time.sleep(delay)
        
    def check_server_status(self) -> bool:
        """
        Check if the server is responding.
        """
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            return response.status_code == 200
        except Exception:
            return False
            
    def authenticate(self, username: str = "admin", password: str = "admin123", 
                    max_connection_attempts: int = None) -> Optional[str]:
        """
        Authenticate with unlimited retries and robust error handling.
        
        Args:
            username: Username for authentication
            password: Password for authentication  
            max_connection_attempts: Maximum attempts (None = unlimited)
            
        Returns:
            JWT token string if successful, None if failed
        """
        attempt = 0
        
        while max_connection_attempts is None or attempt < max_connection_attempts:
            try:
                print(f"🔐 Authentication attempt {attempt + 1}...")
                
                # Check server status first
                if not self.check_server_status():
                    print("❌ Server not responding, checking if backend is running...")
                    attempt += 1
                    if max_connection_attempts is None or attempt < max_connection_attempts:
                        self.wait_with_backoff(attempt - 1)
                    continue
                
                # Prepare authentication data
                auth_data = {
                    'username': username,
                    'password': password
                }
                
                headers = {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Accept': 'application/json'
                }
                
                # Make authentication request
                response = self.session.post(
                    f"{self.base_url}/auth/token",
                    data=auth_data,
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code == 200:
                    token_data = response.json()
                    self.token = token_data.get('access_token')
                    print(f"✅ Authentication successful!")
                    print(f"🔑 Token type: {token_data.get('token_type', 'bearer')}")
                    print(f"⏰ Token expires in: {token_data.get('expires_in', 'unknown')} seconds")
                    return self.token
                    
                elif response.status_code == 401:
                    print(f"❌ Authentication failed: Invalid credentials")
                    return None
                    
                elif response.status_code == 422:
                    print(f"❌ Authentication failed: Validation error - {response.text}")
                    return None
                    
                else:
                    print(f"⚠️ Authentication failed with status {response.status_code}: {response.text}")
                    
            except requests.exceptions.ConnectionError as e:
                print(f"🔌 Connection error: {e}")
                print("   → Backend server might not be running")
                
            except requests.exceptions.Timeout as e:
                print(f"⏱️ Timeout error: {e}")
                
            except requests.exceptions.RequestException as e:
                print(f"🚨 Request error: {e}")
                
            except json.JSONDecodeError as e:
                print(f"📝 JSON decode error: {e}")
                
            except Exception as e:
                print(f"💥 Unexpected error: {e}")
                
            attempt += 1
            if max_connection_attempts is None or attempt < max_connection_attempts:
                self.wait_with_backoff(attempt - 1)
            
        print(f"❌ Authentication failed after {attempt} attempts")
        return None
        
    def make_authenticated_request(self, method: str, endpoint: str, 
                                 **kwargs) -> Optional[requests.Response]:
        """
        Make an authenticated request with token refresh.
        """
        if not self.token:
            print("🔑 No token available, authenticating first...")
            if not self.authenticate():
                return None
                
        headers = kwargs.get('headers', {})
        headers['Authorization'] = f'Bearer {self.token}'
        kwargs['headers'] = headers
        
        try:
            response = self.session.request(method, f"{self.base_url}{endpoint}", **kwargs)
            
            # If token expired, try to refresh
            if response.status_code == 401:
                print("🔄 Token expired, re-authenticating...")
                if self.authenticate():
                    headers['Authorization'] = f'Bearer {self.token}'
                    response = self.session.request(method, f"{self.base_url}{endpoint}", **kwargs)
                    
            return response
            
        except Exception as e:
            print(f"💥 Request error: {e}")
            return None

def main():
    """
    Main function for command line usage.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Robust Authentication Client')
    parser.add_argument('--username', default='admin', help='Username (default: admin)')
    parser.add_argument('--password', default='admin123', help='Password (default: admin123)')
    parser.add_argument('--url', default='http://localhost:8000', help='Base URL')
    parser.add_argument('--max-attempts', type=int, help='Max attempts (default: unlimited)')
    parser.add_argument('--test-endpoint', help='Test an endpoint after authentication')
    
    args = parser.parse_args()
    
    print("🚀 Starting robust authentication client...")
    print(f"🎯 Target URL: {args.url}")
    print(f"👤 Username: {args.username}")
    
    client = RobustAuthClient(args.url)
    
    token = client.authenticate(
        username=args.username,
        password=args.password,
        max_connection_attempts=args.max_attempts
    )
    
    if token:
        print(f"✅ Authentication successful!")
        print(f"🔑 Token: {token[:20]}...{token[-10:] if len(token) > 30 else token}")
        
        if args.test_endpoint:
            print(f"🧪 Testing endpoint: {args.test_endpoint}")
            response = client.make_authenticated_request('GET', args.test_endpoint)
            if response:
                print(f"📊 Response status: {response.status_code}")
                try:
                    print(f"📄 Response data: {json.dumps(response.json(), indent=2)}")
                except:
                    print(f"📄 Response text: {response.text}")
    else:
        print("❌ Authentication failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
