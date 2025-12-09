# 🎵 Spotify to YouTube Music Sync

Automatically sync your Spotify playlists to YouTube Music with a simple, easy-to-use tool. No complex OAuth setup, no Google Cloud project needed!

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## ✨ Features

- ✅ **Simple Setup** - 2-minute YouTube Music authentication (browser-based)
- ✅ **Smart Sync** - Detects duplicates and skips already-synced songs
- ✅ **Batch Sync** - Sync multiple playlists at once
- ✅ **Dry Run Mode** - Preview changes before syncing
- ✅ **Interactive Menu** - Easy-to-use interface with `app.py`
- ✅ **Auto-Sync** - Optional Windows startup integration
- ✅ **Detailed Logging** - Track all sync operations

## 📋 Prerequisites

- **Python 3.8+** installed
- **Spotify Account** (Free or Premium)
- **YouTube Music Account** (Free or Premium)
- **Windows/Linux/macOS** (Windows-specific features for auto-sync)

## 🚀 Quick Start

### 1️⃣ Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/spotify-ytmusic-sync.git
cd spotify-ytmusic-sync
pip install -r requirements.txt
```

### 2️⃣ Configure Credentials

Copy the example config file:
```bash
cp config.example.py config.py  # Linux/Mac
copy config.example.py config.py  # Windows
```

Edit `config.py` with your credentials (see setup sections below).

### 3️⃣ Setup Spotify

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Click **"Create App"**
   - App name: `Playlist Sync` (or anything you like)
   - App description: `Personal playlist sync tool`
   - Redirect URI: `http://127.0.0.1:8888/callback`
3. Copy your **Client ID** and **Client Secret**
4. Update `config.py`:
   ```python
   SPOTIFY_CLIENT_ID = "your_client_id_here"
   SPOTIFY_CLIENT_SECRET = "your_client_secret_here"
   ```

### 4️⃣ Setup YouTube Music (2 Minutes!)

**No Google Cloud project needed!** Just run the setup script:

```bash
python setup_browser_auth.py
```

Follow the on-screen instructions:
1. Open https://music.youtube.com (make sure you're **signed in**)
2. Press **F12** → **Network** tab
3. Type `browse` in the filter box
4. Click **"Library"** in YouTube Music sidebar
5. Find a **POST** request to `browse?...`
6. Copy the request headers:
   - **Firefox**: Right-click → Copy → Copy Request Headers ✅ (Easiest!)
   - **Chrome/Edge**: Copy from `accept: */*` to end of Request Headers section

7. Paste into the terminal and press Enter twice

That's it! No OAuth, no API keys, no complexity. 🎉

### 5️⃣ Configure Playlists

Edit `config.py` and add your playlist mappings:

```python
# Get Spotify playlist ID from URL:
# https://open.spotify.com/playlist/2XgBQIJKjArcbF2Smfjxc2
#                                   ^^^^^^ This part ^^^^^^

# Get YouTube Music playlist ID from URL:
# https://music.youtube.com/playlist?list=PLY3LuyWhQkjoEvyml9yoPi8IOsXQNjE8f
#                                          ^^^^^^^^^^^^^ This part ^^^^^^^^^^^^^

PLAYLIST_MAPPING = {
    "2XgBQIJKjArcbF2Smfjxc2": "PLY3LuyWhQkjoEvyml9yoPi8IOsXQNjE8f",
    # Add more mappings below:
    # "SPOTIFY_PLAYLIST_ID": "YTMUSIC_PLAYLIST_ID",
}
```

### 6️⃣ Run Your First Sync!

**Interactive Menu** (Recommended for first-time users):
```bash
python app.py
```

**Direct Sync**:
```bash
# Preview what will be synced (recommended first!)
python sync_playlists.py --dry-run

# Actually sync
python sync_playlists.py
```

**Test Connections**:
```bash
python sync_playlists.py --test-spotify
python sync_playlists.py --test-ytmusic
```

---

## 🔧 Configuration Options

All settings are in `config.py`:

| Setting | Description | Default |
|---------|-------------|---------|
| `SPOTIFY_CLIENT_ID` | Your Spotify app client ID | Required |
| `SPOTIFY_CLIENT_SECRET` | Your Spotify app client secret | Required |
| `PLAYLIST_MAPPING` | Spotify→YouTube playlist mappings | `{}` |
| `YTMUSIC_PLAYLIST_PRIVATE` | Create playlists as private | `True` |
| `DRY_RUN` | Preview mode (no actual changes) | `False` |
| `MAX_SEARCH_RESULTS` | Search result limit per song | `5` |

