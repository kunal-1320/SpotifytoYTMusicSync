# =============================================================================
# Spotify to YouTube Music Sync - CONFIGURATION
# =============================================================================

# 1. SPOTIFY CONFIGURATION
# -----------------------------------------------------------------------------
# Add your Spotify playlist IDs here (the part after /playlist/ in the URL)
# Example: https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M -> '37i9dQZF1DXcBWIGoYBM5M'
SPOTIFY_PLAYLIST_IDS = [
    'YOUR_SPOTIFY_PLAYLIST_ID_HERE',
]

# 2. YOUTUBE MUSIC CONFIGURATION
# -----------------------------------------------------------------------------
# Default YouTube Music playlist ID where all Spotify tracks will be synced.
# If left as None, the script will look for a playlist named 'Spotify Sync'
YTMUSIC_PLAYLIST_ID = 'YOUR_YTM_PLAYLIST_ID_HERE'

# If True, new playlists created by the script will be private.
YTMUSIC_PLAYLIST_PRIVATE = True

# 3. PLAYLIST MAPPING (Advanced)
# -----------------------------------------------------------------------------
# Map specific Spotify playlists to specific YouTube Music playlists.
# Format: 'Spotify_Playlist_ID': 'YouTube_Music_Playlist_ID'
PLAYLIST_MAPPING = {
    # 'SPOTIFY_ID': 'YTM_ID',
}

# 4. GENERAL SETTINGS
# -----------------------------------------------------------------------------
# Maximum results to consider when searching on YouTube Music (1-5 recommended)
MAX_SEARCH_RESULTS = 3

# File to store logs
LOG_FILE = "sync_log.txt"
