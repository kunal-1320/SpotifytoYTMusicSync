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
from datetime import datetime
from typing import Optional

# Third-party imports
try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
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

def get_spotify_client() -> spotipy.Spotify:
    """Create and return an authenticated Spotify client."""
    auth_manager = SpotifyOAuth(
        client_id=config.SPOTIFY_CLIENT_ID,
        client_secret=config.SPOTIFY_CLIENT_SECRET,
        redirect_uri=config.SPOTIFY_REDIRECT_URI,
        scope="playlist-read-private playlist-read-collaborative",
        cache_path=".spotify_cache"
    )
    return spotipy.Spotify(auth_manager=auth_manager)


def get_spotify_playlist_tracks(sp: spotipy.Spotify, playlist_id: str) -> list[dict]:
    """
    Get all tracks from a Spotify playlist.
    
    Returns:
        List of dicts with 'id', 'name', 'artist', 'album' keys
    """
    tracks = []
    results = sp.playlist_tracks(playlist_id)
    
    while results:
        for item in results["items"]:
            track = item.get("track")
            if track and track.get("name") and track.get("id"):
                # Get primary artist name
                artists = track.get("artists", [])
                artist_name = artists[0]["name"] if artists else "Unknown"
                
                tracks.append({
                    "id": track["id"],  # Spotify track ID for deduplication
                    "name": track["name"],
                    "artist": artist_name,
                    "album": track.get("album", {}).get("name", ""),
                })
        
        # Handle pagination
        if results["next"]:
            results = sp.next(results)
        else:
            break
    
    return tracks