---

## 🤖 Auto-Sync on Windows Login

Want your playlists to sync automatically when you log in?

### Option A: Startup Folder (Simplest)

1. Press `Win + R`, type `shell:startup`, press Enter
2. Copy `run_sync.bat` into the folder that opens
3. Done! Syncs on every login

### Option B: Task Scheduler (Waits for Internet)

1. Open **Task Scheduler**
2. **Create Basic Task**
   - Name: `Spotify YT Music Sync`
   - Trigger: **When I log on**
   - Action: **Start a program**
     - Program: `python`
     - Arguments: `path\to\sync_playlists.py`
3. **Properties** → **Conditions** → ✅ **Start only if network available**

---

## 📁 Project Structure

```
spotify-ytmusic-sync/
├── app.py                    # Interactive menu interface
├── sync_playlists.py         # Main sync script
├── setup_browser_auth.py     # YT Music setup (browser auth)
├── config.example.py         # Configuration template
├── config.py                 # Your credentials (git-ignored)
├── requirements.txt          # Python dependencies
├── run_sync.bat             # Windows auto-sync batch file
├── .gitignore               # Protects sensitive files
└── README.md                # This file
```

**Auto-generated files** (git-ignored):
- `browser_auth.json` - YouTube Music authentication
- `.spotify_cache` - Spotify OAuth tokens
- `sync_cache.json` - Sync history (prevents duplicates)
- `sync_log.txt` - Detailed sync logs

---

## 🔍 How It Works

1. **Fetches** songs from your Spotify playlists
2. **Searches** for each song on YouTube Music
3. **Detects** duplicates using smart matching:
   - Exact video ID matching
   - Normalized title/artist matching
   - Fuzzy similarity matching (70%+ threshold)
4. **Adds** only new songs to your YouTube Music playlists
5. **Caches** synced songs to prevent re-adding

### Duplicate Detection

The tool uses multiple methods to prevent duplicates:

- **Cache-based**: Tracks previously synced songs
- **Exact match**: Compares video IDs
- **Normalized match**: Removes special chars, compares names
- **Fuzzy match**: 70%+ similarity on cleaned names

---

## 🛠️ Troubleshooting

### "Spotify auth failed"
- ✅ Check Client ID/Secret in `config.py`
- ✅ Verify redirect URI: `http://127.0.0.1:8888/callback`
- ✅ Ensure app has correct settings in Spotify Dashboard

### "YouTube Music not configured"
- ✅ Run `python setup_browser_auth.py`
- ✅ Make sure you copied **POST** request headers (not GET)
- ✅ Copy from `music.youtube.com` (not regular youtube.com)
- ✅ Try Firefox for easier header copying

### "Song not found on YouTube Music"
- Some songs may not be available on YouTube Music
- Different region availability
- Check `sync_log.txt` for details
- Try searching manually on YouTube Music

### Headers expire / "401 Unauthorized"
- Browser authentication cookies expire periodically
- Re-run `python setup_browser_auth.py` to get fresh headers
- Copy new headers from browser

---

## 📊 Command Reference

```bash
# Interactive menu
python app.py

# Sync commands
python sync_playlists.py              # Full sync
python sync_playlists.py --dry-run    # Preview only (recommended first!)

# Testing
python sync_playlists.py --test-spotify   # Test Spotify connection
python sync_playlists.py --test-ytmusic   # Test YouTube Music connection
```

---

## 🔐 Security & Privacy

**This tool stores credentials locally:**
- Your Spotify credentials are in `config.py`
- YouTube Music cookies are in `browser_auth.json`
- All sensitive files are protected by `.gitignore`

**Never commit these files to Git!**

If you fork this repo:
1. Use `config.example.py` as a template
2. Create your own `config.py` locally
3. Never push `config.py` or `browser_auth.json`

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 💡 Credits

- **Spotify API**: [Spotipy](https://github.com/spotipy-dev/spotipy)
- **YouTube Music API**: [ytmusicapi](https://github.com/sigma67/ytmusicapi)

---

## ⭐ Support

If you find this tool useful, please consider:
- ⭐ Starring the repository
- 🐛 Reporting bugs via Issues
- 💡 Suggesting features
- 🔀 Contributing code

---

## 📧 Contact

Have questions? Open an issue on GitHub!

---

**Made with ❤️ for music lovers who use both Spotify and YouTube Music**

