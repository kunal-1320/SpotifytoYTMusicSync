## Spotify to YouTube Music Sync

Sync your Spotify playlists to YouTube Music automatically with high-performance, "No-API" technology.

## Why this version?

This project has been overhauled for **maximum speed** and **zero friction**:
- **No Spotify API Keys**: Uses a clean web-scraping engine. No developer account needed.
- **High-Performance Engine**: Parallel data fetching and multi-threaded sync processing.
- **Smart Matching**: Uses `RapidFuzz` for 100x faster track identification.
- **Large Playlist Support**: Robustly handles 1000+ tracks using Spotify's internal Pathfinder API.

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/kunal-1320/SpotifytoYTMusicSync.git
cd SpotifytoYTMusicSync

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create config file
# Windows: copy config.example.py config.py
# Mac/Linux: cp config.example.py config.py

# 4. Run the interactive menu
python app.py
```

### Setup Steps:
1.  **YTMusic Setup** — Authenticate with YouTube Music (simple browser copy-paste).
2.  **Add Playlist IDs** — Add your Spotify Playlist ID to `config.py`.
3.  **Sync Now** — Let the multi-threaded engine do the work.

---

## Features

- **Concurrent Engine** — Fetches Spotify and YouTube data in parallel to cut wait times by 50%.
- **No-API Dependency** — Bypasses official Spotify API limits and premium requirements.
- **Smart Sync** — Detects duplicates automatically and skips already-synced tracks via local caching.
- **Auto-Validation** — Identifies broken mappings and detects session expiry automatically.
- **Dry Run Mode** — Preview exactly what will happen before any changes are made.

---

## Detailed Configuration

### 1. YouTube Music Setup
Run `python setup_browser_auth.py` or use the option in `app.py`.
- **Firefox:** Copy "Request Headers".
- **Chrome/Brave:** Copy as "cURL (bash)".

### 2. Playlist Mapping
Open `config.py` and add your IDs:
```python
SPOTIFY_PLAYLIST_IDS = ['37i9dQZF1DXcBWIGNy_...']

# OR use Advanced Mapping
PLAYLIST_MAPPING = {
    "SPOTIFY_ID": "YT_MUSIC_PLAYLIST_ID",
}
```

---

## Project Structure

- `app.py` — The interactive control center.
- `sync_playlists.py` — High-performance synchronization engine (Multi-threaded).
- `setup_browser_auth.py` — Authentication helper for YT Music.
- `config.py` — Your local configuration (Git-ignored).
- `utils/` — Logic for scraper clients, UI formatting, and validation.

## Security & Privacy
This tool runs **entirely locally**. No data is ever sent to third-party servers.
- `browser_auth.json` — Stores your local session (Git-ignored).
- `sync_cache.json` — Stores your sync history (Git-ignored).
