#!/usr/bin/env python3
"""
Spotify to YouTube Music Playlist Sync
=======================================
Syncs songs from Spotify playlists to YouTube Music.

Usage:
    python sync_playlists.py           # Normal sync
    python sync_playlists.py --dry-run # Preview without syncing
"""

import os
import sys
import json
import argparse
import re
import time
from datetime import datetime
from typing import Optional, List, Dict, Set, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

# Try high-performance fuzzy matching
try:
    from rapidfuzz import fuzz
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False
    from difflib import SequenceMatcher

# Third-party imports
try:
    from ytmusicapi import YTMusic
except ImportError as e:
    print(f"Missing required package: {e}")
    print("Run: pip install -r requirements.txt")
    sys.exit(1)

# Local imports
import config


# =============================================================================
# LOGGING
# =============================================================================

def log(message: str, also_print: bool = True):
    """Log a message to file and optionally print it."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] {message}"
    
    if also_print:
        # Handle Windows console encoding issues
        try:
            print(message)
        except UnicodeEncodeError:
            # Fallback: replace emoji with text equivalents
            safe_message = message.encode('ascii', errors='replace').decode('ascii')
            print(safe_message)
    
    try:
        with open(config.LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_message + "\n")
    except Exception:
        pass  # Don't fail if logging fails


# =============================================================================
# SYNC CACHE - Track what's already been synced
# =============================================================================

SYNC_CACHE_FILE = "sync_cache.json"

def load_sync_cache() -> dict:
    """Load the sync cache from file."""
    if os.path.exists(SYNC_CACHE_FILE):
        try:
            with open(SYNC_CACHE_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_sync_cache(cache: dict):
    """Save the sync cache to file."""
    try:
        with open(SYNC_CACHE_FILE, "w") as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        log(f"Warning: Could not save sync cache: {e}")

def get_synced_tracks(cache: dict, spotify_playlist_id: str, yt_playlist_id: str) -> set:
    """Get set of Spotify track IDs that have been synced to a YT playlist."""
    key = f"{spotify_playlist_id}:{yt_playlist_id}"
    return set(cache.get(key, []))

def mark_as_synced(cache: dict, spotify_playlist_id: str, yt_playlist_id: str, spotify_track_id: str):
    """Mark a Spotify track as synced to a YT playlist."""
    key = f"{spotify_playlist_id}:{yt_playlist_id}"
    if key not in cache:
        cache[key] = []
    if spotify_track_id not in cache[key]:
        cache[key].append(spotify_track_id)


# SPOTIFY FUNCTIONS
# =============================================================================

def get_spotify_client():
    """Create and return a Spotify scraper client."""
    from utils.clients import get_spotify_client as get_client
    return get_client()


def get_spotify_playlist_tracks(sp, playlist_id_or_url: str) -> list[dict]:
    """
    Get all tracks from a Spotify playlist using the scraper + pagination if needed.
    """
    import requests
    import re
    
    # Ensure we have a full URL
    if not playlist_id_or_url.startswith("http"):
        playlist_url = f"https://open.spotify.com/playlist/{playlist_id_or_url}"
        playlist_id = playlist_id_or_url
    else:
        playlist_url = playlist_id_or_url
        playlist_id = playlist_id_or_url.split('/')[-1].split('?')[0]
        
    tracks_data = []
    try:
        log(f"Fetching Spotify playlist: {playlist_url}")
        
        # 1. Get initial tracks from scraper (uses embed URL internally)
        playlist_info = sp.get_playlist_info(playlist_url)
        
        if not playlist_info:
            log(f"  [!] Could not fetch playlist info for: {playlist_url}")
            return []
            
        initial_tracks = playlist_info.get("tracks", [])
        total_in_metadata = playlist_info.get("track_count", len(initial_tracks))
        
        log(f"  [i] Initial view contains {len(initial_tracks)} tracks. Checking for more...")
        
        # Add initial tracks
        for track in initial_tracks:
            if track.get("name"):
                track_id = track.get("id") or f"{track['name']}|{track.get('artists', [{}])[0].get('name', 'unknown')}"
                artists = track.get("artists", [])
                artist_name = (artists[0].get("name") if artists and artists[0] else None) or "Unknown"
                tracks_data.append({
                    "id": track_id,
                    "name": track["name"],
                    "artist": artist_name,
                    "album": track.get("album", {}).get("name") or track.get("album_name", ""),
                })

        # Check if we need more (Spotify embed usually limits to 100)
        # We always check for more if we hit 100, just in case metadata is stale
        if len(tracks_data) >= 100:
            log(f"  [i] Checking for additional tracks via Spotify internal API...")
            
            # Use the scraper's browser to get the embed page content to extract tokens
            embed_url = playlist_url.replace("open.spotify.com/playlist/", "open.spotify.com/embed/playlist/")
            try:
                page_html = sp.browser.get_page_content(embed_url)
                # Extract accessToken from __NEXT_DATA__
                match = re.search(r'"accessToken":"([^"]+)"', page_html)
                if match:
                    access_token = match.group(1)
                    offset = len(tracks_data)
                    # Use a fresh session for pagination (Pathfinder API)
                    api_session = requests.Session()
                    
                    # 3. Get Client Token (Required for Pathfinder)
                    client_token = None
                    try:
                        ct_url = "https://clienttoken.spotify.com/v1/clienttoken"
                        ct_payload = {
                            "client_data": {
                                "client_version": "1.2.87.28.g9713df8f",
                                "client_id": "d8a5ed958d274c2e8ee717e6a4b0971d",
                                "js_sdk_data": {
                                    "device_brand": "unknown", "device_model": "unknown", 
                                    "os": "windows", "os_version": "NT 10.0", 
                                    "device_id": "d8caeebb-5238-46c7-8e24-c5d8ce07f27a", 
                                    "device_type": "computer"
                                }
                            }
                        }
                        ct_headers = {
                            "Accept": "application/json", 
                            "Content-Type": "application/json", 
                            "Origin": "https://open.spotify.com", 
                            "Referer": "https://open.spotify.com/",
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
                        }
                        ct_resp = api_session.post(ct_url, headers=ct_headers, json=ct_payload, timeout=10)
                        if ct_resp.status_code == 200:
                            client_token = ct_resp.json().get("granted_token", {}).get("token")
                    except Exception as ct_err:
                        log(f"    [!] Error getting client token: {ct_err}. Pagination might fail.")
                        
                    if not client_token:
                        log("    [!] Failed to get client token. Attempting pagination without it (may fail 429).")

                    # 4. Paginate using Pathfinder (GraphQL)
                    offset = len(tracks_data)
                    while True:
                        limit = 50 # Pathfinder usually uses 50
                        pf_url = "https://api-partner.spotify.com/pathfinder/v2/query"
                        
                        try:
                            import time
                            log(f"    - Fetching batch starting at {offset}...")
                            time.sleep(1.0) # Optimized delay
                            
                            pf_payload = {
                                "variables": {
                                    "uri": f"spotify:playlist:{playlist_id}",
                                    "offset": offset,
                                    "limit": limit
                                },
                                "operationName": "fetchPlaylistContents",
                                "extensions": {
                                    "persistedQuery": {
                                        "version": 1,
                                        "sha256Hash": "346811f856fb0b7e4f6c59f8ebea78dd081c6e2fb01b77c954b26259d5fc6763"
                                    }
                                }
                            }
                            
                            pf_headers = {
                                "Authorization": f"Bearer {access_token}",
                                "Accept": "application/json",
                                "Content-Type": "application/json",
                                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                                "Origin": "https://open.spotify.com",
                                "Referer": "https://open.spotify.com/"
                            }
                            if client_token:
                                pf_headers["client-token"] = client_token
                            
                            resp = api_session.post(pf_url, headers=pf_headers, json=pf_payload, timeout=15)
                            
                            if resp.status_code == 200:
                                page_data = resp.json()
                                items = page_data.get("data", {}).get("playlistV2", {}).get("content", {}).get("items", [])
                                if not items:
                                    log(f"    - Finished: Reached end of playlist.")
                                    break
                                
                                batch_count = 0
                                for item_entry in items:
                                    # Pathfinder structure is nested: item -> itemV2 -> data
                                    item_v2 = item_entry.get("itemV2", {})
                                    track = item_v2.get("data", {})
                                    
                                    if track and track.get("__typename") == "Track" and track.get("name"):
                                        artists_list = track.get("artists", {}).get("items", [])
                                        artist_name = (artists_list[0].get("profile", {}).get("name") if artists_list else "Unknown")
                                        
                                        tracks_data.append({
                                            "id": track.get("uri", "").split(":")[-1],
                                            "name": track["name"],
                                            "artist": artist_name,
                                            "album": track.get("albumOfTrack", {}).get("name") or "",
                                        })
                                        batch_count += 1
                                    elif track and track.get("__typename") == "Episode" and track.get("name"):
                                        # Handle podcast episodes too!
                                        tracks_data.append({
                                            "id": track.get("uri", "").split(":")[-1],
                                            "name": track["name"],
                                            "artist": track.get("showV2", {}).get("data", {}).get("name") or "Podcast",
                                            "album": "Podcast",
                                        })
                                        batch_count += 1
                                        
                                offset += len(items)
                                log(f"    - Success: {len(tracks_data)} tracks now in memory")
                                if len(items) < limit:
                                    log(f"    - Reached end of playlist (received {len(items)}/{limit} items).")
                                    break
                            elif resp.status_code == 429:
                                retry_after = int(resp.headers.get("Retry-After", 10))
                                log(f"    [!] Rate limited (429). Waiting {retry_after}s...")
                                time.sleep(retry_after)
                                continue # Retry this batch
                            else:
                                log(f"    [!] Pathfinder API failed ({resp.status_code}). Stopping at {len(tracks_data)}.")
                                break
                        except Exception as req_err:
                            log(f"    [!] Request error during pagination: {req_err}")
                            break
                    api_session.close()
                else:
                    log("    [!] Could not extract access token for pagination. Syncing first 100 tracks only.")
            except Exception as pe:
                log(f"    [!] Pagination error: {pe}")
                
    except Exception as e:
        log(f"  [!] Error scraping playlist {playlist_url}: {e}")
    
    return tracks_data


def test_spotify_auth():
    """Test Spotify scraping capability."""
    try:
        sp = get_spotify_client()
        print("✅ Spotify Scraper initialized!")
        
        # Try to scrape a common public playlist as a test
        test_url = "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M" # Today's Top Hits
        print(f"Testing scraper with: {test_url}")
        playlist = sp.get_playlist_info(test_url)
        
        if playlist:
            print(f"✅ Successfully scraped: {playlist.get('name')} ({len(playlist.get('tracks', []))} tracks)")
            return True
        else:
            print("❌ Scraper returned no data.")
            return False
    except Exception as e:
        print(f"❌ Spotify test failed: {e}")
        return False


# =============================================================================
# YOUTUBE MUSIC FUNCTIONS
# =============================================================================

def get_ytmusic_client() -> YTMusic:
    """Create and return an authenticated YouTube Music client."""
    
    browser_auth_path = "browser_auth.json"
    
    # Use browser auth for searching (works with v1.9.0)
    # We'll use direct YouTube API for writing separately
    if os.path.exists(browser_auth_path):
        return YTMusic(browser_auth_path)
    
    raise FileNotFoundError(
        "No YouTube Music authentication found!\n"
        "Run 'python setup_browser_auth.py' to set up authentication."
    )


def get_or_create_ytmusic_playlist(ytm: YTMusic, playlist_name: str) -> str:
    """
    Get existing playlist ID or create a new playlist.
    
    Returns:
        Playlist ID
    """
    # Try to find existing playlist
    try:
        playlists = ytm.get_library_playlists(limit=100)
        if playlists:
            for pl in playlists:
                if pl and pl.get("title", "").lower() == playlist_name.lower():
                    return pl["playlistId"]
    except Exception as e:
        log(f"Warning: Could not list playlists: {e}")
    
    # Create new playlist
    privacy = "PRIVATE" if config.YTMUSIC_PLAYLIST_PRIVATE else "PUBLIC"
    playlist_id = ytm.create_playlist(
        title=playlist_name,
        description="Synced from Spotify",
        privacy_status=privacy
    )
    log(f"Created new YouTube Music playlist: {playlist_name}")
    return playlist_id


def get_ytmusic_playlist_tracks(ytm: YTMusic, playlist_id: str) -> tuple[set[str], set[str], list[dict]]:
    """
    Get all tracks from a YouTube Music playlist.
    
    Returns:
        Tuple of (video_ids set, normalized_names set, processed_tracks list) for deduplication
    """
    video_ids = set()
    track_names = set()
    processed_tracks = []
    
    try:
        # Use a high limit to ensure we get all tracks (limit=None can sometimes truncate at 200)
        playlist = ytm.get_playlist(playlist_id, limit=10000)
        
        # Check for truncation (API may not return all tracks)
        total_count = playlist.get("trackCount", 0)
        actual_count = len(playlist.get("tracks", []))
        if total_count > actual_count:
            log(f"  [!] Warning: YT playlist has {total_count} tracks but API returned {actual_count}")
        
        for track in playlist.get("tracks", []):
            if track:
                # Get video ID for exact matching
                vid = track.get("videoId")
                if vid:
                    video_ids.add(vid)
                
                # Also get track name for fuzzy matching
                title = track.get("title", "")
                if title:
                    artists = track.get("artists", [])
                    artist_name = (artists[0].get("name") if artists and artists[0] else None) or "Unknown"
                    
                    # Pre-calculate normalized key for instant matching
                    key = normalize_track_key(title, artist_name)
                    track_names.add(key)
                    
                    # Pre-clean for fuzzy matching (saves time in the loop)
                    processed_tracks.append({
                        "title": title.lower(),
                        "artist": artist_name.lower(),
                        "clean_title": clean_text(title),
                        "clean_artist": clean_text(artist_name),
                        "videoId": vid
                    })
    except Exception as e:
        log(f"Warning: Could not fetch YT Music playlist tracks: {e}")
    
    return video_ids, track_names, processed_tracks


def simple_track_match(spotify_name: str, spotify_artist: str, yt_tracks: list[dict]) -> bool:
    """
    Fuzzy match to find similar songs.
    Returns True if a match is found with target similarity.
    """
    clean_spotify = clean_text(spotify_name)
    clean_spotify_artist = clean_text(spotify_artist)
    
    for yt in yt_tracks:
        clean_yt = yt["clean_title"]
        clean_yt_artist = yt["clean_artist"]
        
        if HAS_RAPIDFUZZ:
            # RapidFuzz is 10-100x faster than difflib
            name_ratio = fuzz.ratio(clean_spotify, clean_yt) / 100.0
            artist_ratio = fuzz.ratio(clean_spotify_artist, clean_yt_artist) / 100.0
        else:
            name_ratio = SequenceMatcher(None, clean_spotify, clean_yt).ratio()
            artist_ratio = SequenceMatcher(None, clean_spotify_artist, clean_yt_artist).ratio()
        
        # Match if: name >= 70% similar AND artist >= 60% similar
        # OR name >= 85% similar (for cases where artist name differs)
        if (name_ratio >= 0.7 and artist_ratio >= 0.6) or name_ratio >= 0.85:
            return True
    
    return False

# Pre-compiled regex for speed
RE_PARENS = re.compile(r'\([^)]*\)')
RE_BRACKETS = re.compile(r'\[[^\]]*\]')
RE_PUNCT = re.compile(r'[^\w\s]')
RE_SPACES = re.compile(r'\s+')

def clean_text(text: str) -> str:
    """Clean text for comparison (optimized)."""
    if not text:
        return ""
    text = text.lower().strip()
    # Remove parenthetical content
    text = RE_PARENS.sub('', text)
    text = RE_BRACKETS.sub('', text)
    # Remove punctuation
    text = RE_PUNCT.sub('', text)
    # Collapse spaces
    text = RE_SPACES.sub(' ', text).strip()
    return text


def search_ytmusic_song(ytm: YTMusic, track_name: str, artist_name: str) -> Optional[str]:
    """
    Search for a song on YouTube Music.
    
    Returns:
        Video ID if found, None otherwise
    """
    query = f"{track_name} {artist_name}"
    
    try:
        results = ytm.search(query, filter="songs", limit=config.MAX_SEARCH_RESULTS)
        
        if results:
            # Return the first result's video ID
            return results[0].get("videoId")
    except Exception as e:
        log(f"Search error for '{query}': {e}", also_print=False)
    
    return None


# OAuth fallback removed - browser auth now supports adding songs!


def test_ytmusic_auth():
    """Test YouTube Music authentication and print playlist info."""
    try:
        ytm = get_ytmusic_client()
        playlists = ytm.get_library_playlists(limit=10)
        
        print("✅ YouTube Music connected!")
        print("\nYour YouTube Music playlists:")
        for i, pl in enumerate(playlists, 1):
            print(f"  {i}. {pl['title']} (ID: {pl['playlistId']})")
        
        return True
    except FileNotFoundError as e:
        print(f"❌ {e}")
        return False
    except Exception as e:
        print(f"❌ YouTube Music auth failed: {e}")
        return False


# =============================================================================
# SYNC LOGIC
# =============================================================================

# Common song suffixes
STR_SUFFIXES = [
    ' - remaster', ' - remastered', ' remastered', ' - single', 
    ' - radio edit', ' - live', ' - acoustic', ' - remix',
    ' - original', ' - version', ' - edit', ' - mix',
    ' - from', ' - feat', ' feat.', ' ft.', ' featuring'
]

# Pre-compile regex for common suffixes for speed
COMMON_SUFFIXES_RE = re.compile(
    r'(?:' + '|'.join(re.escape(s) for s in STR_SUFFIXES) + r')\b',
    re.IGNORECASE
)

def normalize_track_key(name: str, artist: str) -> str:
    """Create a normalized key for track comparison (optimized)."""
    
    def clean(text):
        if not text: return ""
        text = text.lower()
        # 1. Remove anything in brackets/parentheses (e.g. "[Official Video]", "(Live)")
        text = re.sub(r'[\(\[][^\]\)]*[\)\]]', '', text)
        # 2. Strip soundtrack references like "From 'Movie'" or "- From Movie"
        text = re.sub(r'[-\s]*\bfrom\b\s+["\'].*?["\']', '', text)
        text = re.sub(r'[-\s]*\bfrom\b\s+.*$', '', text) # Catch "- from Movie Name" at end
        # 3. Remove common suffixes like " - Single", " - Remastered"
        text = re.sub(COMMON_SUFFIXES_RE, '', text)
        # 4. Remove common noise like "official video", "lyrics", etc.
        text = re.sub(r'\b(official|video|lyrics|audio|full|hd|4k)\b', '', text)
        # 5. Remove punctuation
        text = RE_PUNCT.sub(' ', text) 
        # 6. Collapse spaces
        text = RE_SPACES.sub(' ', text).strip()
        return text
    
    clean_name = clean(name)
    clean_artist = clean(artist)
    
    # YouTube specific: if title is "Artist - Song" or "Song - Artist", 
    # the clean_name might still contain the artist. Strip it.
    if clean_artist and clean_artist in clean_name:
        # Remove artist name from title if it's a distinct part
        clean_name = clean_name.replace(clean_artist, "").strip()
        # Collapse any double spaces created by removal
        clean_name = RE_SPACES.sub(' ', clean_name).strip()
    
    # Special case: if stripping the artist left us with nothing, 
    # fall back to the original clean name
    if not clean_name:
        clean_name = clean(name)
        
    return f"{clean_name}|{clean_artist}"


def sync_playlists(dry_run: bool = False):
    """
    Main sync function. Syncs songs from Spotify to YouTube Music.
    
    Args:
        dry_run: If True, only show what would be synced without actually syncing
    """
    from datetime import datetime
    sync_start_time = datetime.now()
    
    log("=" * 60)
    log(f"SYNC STARTED {'(DRY RUN)' if dry_run else ''}")
    log("=" * 60)
    
    # Check if we have valid playlists to sync
    has_mapping = hasattr(config, "PLAYLIST_MAPPING") and config.PLAYLIST_MAPPING
    # Use getattr for safety with SPOTIFY_PLAYLIST_IDS as well
    spotify_playlist_ids = getattr(config, "SPOTIFY_PLAYLIST_IDS", [])
    has_legacy = spotify_playlist_ids and len(spotify_playlist_ids) > 0 and "YOUR_" not in spotify_playlist_ids[0]

    if not has_mapping and not has_legacy:
        log("❌ Error: Please add at least one Spotify playlist ID in config.py (either in PLAYLIST_MAPPING or SPOTIFY_PLAYLIST_IDS)")
        return
    
    # Connect to both services
    try:
        log("Initializing Spotify Scraper...")
        sp = get_spotify_client()
        log("✅ Spotify Scraper ready")
    except Exception as e:
        log(f"❌ Spotify initialization failed: {e}")
        return
    
    try:
        log("Connecting to YouTube Music...")
        ytm = get_ytmusic_client()
        log("✅ YouTube Music connected")
    except Exception as e:
        log(f"❌ YouTube Music connection failed: {e}")
        return
    
    # Stats
    total_spotify_tracks = 0
    already_synced = 0
    newly_added = 0
    not_found = 0
    errors = 0
    
    # Load sync cache (tracks what's already been synced)
    sync_cache = load_sync_cache()
    
    # Get playlists to sync
    playlists_to_sync = []
    if hasattr(config, 'PLAYLIST_MAPPING') and config.PLAYLIST_MAPPING:
        # Use the new mapping format
        for spotify_id, yt_id in config.PLAYLIST_MAPPING.items():
            playlists_to_sync.append((spotify_id, yt_id))
    else:
        # Fall back to old format (all Spotify playlists -> one YT playlist)
        yt_id = config.YTMUSIC_PLAYLIST_ID if hasattr(config, 'YTMUSIC_PLAYLIST_ID') and config.YTMUSIC_PLAYLIST_ID else None
        for spotify_id in config.SPOTIFY_PLAYLIST_IDS:
            playlists_to_sync.append((spotify_id, yt_id))
    
    # Validate mappings - check if YT playlists still exist
    log("Validating playlist mappings...")
    
    # First, test YTMusic authentication
    try:
        from utils.ytmusic_validator import check_ytmusic_auth
        auth_valid, auth_msg, error_type = check_ytmusic_auth()
        
        if not auth_valid and error_type in ('expired', 'missing'):
            log("=" * 60)
            if error_type == 'expired':
                log("*** WARNING: YOUTUBE MUSIC AUTHENTICATION HAS EXPIRED! ***")
            else:
                log("*** WARNING: YOUTUBE MUSIC HEADERS NOT CONFIGURED! ***")
            log("=" * 60)
            log(f"    {auth_msg}")
            log("    Skipping playlist validation to prevent incorrect mapping removal.")
            log("    Please re-run: python setup_browser_auth.py")
            log("=" * 60)
            log("")
            # Don't validate playlists if auth is broken - can't tell if playlists exist or not
            playlists_to_sync = [(sp, yt) for sp, yt in playlists_to_sync]  # Keep all
        else:
            # Auth is valid, proceed with validation
            from utils.ytmusic_validator import validate_all_playlists
            
            mapping = {sp_id: yt_id for sp_id, yt_id in playlists_to_sync}
            validation_results = validate_all_playlists(ytm, mapping)
            
            valid_playlists = validation_results['valid']
            broken_mappings = validation_results['missing']
            auth_errors = validation_results['auth_errors']
            unknown_errors = validation_results['unknown_errors']
            
            # Report results
            if broken_mappings:
                log(f"[!] Found {len(broken_mappings)} broken mapping(s) - YouTube playlists no longer exist:")
                for sp_id, yt_id in broken_mappings:
                    log(f"    - Spotify: {sp_id[:30]}... -> YT: {yt_id} (DELETED)")
                log("    Use 'Validate mappings' in app.py to review and remove these.")
                log("")
            
            if auth_errors:
                log(f"[!] Found {len(auth_errors)} mapping(s) with authentication errors:")
                for sp_id, yt_id in auth_errors:
                    log(f"    - Spotify: {sp_id[:30]}... -> YT: {yt_id} (AUTH ERROR)")
                log("    These mappings are preserved - headers may be expired.")
                log("")
            
            if unknown_errors:
                log(f"[!] Found {len(unknown_errors)} mapping(s) with unknown errors:")
                for sp_id, yt_id, err_msg in unknown_errors:
                    log(f"    - Spotify: {sp_id[:30]}... -> YT: {yt_id}")
                    log(f"      Error: {err_msg}")
                log("")
            
            # Use only valid playlists + auth errors (preserve auth errors)
            # Exclude only genuinely broken playlists
            playlists_to_sync = valid_playlists + auth_errors
    except ImportError:
        # Fallback to old behavior if validator not available
        log("[!] Warning: ytmusic_validator not found, using legacy validation")
        valid_playlists = []
        for spotify_id, yt_id in playlists_to_sync:
            if not yt_id:
                valid_playlists.append((spotify_id, yt_id))
                continue
            try:
                ytm.get_playlist(yt_id, limit=1)
                valid_playlists.append((spotify_id, yt_id))
            except Exception:
                log(f"[!] Could not access playlist: {yt_id}")
        playlists_to_sync = valid_playlists
    
    if not playlists_to_sync:
        log("[!] No valid playlists to sync.")
        return
        
    log(f"[OK] {len(playlists_to_sync)} valid playlist(s) to sync")

    
    # Process each playlist pair
    for spotify_playlist_id, yt_playlist_id in playlists_to_sync:
        try:
            # Ensure we have a full URL
            if not spotify_playlist_id.startswith("http"):
                spotify_url = f"https://open.spotify.com/playlist/{spotify_playlist_id}"
            else:
                spotify_url = spotify_playlist_id
                
            # Get Spotify playlist info using scraper
            playlist_info = sp.get_playlist_info(spotify_url)
            if not playlist_info:
                log(f"  [!] Could not fetch playlist info for: {spotify_url}")
                continue
                
            playlist_name = playlist_info.get("name", "Unknown Playlist")
            log(f"\n📋 Processing: {playlist_name}")
            
            # Determine target YT playlist
            if not yt_playlist_id:
                log(f"  ⚠️ No YouTube Music playlist mapped for this playlist. Skipping.")
                continue
            
            log(f"  → Target YT playlist: {yt_playlist_id}")
            
            # --- OPTIMIZATION: PARALLEL DATA FETCHING ---
            log(f"  [i] Fetching music data from both platforms...")
            with ThreadPoolExecutor(max_workers=2) as executor:
                # Start both fetch tasks concurrently
                future_yt = executor.submit(get_ytmusic_playlist_tracks, ytm, yt_playlist_id)
                future_sp = executor.submit(get_spotify_playlist_tracks, sp, spotify_playlist_id)
                
                # Wait for results
                existing_video_ids, existing_track_names, yt_raw_tracks = future_yt.result()
                spotify_tracks = future_sp.result()
            
            # Get Spotify tracks that have already been synced (from local cache)
            already_synced_ids = get_synced_tracks(sync_cache, spotify_playlist_id, yt_playlist_id)
            
            cache_hits = len([t for t in spotify_tracks if t["id"] in already_synced_ids])
            log(f"  Found {len(spotify_tracks)} Spotify tracks ({cache_hits} in sync cache, {len(existing_video_ids)} in YT playlist)")
            total_spotify_tracks += len(spotify_tracks)
            
            # --- OPTIMIZATION: PARALLEL MATCHING & SEARCH ---
            songs_to_add = []
            tracks_to_cache = []
            
            def process_track(track):
                spotify_track_id = track["id"]
                track_name = track["name"]
                track_artist = track["artist"]
                track_key = normalize_track_key(track_name, track_artist)
                
                # Fast path: Cache check
                if spotify_track_id in already_synced_ids:
                    return "cache", spotify_track_id, None
                
                # Fast path: Dictionary lookup (Exact/Normalized match)
                if track_key in existing_track_names:
                    return "synced", spotify_track_id, None
                
                # Fuzzy path: More expensive
                if simple_track_match(track_name, track_artist, yt_raw_tracks):
                    return "synced", spotify_track_id, None
                
                # Search path: Most expensive (Network I/O)
                video_id = search_ytmusic_song(ytm, track_name, track_artist)
                if video_id:
                    # Double check video ID in existing set
                    if video_id in existing_video_ids:
                        return "synced", spotify_track_id, None
                    return "new", spotify_track_id, (video_id, track_name, track_artist, track_key)
                
                return "not_found", spotify_track_id, None

            log(f"  [i] Analyzing tracks for sync...")
            # Use a smaller worker pool for search to avoid YT rate limits
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(process_track, t) for t in spotify_tracks]
                
                for future in as_completed(futures):
                    result_type, track_id, data = future.result()
                    
                    if result_type == "cache":
                        already_synced += 1
                    elif result_type == "synced":
                        already_synced += 1
                        mark_as_synced(sync_cache, spotify_playlist_id, yt_playlist_id, track_id)
                    elif result_type == "new":
                        video_id, name, artist, key = data
                        if dry_run:
                            log(f"  Would add: {name} - {artist}")
                            newly_added += 1
                        else:
                            # Prevent adding same song twice if multiple threads found it
                            if video_id not in existing_video_ids:
                                songs_to_add.append(video_id)
                                tracks_to_cache.append(track_id)
                                existing_video_ids.add(video_id)
                                log(f"  + Found: {name} - {artist}")
                                newly_added += 1
                            else:
                                already_synced += 1
                        existing_track_names.add(key)
                    elif result_type == "not_found":
                        not_found += 1
            
            # Add songs in batch (more efficient)
            if songs_to_add and not dry_run:
                try:
                    ytm.add_playlist_items(yt_playlist_id, songs_to_add)
                    log(f"✅ Added {len(songs_to_add)} songs to YouTube Music")
                    # Mark all as synced in cache
                    for track_id in tracks_to_cache:
                        mark_as_synced(sync_cache, spotify_playlist_id, yt_playlist_id, track_id)
                except Exception as e:
                    log(f"Error adding songs: {e}")
                    errors += len(songs_to_add)
                    newly_added -= len(songs_to_add)
                    
        except Exception as e:
            import traceback
            log(f"[ERROR] Error processing playlist: {e}")
            log(f"[DEBUG] Full traceback:\n{traceback.format_exc()}")
            errors += 1
    
    # Save sync cache
    if not dry_run:
        save_sync_cache(sync_cache)
    
    # Calculate sync duration
    from datetime import datetime
    sync_end_time = datetime.now()
    duration_seconds = (sync_end_time - sync_start_time).total_seconds()
    duration_str = f"{int(duration_seconds // 60)}m {int(duration_seconds % 60)}s" if duration_seconds >= 60 else f"{int(duration_seconds)}s"
    
    # Summary with enhanced formatting
    log("\n" + "=" * 60)
    log("✓ SYNC COMPLETE!" if not dry_run else "DRY RUN COMPLETE!")
    log("=" * 60)
    log(f"Playlists processed: {len(playlists_to_sync)}")
    log(f"Total tracks found:  {total_spotify_tracks}")
    log("")
    log(f"✓ Already synced:    {already_synced}")
    log(f"+ Newly added:       {newly_added}")
    if not_found > 0:
        log(f"⚠ Not found on YT:  {not_found}")
    if errors > 0:
        log(f"✗ Errors:            {errors}")
    log("")
    log(f"Time taken: {duration_str}")
    log("=" * 60)
    
    # Show success tip
    if not dry_run and newly_added > 0:
        log("💡 Tip: Check your YouTube Music playlists to see the new songs!")
    elif dry_run and newly_added > 0:
        log(f"💡 Tip: Run without --dry-run to actually sync {newly_added} new songs!")
    elif newly_added == 0 and not_found == 0:
        log("✓ All your music is already synced!")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Sync Spotify playlists to YouTube Music"
    )
    parser.add_argument(
        "--dry-run", "-d",
        action="store_true",
        help="Preview sync without actually adding songs"
    )
    parser.add_argument(
        "--test-spotify",
        action="store_true",
        help="Test Spotify authentication"
    )
    parser.add_argument(
        "--test-ytmusic",
        action="store_true",
        help="Test YouTube Music authentication"
    )
    
    args = parser.parse_args()
    
    if args.test_spotify:
        test_spotify_auth()
    elif args.test_ytmusic:
        test_ytmusic_auth()
    else:
        dry_run = args.dry_run or config.DRY_RUN
        sync_playlists(dry_run=dry_run)


if __name__ == "__main__":
    main()
