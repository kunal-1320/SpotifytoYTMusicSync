#!/usr/bin/env python3
"""
YouTube Music OAuth Setup Script
================================

⚠️  DEPRECATION NOTICE ⚠️
========================
This OAuth setup method is DEPRECATED and unnecessarily complex.

We now recommend the SIMPLER browser authentication method instead:
  → Run: python setup_browser_auth.py

Browser auth:
  ✅ No Google Cloud project needed
  ✅ No OAuth consent screen
  ✅ No API enabling
  ✅ 2-minute setup instead of 10-15 minutes
  ✅ Same functionality

This file is kept for backward compatibility only.
If you still want to use OAuth, continue below.
========================

Uses Google's OAuth Device Authorization flow.
"""

import os
import sys
import json
import time

print()
print("=" * 60)
print("⚠️  DEPRECATION WARNING")
print("=" * 60)
print()
print("This OAuth setup is now DEPRECATED.")
print("We recommend using the simpler browser auth method instead:")
print()
print("  → Run: python setup_browser_auth.py")
print()
print("Browser auth is much easier (2 minutes vs 10-15 minutes)")
print("and doesn't require a Google Cloud project.")
print()
choice = input("Continue with OAuth anyway? (y/N): ").strip().lower()

if choice != 'y':
    print()
    print("Good choice! Run: python setup_browser_auth.py")
    print()
    sys.exit(0)

print()
print("Continuing with OAuth setup...")
print()

try:
    import requests
except ImportError:
    print("Installing requests...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests


def main():
    print("=" * 60)
    print("YOUTUBE MUSIC OAUTH SETUP")
    print("=" * 60)
    print()
    print("This script will help you set up YouTube Music authentication.")
    print("You only need to do this ONCE.")
    print()
    print("-" * 60)
    print("STEP 1: Google Cloud Console Setup")
    print("-" * 60)
    print("""
1. Go to: https://console.cloud.google.com/
2. Create a new project (or select existing)
3. Go to "APIs & Services" > "Library"
4. Search for "YouTube Data API v3" and ENABLE it
5. Go to "APIs & Services" > "OAuth consent screen"
   - Choose "External" user type
   - Fill in app name (e.g., "Spotify Sync")
   - Add your email as test user
6. Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Application type: "TVs and Limited Input devices"
   - Name it anything (e.g., "Spotify Sync Client")
7. Copy the Client ID and Client Secret shown
""")
    
    input("Press ENTER when you have your Client ID and Client Secret ready...")
    print()
    
    print("-" * 60)
    print("STEP 2: Enter Your Credentials")
    print("-" * 60)
    
    client_id = input("Enter your Client ID: ").strip()
    client_secret = input("Enter your Client Secret: ").strip()
    
    if not client_id or not client_secret:
        print("\n❌ Error: Client ID and Client Secret are required!")
        sys.exit(1)
    
    print()
    print("-" * 60)
    print("STEP 3: Device Authorization")
    print("-" * 60)
    
    # Get device code from Google
    code_response = requests.post(
        "https://oauth2.googleapis.com/device/code",
        data={
            "client_id": client_id,
            "scope": "https://www.googleapis.com/auth/youtube"
        }
    ).json()
    
    if "error" in code_response:
        error_msg = code_response.get("error_description", code_response["error"])
        print(f"\n❌ Error getting device code: {error_msg}")
        print("\nMake sure you:")
        print("1. Created 'TVs and Limited Input devices' type OAuth client")
        print("2. Enabled YouTube Data API v3")
        sys.exit(1)
    
    device_code = code_response["device_code"]
    user_code = code_response["user_code"]
    verification_url = code_response["verification_url"]
    interval = code_response.get("interval", 5)
    
    print()
    print("=" * 60)
    print("AUTHORIZATION REQUIRED")
    print("=" * 60)
    print()
    print(f"1. Go to: {verification_url}")
    print(f"2. Enter this code: {user_code}")
    print(f"3. Sign in with your Google account")
    print()
    print("=" * 60)
    print()
    print("Waiting for you to authorize", end="", flush=True)
    
    # Poll for token
    while True:
        time.sleep(interval)
        
        token_response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code"
            }
        ).json()
        
        if "access_token" in token_response:
            # Success! Save credentials
            oauth_data = {
                "access_token": token_response["access_token"],
                "refresh_token": token_response["refresh_token"],
                "token_type": token_response.get("token_type", "Bearer"),
                "expires_in": token_response.get("expires_in", 3600),
                "scope": token_response.get("scope", "https://www.googleapis.com/auth/youtube"),
                "client_id": client_id,
                "client_secret": client_secret
            }
            
            # Save to oauth.json in the same directory as this script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            oauth_path = os.path.join(script_dir, "oauth.json")
            
            with open(oauth_path, "w") as f:
                json.dump(oauth_data, f, indent=2)
            
            print()
            print()
            print("=" * 60)
            print("✅ SUCCESS! OAuth setup complete.")
            print("=" * 60)
            print()
            print(f"Created: {oauth_path}")
            print()
            print("You can now run: python sync_playlists.py")
            print()
            return
            
        elif token_response.get("error") == "authorization_pending":
            # Still waiting for user to authorize
            print(".", end="", flush=True)
            continue
        elif token_response.get("error") == "slow_down":
            # Google wants us to slow down
            interval += 2
            continue
        elif token_response.get("error") == "access_denied":
            print("\n\n❌ Authorization was denied. Please try again.")
            sys.exit(1)
        elif token_response.get("error") == "expired_token":
            print("\n\n❌ Device code expired. Please run the script again.")
            sys.exit(1)
        else:
            # Unknown error
            error_msg = token_response.get("error_description", token_response.get("error", "Unknown error"))
            print(f"\n\n❌ Error: {error_msg}")
            sys.exit(1)


if __name__ == "__main__":
    main()