def test_spotify_auth():
    """Test Spotify authentication and print user info."""
    try:
        sp = get_spotify_client()
        user = sp.current_user()
        print(f"✅ Spotify connected as: {user['display_name']} ({user['id']})")
        
        # List playlists
        playlists = sp.current_user_playlists(limit=10)
        print("\nYour Spotify playlists:")
        for i, pl in enumerate(playlists["items"], 1):
            print(f"  {i}. {pl['name']} (ID: {pl['id']})")
        
        return True
    except Exception as e:
        print(f"❌ Spotify auth failed: {e}")
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
        Tuple of (video_ids set, normalized_names set, raw_tracks list) for deduplication
    """
    video_ids = set()
    track_names = set()
    raw_tracks = []
    
    try:
        playlist = ytm.get_playlist(playlist_id, limit=None)
        
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
                if track.get("title"):
                    artists = track.get("artists", [])
                    artist_name = artists[0]["name"] if artists else "Unknown"
                    key = normalize_track_key(track["title"], artist_name)
                    track_names.add(key)
                    
                    # Store raw data for fuzzy matching
                    raw_tracks.append({
                        "title": track["title"].lower(),
                        "artist": artist_name.lower(),
                        "videoId": vid
                    })
    except Exception as e:
        log(f"Warning: Could not fetch YT Music playlist tracks: {e}")
    
    return video_ids, track_names, raw_tracks


def simple_track_match(spotify_name: str, spotify_artist: str, yt_tracks: list[dict]) -> bool:
    """
    Fuzzy match using SequenceMatcher to find similar songs.
    Returns True if a match is found with >= 70% similarity.
    """
    from difflib import SequenceMatcher
    import re
    
    def clean_text(text: str) -> str:
        """Clean text for comparison."""
        text = text.lower().strip()
        # Remove parenthetical content
        text = re.sub(r'\([^)]*\)', '', text)
        text = re.sub(r'\[[^\]]*\]', '', text)
        # Remove punctuation
        text = re.sub(r'[^\w\s]', '', text)
        # Collapse spaces
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    clean_spotify = clean_text(spotify_name)
    clean_spotify_artist = clean_text(spotify_artist)
    
    for yt in yt_tracks:
        clean_yt = clean_text(yt["title"])
        clean_yt_artist = clean_text(yt.get("artist", ""))
        
        # Compare song names
        name_ratio = SequenceMatcher(None, clean_spotify, clean_yt).ratio()
        
        # Compare artists
        artist_ratio = SequenceMatcher(None, clean_spotify_artist, clean_yt_artist).ratio()
        
        # Match if: name >= 70% similar AND artist >= 60% similar
        # OR name >= 85% similar (for cases where artist name differs)
        if (name_ratio >= 0.7 and artist_ratio >= 0.6) or name_ratio >= 0.85:
            return True
    
    return False


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

def normalize_track_key(name: str, artist: str) -> str:
    """Create a normalized key for track comparison (aggressive normalization)."""
    import re
    
    def clean(text: str) -> str:
        text = text.lower().strip()
        
        # Remove anything in parentheses or brackets
        text = re.sub(r'\([^)]*\)', '', text)
        text = re.sub(r'\[[^\]]*\]', '', text)
        
        # Remove common suffixes/prefixes
        suffixes = [
            ' - remaster', ' - remastered', ' remastered', ' - single', 
            ' - radio edit', ' - live', ' - acoustic', ' - remix',
            ' - original', ' - version', ' - edit', ' - mix',
            ' - from', ' - feat', ' feat.', ' ft.', ' featuring'
        ]
        for suffix in suffixes:
            if suffix in text:
                text = text.split(suffix)[0]
        
        # Remove punctuation except spaces
        text = re.sub(r'[^\w\s]', '', text)
        
        # Collapse multiple spaces
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    clean_name = clean(name)
    clean_artist = clean(artist)
    
    return f"{clean_name}|{clean_artist}"


def sync_playlists(dry_run: bool = False):
    """
    Main sync function. Syncs songs from Spotify to YouTube Music.
    
    Args:
        dry_run: If True, only show what would be synced without actually syncing
    """
    log("=" * 60)
    log(f"SYNC STARTED {'(DRY RUN)' if dry_run else ''}")
    log("=" * 60)
    
    # Validate config
    if "YOUR_" in config.SPOTIFY_CLIENT_ID or "YOUR_" in config.SPOTIFY_CLIENT_SECRET:
        log("❌ Error: Please configure your Spotify credentials in config.py")
        return
    
    # Check if we have valid playlists to sync
    has_mapping = hasattr(config, "PLAYLIST_MAPPING") and config.PLAYLIST_MAPPING
    has_legacy = config.SPOTIFY_PLAYLIST_IDS and "YOUR_" not in config.SPOTIFY_PLAYLIST_IDS[0]

    if not has_mapping and not has_legacy:
        log("❌ Error: Please add at least one Spotify playlist ID in config.py (either in PLAYLIST_MAPPING or SPOTIFY_PLAYLIST_IDS)")
        return
    
    # Connect to both services
    try:
        log("Connecting to Spotify...")
        sp = get_spotify_client()
        user = sp.current_user()
        log(f"✅ Spotify: {user['display_name']}")
    except Exception as e:
        log(f"❌ Spotify connection failed: {e}")
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
    valid_playlists = []
    broken_mappings = []
    
    for spotify_id, yt_id in playlists_to_sync:
        if not yt_id:
            valid_playlists.append((spotify_id, yt_id))
            continue
        try:
            # Try to access the playlist
            ytm.get_playlist(yt_id, limit=1)
            valid_playlists.append((spotify_id, yt_id))
        except Exception:
            broken_mappings.append((spotify_id, yt_id))
    
    if broken_mappings:
        log(f"[!] Found {len(broken_mappings)} broken mapping(s) - YouTube playlists no longer exist:")
        for sp_id, yt_id in broken_mappings:
            log(f"    - Spotify: {sp_id[:30]}... -> YT: {yt_id} (REMOVED)")
        
        # Auto-remove broken mappings from config
        try:
            from config_updater import remove_playlist_mappings
            sp_ids_to_remove = [sp_id for sp_id, _ in broken_mappings]
            removed = remove_playlist_mappings(sp_ids_to_remove)
            log(f"[OK] Removed {removed} broken mapping(s) from config.py")
        except Exception as e:
            log(f"[!] Could not auto-remove from config: {e}")
        log("")
    
    playlists_to_sync = valid_playlists
    
    if not playlists_to_sync:
        log("[!] No valid playlists to sync.")
        return
        
    log(f"[OK] {len(playlists_to_sync)} valid playlist(s) to sync")

    
    # Process each playlist pair
    for spotify_playlist_id, yt_playlist_id in playlists_to_sync:
        try:
            # Get Spotify playlist info
            playlist_info = sp.playlist(spotify_playlist_id, fields="name")
            playlist_name = playlist_info["name"]
            log(f"\n📋 Processing: {playlist_name}")
            
            # Determine target YT playlist
            if not yt_playlist_id:
                log(f"  ⚠️ No YouTube Music playlist mapped for this playlist. Skipping.")
                continue
            
            log(f"  → Target YT playlist: {yt_playlist_id}")
            
            # Get existing tracks in this YT Music playlist
            existing_video_ids, existing_track_names, yt_raw_tracks = get_ytmusic_playlist_tracks(ytm, yt_playlist_id)
            
            # Get Spotify tracks that have already been synced (from local cache)
            already_synced_ids = get_synced_tracks(sync_cache, spotify_playlist_id, yt_playlist_id)
            
            # Get Spotify tracks
            spotify_tracks = get_spotify_playlist_tracks(sp, spotify_playlist_id)
            cache_hits = len([t for t in spotify_tracks if t["id"] in already_synced_ids])
            log(f"  Found {len(spotify_tracks)} Spotify tracks ({cache_hits} in sync cache, {len(existing_video_ids)} in YT playlist)")
            total_spotify_tracks += len(spotify_tracks)
            
            # Sync each track
            songs_to_add = []
            tracks_to_cache = []  # Track IDs to mark as synced after successful add
            
            for track in spotify_tracks:
                spotify_track_id = track["id"]
                track_key = normalize_track_key(track["name"], track["artist"])
                
                # Check 1: Already synced according to our cache?
                if spotify_track_id in already_synced_ids:
                    already_synced += 1
                    continue
                
                # Check 2: Already in YT Music playlist (by normalized name)?
                if track_key in existing_track_names:
                    already_synced += 1
                    mark_as_synced(sync_cache, spotify_playlist_id, yt_playlist_id, spotify_track_id)
                    continue
                
                # Check 3: Fuzzy match against YT tracks (keyword-based)
                if simple_track_match(track["name"], track["artist"], yt_raw_tracks):
                    already_synced += 1
                    mark_as_synced(sync_cache, spotify_playlist_id, yt_playlist_id, spotify_track_id)
                    continue
                
                # Search for song on YT Music
                video_id = search_ytmusic_song(ytm, track["name"], track["artist"])
                
                if video_id:
                    # Check 4: is this video ID already in the playlist?
                    if video_id in existing_video_ids:
                        already_synced += 1
                        mark_as_synced(sync_cache, spotify_playlist_id, yt_playlist_id, spotify_track_id)
                        continue
                    
                    if dry_run:
                        log(f"  Would add: {track['name']} - {track['artist']}")
                        newly_added += 1
                    else:
                        songs_to_add.append(video_id)
                        tracks_to_cache.append(spotify_track_id)
                        existing_video_ids.add(video_id)  # Prevent duplicates in this run
                        log(f"  + Found: {track['name']} - {track['artist']}")
                        newly_added += 1
                    existing_track_names.add(track_key)  # Prevent duplicates
                else:
                    log(f"  [!] Not found: {track['name']} - {track['artist']}")
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
            log(f"[ERROR] Error processing playlist: {e}")
            errors += 1
    
    # Save sync cache
    if not dry_run:
        save_sync_cache(sync_cache)
    
    # Summary
    log("\n" + "=" * 60)
    log("SYNC SUMMARY" + (" (DRY RUN)" if dry_run else ""))
    log("=" * 60)
    log(f"Total Spotify tracks: {total_spotify_tracks}")
    log(f"Already synced:       {already_synced}")
    log(f"Newly added:          {newly_added}")
    log(f"Not found on YT:      {not_found}")
    log(f"Errors:               {errors}")
    log("=" * 60)


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
