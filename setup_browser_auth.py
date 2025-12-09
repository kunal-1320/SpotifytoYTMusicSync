#!/usr/bin/env python3
"""
YouTube Music Browser Authentication Setup
===========================================
Simple 2-minute setup - just copy request headers from your browser!
No Google Cloud project or OAuth setup needed.
"""

import os
import json

def print_instructions():
    """Print detailed browser-specific instructions."""
    print()
    print("=" * 70)
    print("  YOUTUBE MUSIC SETUP - Simple Browser Authentication")
    print("=" * 70)
    print()
    print("This is EASY! Just follow the steps for your browser:")
    print()
    print("-" * 70)
    print("STEP 1: Open YouTube Music and Sign In")
    print("-" * 70)
    print("  1. Go to: https://music.youtube.com")
    print("  2. Make sure you're SIGNED IN with your Google account")
    print()
    print("-" * 70)
    print("STEP 2: Open Developer Tools")
    print("-" * 70)
    print("  • Press F12 (or Right-click → Inspect)")
    print("  • Click the 'Network' tab at the top")
    print()
    print("-" * 70)
    print("STEP 3: Find an Authenticated Request")
    print("-" * 70)
    print("  • In the Network tab filter box, type: browse")
    print("  • Click on 'Library' in YouTube Music (left sidebar)")
    print("  • Look for a POST request with these details:")
    print("      ✓ Status: 200")
    print("      ✓ Method: POST")
    print("      ✓ Name/File: browse?...")
    print()
    print("-" * 70)
    print("STEP 4: Copy Request Headers (BROWSER-SPECIFIC)")
    print("-" * 70)
    print()
    print("  📌 FIREFOX (Recommended):")
    print("     • Click on the 'browse' request")
    print("     • Right-click → Copy → Copy Request Headers")
    print("     • Done! That's it.")
    print()
    print("  📌 CHROME / EDGE:")
    print("     • Click on the 'browse' request")
    print("     • In the 'Headers' tab on the right")
    print("     • Scroll to 'Request Headers' section")
    print("     • Select and copy EVERYTHING from 'accept: */*' to the end")
    print()
    print("=" * 70)
    print()

def parse_headers(headers_text):
    """Parse raw request headers into a dictionary."""
    headers = {}
    lines = headers_text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if ':' in line:
            key, value = line.split(':', 1)
            headers[key.strip().lower()] = value.strip()
    
    return headers

def main():
    print_instructions()
    
    print("Paste your request headers below (then press Enter twice):")
    print("-" * 70)
    
    # Collect multi-line input
    lines = []
    empty_count = 0
    while True:
        try:
            line = input()
            if line.strip() == "":
                empty_count += 1
                if empty_count >= 2:  # Two empty lines = done
                    break
            else:
                empty_count = 0
                lines.append(line)
        except EOFError:
            break
    
    headers_text = '\n'.join(lines)
    
    if not headers_text or len(headers_text) < 100:
        print()
        print("❌ Error: Headers seem too short or empty.")
        print("   Make sure you copied the full request headers.")
        input("\nPress Enter to exit...")
        return
    
    # Parse headers
    try:
        headers = parse_headers(headers_text)
        
        # Verify we have the essential headers
        if 'cookie' not in headers:
            print()
            print("❌ Error: No 'cookie' found in headers.")
            print("   Make sure you copied the full request headers including the cookie.")
            input("\nPress Enter to exit...")
            return
        
        # Check if this looks like YouTube Music headers
        if 'music.youtube.com' not in headers.get('origin', '') and \
           'music.youtube.com' not in headers.get('referer', ''):
            print()
            print("⚠️  Warning: Headers don't seem to be from music.youtube.com")
            print("   Make sure you're copying from YouTube MUSIC, not regular YouTube!")
            print()
            choice = input("Continue anyway? (y/N): ").strip().lower()
            if choice != 'y':
                return
        
        # Create auth file with parsed headers
        auth_data = {
            "accept": headers.get("accept", "*/*"),
            "accept-language": headers.get("accept-language", "en-US,en;q=0.9"),
            "content-type": headers.get("content-type", "application/json"),
            "cookie": headers["cookie"],
            "user-agent": headers.get("user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"),
            "x-goog-authuser": headers.get("x-goog-authuser", "0"),
            "origin": headers.get("origin", "https://music.youtube.com")
        }
        
        # Add optional headers if present
        if "authorization" in headers:
            auth_data["authorization"] = headers["authorization"]
        if "x-goog-visitor-id" in headers:
            auth_data["x-goog-visitor-id"] = headers["x-goog-visitor-id"]
        if "referer" in headers:
            auth_data["referer"] = headers["referer"]
        
        # Save to file
        auth_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser_auth.json")
        with open(auth_path, "w") as f:
            json.dump(auth_data, f, indent=2)
        
        print()
        print("✅ Headers saved to browser_auth.json")
        print()
        print("Testing connection...")
        
        # Test the connection with better error handling
        try:
            from ytmusicapi import YTMusic
            ytm = YTMusic(auth_path)
            
            # Try a simple search first (more reliable than get_library_playlists)
            try:
                search_result = ytm.search('test', filter='songs', limit=1)
                
                if search_result and len(search_result) > 0:
                    print()
                    print("=" * 70)
                    print("  ✅ SUCCESS! YouTube Music is connected and working!")
                    print("=" * 70)
                    print()
                    print("You can now:")
                    print("  • Run the main app: python app.py")
                    print("  • Or sync directly: python sync_playlists.py")
                    print()
                else:
                    print()
                    print("⚠️  Connection test completed, but results are unclear.")
                    print()
                    print("The headers are saved. Try running the sync to see if it works:")
                    print("  python sync_playlists.py --test-ytmusic")
                    
            except Exception as search_error:
                error_str = str(search_error)
                if "401" in error_str or "unauthorized" in error_str.lower():
                    print()
                    print("❌ Authentication failed!")
                    print()
                    print("Common fixes:")
                    print("  1. Make sure you copied from music.youtube.com (not youtube.com)")
                    print("  2. Copy from a 'browse' POST request, not GET")
                    print("  3. Make sure you're logged in to YouTube Music")
                    print("  4. Try copying fresh headers (cookies expire)")
                    print()
                elif "400" in error_str or "bad request" in error_str.lower():
                    print()
                    print("⚠️  Request format issue")
                    print()
                    print("This usually means:")
                    print("  • Headers might be incomplete")
                    print("  • Try copying from a different 'browse' request")
                    print("  • Make sure you selected the FULL headers")
                    print()
                else:
                    print()
                    print(f"⚠️  Connection test error: {search_error}")
                    print()
                    print("Headers are saved, but verification failed.")
                    print("Try running the sync to see if it works anyway:")
                    print("  python sync_playlists.py --test-ytmusic")
                    print()
                    
        except ImportError:
            print()
            print("❌ ytmusicapi not installed!")
            print("   Run: pip install ytmusicapi")
        except Exception as e:
            print()
            print(f"⚠️  Unexpected error: {e}")
            print()
            print("Headers saved. Try testing with:")
            print("  python sync_playlists.py --test-ytmusic")
    
    except Exception as e:
        print()
        print(f"❌ Error: {e}")
        print("   Something went wrong parsing the headers.")
        print("   Make sure you copied the raw request headers correctly.")
    
    print()
    input("Press Enter to exit...")

if __name__ == "__main__":
    main()
