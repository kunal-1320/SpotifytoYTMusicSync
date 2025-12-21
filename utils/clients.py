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
    Create and return an authenticated Spotify client.
    
    Returns:
        spotipy.Spotify: Authenticated Spotify client
    
    Raises:
        ImportError: If spotipy is not installed
        Exception: If authentication fails
    """
    try:
        import spotipy
        from spotipy.oauth2 import SpotifyOAuth
        import config
    except ImportError as e:
        raise ImportError(f"Required package not installed: {e}")
    
    try:
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=config.SPOTIFY_CLIENT_ID,
            client_secret=config.SPOTIFY_CLIENT_SECRET,
            redirect_uri=config.SPOTIFY_REDIRECT_URI,
            scope="playlist-read-private playlist-read-collaborative"
        ))
        return sp
    except Exception as e:
        raise Exception(f"Failed to authenticate with Spotify: {e}")


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
    Test Spotify connection and return user info.
    
    Returns:
        Tuple of (success: bool, message: str, user_info: dict or None)
    """
    try:
        sp = get_spotify_client()
        user = sp.current_user()
        return (True, f"Connected as: {user['display_name']}", user)
    except Exception as e:
        return (False, str(e), None)


def test_ytmusic_connection() -> tuple:
    """
    Test YouTube Music connection.
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        ytm = get_ytmusic_client()
        # Try a simple search to verify the connection works
        result = ytm.search('test', filter='songs', limit=1)
        if result:
            return (True, "YouTube Music connected and working!")
        else:
            return (True, "Connected but no search results (may still work)")
    except Exception as e:
        return (False, str(e))


def check_spotify_configured() -> bool:
    """Check if Spotify credentials are configured."""
    try:
        import config
        if (hasattr(config, 'SPOTIFY_CLIENT_ID') and 
            config.SPOTIFY_CLIENT_ID and 
            config.SPOTIFY_CLIENT_ID != "YOUR_SPOTIFY_CLIENT_ID"):
            return True
    except Exception:
        pass
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
        success, msg = test_ytmusic_connection()
        print(f"YouTube Music connection: {'OK' if success else 'FAILED'} - {msg}")
