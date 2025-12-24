How to use :
* git clone https://github.com/kunal-1320/SpotifytoYTMusicSync.git
* cd SpotifytoYTMusicSync
* pip install -r requirements.txt
* cp config.example.py config.py
* Then, Run app.py
    * 1. setup spotify  --> to check go to manage playlist--->view spotify playlist
    * 2. setup ytmusic  --> same for this 
    * 3. Map the playlist --> little labour work
    * OR
    * 3. Auto Create playlist
    * 4. Dry sync run
    * 5. Main Sync
     
NOTE : youtubemus request headers get expired automatically so when you want you can setup ytmusic again

FUTURE UPDATE:
1. STATUS if request header is expired
2. playlist mapping validation can't differentiate between request header auth expiration and missing playlist.( so it removes the mapping no matter what)
3. I still don't know request header thing works on chrome or not ( currently using firefox)

=====================================================================================
# Spotify to YouTube Music Sync

Sync your Spotify playlists to YouTube Music automatically.

## Features

- **Simple Setup** - No Google Cloud project needed, just browser authentication
- **Smart Sync** - Detects duplicates, skips already-synced songs
- **Auto-validation** - Automatically removes broken playlist mappings
- **Batch Sync** - Sync multiple playlists at once
- **Dry Run** - Preview changes before syncing

## Requirements

- Python 3.8+
- Spotify account
- YouTube Music account

## Installation

```bash
git clone https://github.com/yourusername/SpotifytoYTMusicSync.git
cd SpotifytoYTMusicSync
pip install -r requirements.txt
```

## Setup

### 1. Create Config File
in command prompt ---> same location in the directory
```bash
cp config.example.py config.py
```

### 2. Setup Spotify

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create an app
3. Set Redirect URI to: `http://127.0.0.1:8888/callback`
4. Copy Client ID and Secret to `config.py`   ---> also can be done from app.py

### 3. Setup YouTube Music
---> can be also done from app.py
```bash
python setup_browser_auth.py
```

Follow the instructions to copy request headers from your browser. (use firefox, i haven't test from chrome/brave tho)

### 4. Add Playlist Mappings

Edit `config.py`:

```python
PLAYLIST_MAPPING = {
    "SPOTIFY_PLAYLIST_ID": "YTMUSIC_PLAYLIST_ID",
}
```

**Finding IDs:**  When you open you playlists in browser. 
- Spotify: `https://open.spotify.com/playlist/[ID]`
- YouTube Music: `https://music.youtube.com/playlist?list=[ID]`

## Usage

### Interactive Menu (Recommended)

```bash
python app.py
```

### Command Line

```bash
python sync_playlists.py --dry-run  # Preview
python sync_playlists.py            # Sync
```

## Project Structure

```
SpotifytoYTMusicSync/
├── app.py                 # Interactive menu
├── sync_playlists.py      # Main sync script
├── setup_browser_auth.py  # YouTube Music setup
├── config.example.py      # Config template
├── config_updater.py      # Config management
├── utils/                 # Shared utilities
└── requirements.txt
```

## Auto-Sync (Windows)

1. Press `Win+R`, type `shell:startup`
2. Copy `run_sync.bat` into the folder
3. Playlists sync on every login

## Security

These files contain your credentials and are git-ignored:
- `config.py` - Your API keys
- `browser_auth.json` - YouTube cookies

**Never commit these files!**






