# =============================================================================
# SPOTIFY TO YOUTUBE MUSIC SYNC - CONFIGURATION
# =============================================================================
# Fill in your credentials below. Follow README.md for setup instructions.
#
# IMPORTANT: After filling this out, rename this file to config.py
# DO NOT commit config.py to GitHub - it's in .gitignore for your safety!

# -----------------------------------------------------------------------------
# SPOTIFY SETTINGS
# -----------------------------------------------------------------------------
# Get these from https://developer.spotify.com/dashboard
# 1. Create a new app
# 2. Copy Client ID and Client Secret
# 3. Add http://127.0.0.1:8888/callback as Redirect URI

SPOTIFY_CLIENT_ID = "YOUR_SPOTIFY_CLIENT_ID"
SPOTIFY_CLIENT_SECRET = "YOUR_SPOTIFY_CLIENT_SECRET"
SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8888/callback"

# Spotify playlist IDs to sync (you can add multiple)
# To get playlist ID: Open playlist in Spotify > Share > Copy link
# The ID is the part after /playlist/ (e.g., 37i9dQZF1DXcBWIGoYBM5M)
SPOTIFY_PLAYLIST_IDS = [
    "YOUR_SPOTIFY_PLAYLIST_ID",
    # "YOUR_PLAYLIST_ID_2",  # Uncomment to add more
]

# -----------------------------------------------------------------------------
# YOUTUBE MUSIC SETTINGS
# -----------------------------------------------------------------------------
# Set up YouTube Music browser authentication by running: python setup_browser_auth.py

# =============================================================================
# PLAYLIST MAPPING (Spotify -> YouTube Music)
# =============================================================================
# Map each Spotify playlist ID to a YouTube Music playlist ID
# 
# To get Spotify playlist ID:
#   Open playlist -> Share -> Copy link -> get ID after /playlist/
#
# To get YouTube Music playlist ID:
#   Open playlist -> copy URL -> get ID after ?list= (starts with PL...)
#
# Format: "SPOTIFY_ID": "YTMUSIC_ID"

PLAYLIST_MAPPING = {
    # Example: "2XgBQIJKjArcbF2Smfjxc2": "PLY3LuyWhQkjoEvyml9yoPi8IOsXQNjE8f",
    
    # Add your mappings below:
}

# Fallback: If a Spotify playlist is NOT in PLAYLIST_MAPPING,
# songs will be added to this default YouTube Music playlist
YTMUSIC_PLAYLIST_NAME = "Synced from Spotify"
YTMUSIC_PLAYLIST_ID = None  # Set to a playlist ID to use as default

# Set to True to create the playlist as private (False = public)
YTMUSIC_PLAYLIST_PRIVATE = True

# -----------------------------------------------------------------------------
# SYNC SETTINGS
# -----------------------------------------------------------------------------
# Set to True to only show what would be synced without actually adding songs
DRY_RUN = False

# Path to log file
LOG_FILE = "sync_log.txt"

# How many search results to check when finding a song on YT Music
# Higher = more accurate but slower
MAX_SEARCH_RESULTS = 5
