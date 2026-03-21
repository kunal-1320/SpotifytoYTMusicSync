"""
Clients Module - Centralized Spotify and YouTube Music client initialization
============================================================================
Single source of truth for API client creation and authentication.
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_spotify_client():
    """
    Create and return a Spotify scraper client.
    
    Returns:
        SpotifyClient: Scraper client
    
    Raises:
        ImportError: If spotify_scraper is not installed
    """
    try:
        from spotify_scraper import SpotifyClient
        return SpotifyClient()
    except ImportError as e:
        raise ImportError(f"Required package not installed: {e}")
    except Exception as e:
        raise Exception(f"Failed to initialize Spotify scraper: {e}")


def get_ytmusic_client():
    """
    Create and return an authenticated YouTube Music client.
    
    Returns:
        YTMusic: Authenticated YouTube Music client
    
    Raises:
        FileNotFoundError: If browser_auth.json doesn't exist
        ImportError: If ytmusicapi is not installed
        Exception: If authentication fails
    """
    try:
        from ytmusicapi import YTMusic
    except ImportError:
        raise ImportError("ytmusicapi not installed. Run: pip install ytmusicapi")
    
    # Look for auth file in main directory
    auth_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'browser_auth.json'
    )
    
    if not os.path.exists(auth_file):
        raise FileNotFoundError(
            f"YouTube Music authentication file '{auth_file}' not found.\n"
            "Please run 'python setup_browser_auth.py' first."
        )
    
    try:
        ytm = YTMusic(auth_file)
        return ytm
    except Exception as e:
        raise Exception(f"Failed to authenticate with YouTube Music: {e}")


def test_spotify_connection() -> tuple:
    """
    Test Spotify connection by attempting to initialize the scraper.
    
    Returns:
        Tuple of (success: bool, message: str, info: dict or None)
    """
    try:
        client = get_spotify_client()
        # No easy way to get "user info" without API, but we can verify scraping works
        return (True, "Spotify Scraper initialized (No-API mode)", {"mode": "scraping"})
    except Exception as e:
        return (False, str(e), None)


def test_ytmusic_connection() -> tuple:
    """
    Test YouTube Music connection.
    
    Returns:
        Tuple of (success: bool, message: str, error_type: str)
        error_type can be: 'none', 'auth', 'network', 'unknown'
    """
    try:
        ytm = get_ytmusic_client()
        # Try a simple search to verify the connection works
        result = ytm.search('test', filter='songs', limit=1)
        if result:
            return (True, "YouTube Music connected and working!", 'none')
        else:
            return (True, "Connected but no search results (may still work)", 'none')
    except FileNotFoundError as e:
        return (False, str(e), 'auth')
    except Exception as e:
        error_str = str(e).lower()
        
        # Check for authentication errors
        if '401' in error_str or 'unauthorized' in error_str or 'authentication' in error_str:
            return (False, "YouTube Music headers have expired. Please re-run: python setup_browser_auth.py", 'auth')
        
        # Network errors
        if 'network' in error_str or 'connection' in error_str:
            return (False, str(e), 'network')
        
        return (False, str(e), 'unknown')


def check_spotify_configured() -> bool:
    """Check if Spotify scraper is available."""
    try:
        from spotify_scraper import SpotifyClient
        return True
    except ImportError:
        return False


def check_ytmusic_configured() -> bool:
    """Check if YouTube Music auth file exists."""
    auth_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'browser_auth.json'
    )
    return os.path.exists(auth_file)


# Self-test
if __name__ == "__main__":
    print("Testing clients module...")
    print()
    
    print(f"Spotify configured: {check_spotify_configured()}")
    print(f"YouTube Music configured: {check_ytmusic_configured()}")
    print()
    
    if check_spotify_configured():
        success, msg, _ = test_spotify_connection()
        print(f"Spotify connection: {'OK' if success else 'FAILED'} - {msg}")
    
    if check_ytmusic_configured():
        success, msg, error_type = test_ytmusic_connection()
        print(f"YouTube Music connection: {'OK' if success else 'FAILED'} - {msg}")
