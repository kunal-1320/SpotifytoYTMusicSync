#!/usr/bin/env python3
"""
Spotify to YouTube Music Sync - Interactive Menu
=================================================
Run this file for easy setup and sync operations.
"""

import os
import sys

# Add current directory to path for local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import shared utilities
from utils.ui import (
    clear_screen, print_header, print_menu, print_submenu,
    get_choice, pause, safe_print, print_status,
    print_success, print_error, print_warning, print_info,
    print_divider, print_box, Colors
)
from utils.clients import (
    get_spotify_client, get_ytmusic_client,
    check_spotify_configured, check_ytmusic_configured,
    test_spotify_connection, test_ytmusic_connection
)


# =============================================================================
# CONFIG HELPERS
# =============================================================================

def get_playlist_mapping():
    """Get current playlist mappings from config."""
    try:
        import importlib
        import config
        importlib.reload(config)
        if hasattr(config, 'PLAYLIST_MAPPING'):
            return config.PLAYLIST_MAPPING
    except Exception:
        pass
    return {}


def ensure_config_exists():
    """Ensure config.py exists, create from example if needed."""
    import shutil
    if not os.path.exists("config.py"):
        if os.path.exists("config.example.py"):
            shutil.copy("config.example.py", "config.py")
            print_info("Created config.py from config.example.py")
            return True
        else:
            print_error("config.example.py not found!")
            return False
    return os.path.exists("config.py")


# =============================================================================
# SETUP FUNCTIONS
# =============================================================================

def setup_spotify():
    """Spotify setup is no longer required."""
    print_header("SPOTIFY SETUP")
    print_success("Spotify Scraper Mode is ACTIVE.")
    print()
    print("This tool now uses web scraping for Spotify data.")
    print("No API keys, Client IDs, or Developer Apps are required!")
    print()
    print_info("You can directly map public playlists by their URLs.")
    pause()
    return True


def setup_ytmusic():
    """Interactive YouTube Music setup."""
    print_header("YOUTUBE MUSIC SETUP", "Simple 2-minute browser authentication")
    
    print_box([
        "OPTION 1 - Easiest (Recommended):",
        "  Run: python setup_browser_auth.py",
        "",
        "OPTION 2 - Quick (if you know what you're doing):",
        "  1. Go to https://music.youtube.com (signed in)",
        "  2. Press F12 > Network tab > filter 'browse'",
        "  3. Click 'Library' in YouTube Music",
        "  4. Find a POST request to 'browse?...'",
        "  5. Copy headers: Chrome (Copy as cURL bash) | Firefox (Copy Request Headers)"
    ])
    print()
    
    choice = input("Continue with quick setup here? (y/n): ").strip().lower()
    
    if choice != 'y':
        print_info("Run: python setup_browser_auth.py")
        pause()
        return False
    
    
    # Use shared input helper
    from utils.ui import get_multiline_input
    headers_text = get_multiline_input("Paste your request headers below (press Enter twice when done):")
    
    if not headers_text or len(headers_text) < 100:
        print_error("Headers too short or empty. Cancelled.")
        pause()
        return False
    
    try:
        from utils.auth_helper import parse_headers, validate_headers, save_browser_auth
        
        headers = parse_headers(headers_text)
        is_valid, missing = validate_headers(headers)

        if not is_valid:
            print_error("Missing required headers!")
            possible_issues = []
            if 'x-goog-visitor-id' in missing:
                possible_issues.append("Missing x-goog-visitor-id (Required for playlists)")
            if 'cookie' in missing:
                possible_issues.append("Missing Cookie header")
            
            for issue in possible_issues:
                print_warning(f"  • {issue}")
            
            print_info("Please ensure you copied the FULL cURL command or ALL headers.")
            pause()
            return False

        # Save to file
        save_browser_auth(headers, 'browser_auth.json')

        print_success("YouTube Music browser auth saved!")
        
        # Test connection
        print_info("Testing YouTube Music connection...")
        success, msg, error_type = test_ytmusic_connection()
        if success:
            print_success(msg)
        else:
            print_warning(f"Connection test: {msg}")
        
        pause()
        return True
    except Exception as e:
        print_error(str(e))
        print_info("Try running: python setup_browser_auth.py")
        pause()
        return False


# =============================================================================
# PLAYLIST MANAGEMENT
# =============================================================================

def manage_playlists():
    """Playlist management submenu."""
    while True:
        print_header("PLAYLIST MANAGEMENT", "Manage your playlist mappings")
        
        mapping = get_playlist_mapping()
        
        if mapping:
            print(f"Current mappings ({len(mapping)} total):")
            print_divider()
            for i, (sp_id, yt_id) in enumerate(list(mapping.items())[:5], 1):
                safe_print(f"  {i}. {Colors.DIM}Spotify:{Colors.RESET} {sp_id[:30]}...")
                safe_print(f"     {Colors.DIM}YTMusic:{Colors.RESET} {yt_id}")
            if len(mapping) > 5:
                print(f"  ... and {len(mapping) - 5} more")
            print()
        else:
            print_warning("No playlists configured yet.")
            print()
        
        print_menu([
            "Add new playlist mapping",
            "Remove a playlist mapping",
            "Validate mappings",
            "Check YT Music headers status",
            "View YouTube Music playlists",
            "Create YouTube Music playlist",
        ])
        
        choice = get_choice(6)
        
        if choice == 0:
            break
        elif choice == 1:
            add_playlist_mapping()
        elif choice == 2:
            remove_playlist_mapping()
        elif choice == 3:
            validate_mappings()
        elif choice == 4:
            check_ytmusic_headers_status()
        elif choice == 5:
            view_ytmusic_playlists()
        elif choice == 6:
            create_ytmusic_playlist_interactive()


def add_playlist_mapping():
    """Add a new playlist mapping by URL."""
    print_header("ADD PLAYLIST MAPPING")
    
    print_info("No API keys needed! Just paste the Spotify playlist URL.")
    print()
    
    spotify_url = input("Enter Spotify Playlist URL (or ID): ").strip()
    if not spotify_url:
        print_warning("Cancelled.")
        pause()
        return
        
    # Standardize ID to URL if only ID provided
    if not spotify_url.startswith("http") and len(spotify_url) > 10:
        spotify_url = f"https://open.spotify.com/playlist/{spotify_url}"
    
    # Check if we can fetch this playlist
    print_info("Verifying Spotify playlist...")
    try:
        sp = get_spotify_client()
        playlist_info = sp.get_playlist_info(spotify_url)
        if not playlist_info:
            print_error("Could not fetch playlist info. Is it public?")
            pause()
            return
        spotify_name = playlist_info.get('name', 'Unknown')
        print_success(f"Found Spotify playlist: {spotify_name}")
    except Exception as e:
        print_error(f"Error fetching Spotify playlist: {e}")
        pause()
        return
        
    # Get YT Music Playlists
    print_info("Fetching your YouTube Music playlists...")
    try:
        ytm = get_ytmusic_client()
        yt_playlists = ytm.get_library_playlists(limit=50)
    except Exception as e:
        print_error(f"Failed to fetch YouTube Music playlists: {e}")
        pause()
        return

    print()
    print_success("Select Target YouTube Music Playlist:")
    print_divider()
    for i, pl in enumerate(yt_playlists, 1):
        safe_print(f"  [{i}] {pl.get('title', 'Unknown')}")
    print("  [0] Cancel")
    print()
    
    try:
        yt_choice = int(input(f"Select (1-{len(yt_playlists)}): ").strip())
        if yt_choice == 0: return
        selected_yt = yt_playlists[yt_choice - 1]
        ytmusic_id = selected_yt.get('playlistId')
        ytmusic_name = selected_yt.get('title', 'Unknown')
    except:
        print_error("Invalid selection!")
        pause()
        return
        
    # Save mapping
    try:
        from config_updater import append_playlist_mappings
        # We'll save the ID part as key, or full URL? 
        # config.py currently uses IDs like "2XgBQIJKjArcbF2Smfjxc2"
        # Let's extract ID if it's a URL
        spotify_id = spotify_url.split('/')[-1].split('?')[0]
        
        added = append_playlist_mappings({spotify_id: ytmusic_id})
        if added > 0:
            print_success(f"Mapped: {spotify_name} → {ytmusic_name}")
        else:
            print_error("Failed to update config.py")
    except Exception as e:
        print_error(f"Error: {e}")
    
    pause()




def remove_playlist_mapping():
    """Remove a playlist mapping."""
    mapping = get_playlist_mapping()
    if not mapping:
        print_warning("No mappings to remove.")
        pause()
        return
    
    print_header("REMOVE PLAYLIST MAPPING")
    print_info("Fetching playlist names...")
    print()
    
    # Fetch playlist names
    items = []
    try:
        from utils.clients import get_spotify_client
        sp = get_spotify_client()
        ytm = get_ytmusic_client()
        
        for sp_id, yt_id in mapping.items():
            # Get Spotify name via scraping
            try:
                # Standardize ID to URL
                sp_url = f"https://open.spotify.com/playlist/{sp_id}" if not sp_id.startswith("http") else sp_id
                sp_playlist = sp.get_playlist_info(sp_url)
                sp_name = sp_playlist.get('name', f"Playlist {sp_id[:8]}...")
            except:
                sp_name = f"[Error: {sp_id[:10]}...]"
            
            # Get YTMusic name
            try:
                yt_playlist = ytm.get_playlist(yt_id, limit=0)
                yt_name = yt_playlist.get('title', 'Unknown')
            except:
                yt_name = f"[Error: {yt_id[:10]}...]"
            
            items.append((sp_id, yt_id, sp_name, yt_name))
        
        # Display mappings with names
        print("Select mapping to remove:")
        print_divider()
        for i, (sp_id, yt_id, sp_name, yt_name) in enumerate(items, 1):
            safe_print(f"  {Colors.CYAN}[{i}]{Colors.RESET} {sp_name} → {yt_name}")
            print(f"      {Colors.DIM}{sp_id} → {yt_id}{Colors.RESET}")
        print("  [0] Cancel")
        print()
        
    except Exception as e:
        print_error(f"Error fetching names: {e}")
        print()
        items = [(sp_id, yt_id, sp_id[:30], yt_id[:30]) for sp_id, yt_id in mapping.items()]
        for i, (sp_id, _, _, _) in enumerate(items, 1):
            print(f"  [{i}] {sp_id[:40]}...")
        print("  [0] Cancel")
        print()
    
    choice = get_choice(len(items))
    if choice == 0:
        return
    
    sp_id_to_remove, _, sp_name, yt_name = items[choice - 1]
    
    try:
        with open("config.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        import re
        pattern = rf'\s*"{re.escape(sp_id_to_remove)}"\s*:\s*"[^"]*"\s*,?\s*\n?'
        content = re.sub(pattern, '\n', content)
        
        with open("config.py", "w", encoding="utf-8") as f:
            f.write(content)
        
        print_success(f"Removed: {sp_name}")
    except Exception as e:
        print_error(str(e))
    
    pause()


def check_ytmusic_headers_status():
    """Check if YouTube Music headers are still valid."""
    print_header("YOUTUBE MUSIC HEADERS STATUS", "Check authentication validity")
    
    if not check_ytmusic_configured():
        print_error("YouTube Music not configured!")
        print_info("Run: python setup_browser_auth.py")
        pause()
        return
    
    print_info("Testing YouTube Music authentication...")
    print()
    
    try:
        from utils.ytmusic_validator import check_ytmusic_auth
        is_valid, message, error_type = check_ytmusic_auth()
        
        print_divider()
        if is_valid:
            print_success("✅ YouTube Music Headers: VALID")
            print()
            safe_print(f"  {Colors.GREEN}Your authentication is working correctly!{Colors.RESET}")
            print(f"  You can sync playlists without any issues.")
        else:
            if error_type == 'missing':
                print_error("❌ YouTube Music Headers: NOT CONFIGURED")
                print()
                safe_print(f"  {Colors.RED}Headers file (browser_auth.json) not found.{Colors.RESET}")
                print()
                print_warning("Action Required:")
                print("  1. Run: python setup_browser_auth.py")
                print("  2. Follow the instructions to configure headers")
                print("  3. Paste the request headers when prompted")
            elif error_type == 'expired':
                print_error("❌ YouTube Music Headers: EXPIRED")
                print()
                safe_print(f"  {Colors.RED}Your authentication headers have EXPIRED.{Colors.RESET}")
                print()
                print_warning("Action Required:")
                print("  1. Run: python setup_browser_auth.py")
                print("  2. Follow the instructions to get NEW headers")
                print("  3. Paste the new headers when prompted")
            elif error_type == 'network':
                print_warning("⚠️  YouTube Music Headers: NETWORK ERROR")
                print()
                print(f"  {message}")
                print()
                print_info("Check your internet connection and try again.")
            else:
                print_warning("⚠️  YouTube Music Headers: UNKNOWN STATUS")
                print()
                print(f"  {message}")
        print_divider()
        
    except Exception as e:
        print_error(f"Error checking headers: {e}")
        import traceback
        traceback.print_exc()
    
    pause()


def validate_mappings():
    """Validate playlist mappings and find broken ones."""
    print_header("VALIDATE MAPPINGS", "Check for broken YouTube Music playlists")
    
    mapping = get_playlist_mapping()
    if not mapping:
        print_warning("No mappings to validate.")
        pause()
        return
    
    if not check_ytmusic_configured():
        print_error("YouTube Music not configured!")
        pause()
        return
    
    print_info(f"Checking {len(mapping)} playlist mappings...")
    print()
    
    try:
        # First check authentication
        from utils.ytmusic_validator import check_ytmusic_auth
        auth_valid, auth_msg, error_type = check_ytmusic_auth()
        
        if not auth_valid and error_type in ('expired', 'missing'):
            if error_type == 'expired':
                print_error("YouTube Music headers have EXPIRED!")
            else:
                print_error("YouTube Music headers NOT CONFIGURED!")
            print_warning(auth_msg)
            print()
            print_info("Cannot validate mappings without valid authentication.")
            if error_type == 'expired':
                print_info("Your headers have expired - please refresh them.")
            print_info("Please run: python setup_browser_auth.py")
            pause()
            return
        
        # Auth is valid, proceed with validation
        ytm = get_ytmusic_client()
        from utils.ytmusic_validator import validate_all_playlists
        
        print_info("Validating playlist access...")
        results = validate_all_playlists(ytm, mapping)
        
        print()
        print_divider()
        print_success(f"Valid mappings: {len(results['valid'])}")
        
        # Show auth errors separately
        if results['auth_errors']:
            print_warning(f"Auth errors: {len(results['auth_errors'])}")
            print("\nThe following mappings have authentication errors:")
            print_divider()
            for sp_id, yt_id in results['auth_errors']:
                safe_print(f"  Spotify: {sp_id[:35]}...")
                safe_print(f"  YTMusic: {Colors.YELLOW}{yt_id}{Colors.RESET} (AUTH ERROR)")
                print()
            print_info("These might be temporary - headers may be partially expired.")
            print()
        
        # Show missing playlists
        if results['missing']:
            print_warning(f"Missing playlists: {len(results['missing'])}")
            print("\nThe following YouTube Music playlists no longer exist:")
            print_divider()
            for sp_id, yt_id in results['missing']:
                safe_print(f"  Spotify: {sp_id[:35]}...")
                safe_print(f"  YTMusic: {Colors.RED}{yt_id}{Colors.RESET} (NOT FOUND)")
                print()
            
            confirm = input("Remove these broken mappings from config? (y/n): ").strip().lower()
            if confirm == 'y':
                from config_updater import remove_playlist_mappings
                sp_ids_to_remove = [sp_id for sp_id, _ in results['missing']]
                removed = remove_playlist_mappings(sp_ids_to_remove)
                print_success(f"Removed {removed} broken mappings!")
                print_info("Backup saved as config.py.backup")
            else:
                print_info("No changes made.")
        elif not results['auth_errors']:
            print_success("All mappings are valid!")
        
        # Show unknown errors
        if results['unknown_errors']:
            print_warning(f"Unknown errors: {len(results['unknown_errors'])}")
            for sp_id, yt_id, err_msg in results['unknown_errors']:
                safe_print(f"  {sp_id[:35]}... -> {yt_id}")
                print(f"    Error: {err_msg}")
        
    except Exception as e:
        print_error(str(e))
        import traceback
        traceback.print_exc()
    
    pause()




def view_ytmusic_playlists():
    """View user's YouTube Music playlists."""
    print_header("YOUR YOUTUBE MUSIC PLAYLISTS")
    
    # First check if authentication is actually valid
    if not check_ytmusic_configured():
        print_error("YouTube Music not configured!")
        print_info("Please run: python setup_browser_auth.py")
        pause()
        return
    
    # Verify auth is valid, not just that file exists
    try:
        from utils.ytmusic_validator import check_ytmusic_auth
        is_valid, message, error_type = check_ytmusic_auth()
        if not is_valid:
            if error_type == 'expired':
                print_error("YouTube Music headers have EXPIRED!")
                print_warning("Your authentication is no longer valid.")
            else:
                print_error(f"Authentication error: {message}")
            print_info("Please run: python setup_browser_auth.py to refresh")
            pause()
            return
    except Exception as e:
        print_warning(f"Could not verify auth: {e}")
    
    try:
        ytm = get_ytmusic_client()
        playlists = ytm.get_library_playlists(limit=20)
        
        if playlists:
            print(f"Found {len(playlists)} playlists:")
            print_divider()
            
            for pl in playlists:
                safe_print(f"  {Colors.BOLD}{pl.get('title', 'Unknown')}{Colors.RESET}")
                print(f"  {Colors.DIM}ID: {pl.get('playlistId', 'N/A')}{Colors.RESET}")
                print()
        else:
            print_warning("No playlists found.")
    except Exception as e:
        error_str = str(e).lower()
        if '401' in error_str or 'unauthorized' in error_str or 'not signed in' in error_str:
            print_error("You are NOT signed in! Your authentication headers have expired.")
            print_info("Please run: python setup_browser_auth.py to get fresh headers")
        else:
            print_error(str(e))
    
    pause()


def create_ytmusic_playlist_interactive():
    """Create a new YouTube Music playlist."""
    print_header("CREATE YOUTUBE MUSIC PLAYLIST")
    
    # First check if authentication is actually valid
    if not check_ytmusic_configured():
        print_error("YouTube Music not configured!")
        print_info("Please run: python setup_browser_auth.py")
        pause()
        return
    
    # Verify auth is valid, not just that file exists
    try:
        from utils.ytmusic_validator import check_ytmusic_auth
        is_valid, message, error_type = check_ytmusic_auth()
        if not is_valid:
            if error_type == 'expired':
                print_error("YouTube Music headers have EXPIRED!")
                print_warning("Your authentication is no longer valid.")
            else:
                print_error(f"Authentication error: {message}")
            print_info("Please run: python setup_browser_auth.py to refresh")
            pause()
            return
    except Exception as e:
        print_warning(f"Could not verify auth: {e}")
    
    playlist_name = input("Enter playlist name: ").strip()
    if not playlist_name:
        print_error("Playlist name cannot be empty.")
        pause()
        return
    
    description = input("Enter description (optional): ").strip()
    
    print("\nPrivacy options:")
    print("  [1] Private (only you)")
    print("  [2] Public (anyone)")
    print("  [3] Unlisted (with link)")
    
    privacy_choice = input("Choose (1-3, default=1): ").strip()
    privacy_map = {"1": "PRIVATE", "2": "PUBLIC", "3": "UNLISTED", "": "PRIVATE"}
    privacy_status = privacy_map.get(privacy_choice, "PRIVATE")
    
    print_divider()
    safe_print(f"Name: {playlist_name}")
    print(f"Description: {description or '(none)'}")
    print(f"Privacy: {privacy_status}")
    print_divider()
    
    if input("\nCreate this playlist? (y/n): ").strip().lower() != 'y':
        print_warning("Cancelled.")
        pause()
        return
    
    try:
        from create_ytmusic_playlist import create_playlist
        playlist_id = create_playlist(playlist_name, description, privacy_status)
        print_success(f"Created! ID: {playlist_id}")
    except Exception as e:
        error_str = str(e).lower()
        if '401' in error_str or 'unauthorized' in error_str or 'not signed in' in error_str:
            print_error("You are NOT signed in! Your authentication headers have expired.")
            print_info("Please run: python setup_browser_auth.py to get fresh headers")
        else:
            print_error(str(e))
    
    pause()


# =============================================================================
# AUTO-CREATE YOUTUBE MUSIC PLAYLISTS
# =============================================================================

def auto_create_menu():
    """Auto-creation is disabled in No-API mode."""
    print_header("AUTO-CREATE PLAYLISTS")
    print_warning("This feature is disabled in No-API Scraper mode.")
    print()
    print("Auto-creation requires listing all your private playlists via the Spotify API.")
    print("Since we are now using a scraper (which only sees public playlists),")
    print("you must manually map your playlists using their URLs.")
    print()
    print_info("Go to 'Manage Playlists' -> 'Add new playlist mapping' instead.")
    pause()


def auto_create_ytm_playlists(dry_run=False):
    """Auto-create YouTube Music playlists from Spotify."""
    mode = "(DRY RUN)" if dry_run else ""
    print_header(f"AUTO-CREATE PLAYLISTS {mode}")
    
    if not check_spotify_configured():
        print_error("Spotify not configured! Set it up first.")
        pause()
        return
    
    if not check_ytmusic_configured():
        print_error("YouTube Music not configured! Set it up first.")
        pause()
        return
    
    try:
        import importlib
        import config
        importlib.reload(config)
        from config_updater import append_playlist_mappings
        
        print_info("Connecting to Spotify...")
        sp = get_spotify_client()
        
        print_info("Fetching your Spotify playlists...")
        all_playlists = []
        results = sp.current_user_playlists(limit=50)
        while results:
            all_playlists.extend(results['items'])
            if results['next']:
                results = sp.next(results)
            else:
                break
        
        print_success(f"Found {len(all_playlists)} Spotify playlists")
        
        # Get current mapping
        current_mapping = getattr(config, 'PLAYLIST_MAPPING', {}).copy()
        
        # Find unmapped playlists
        unmapped = [pl for pl in all_playlists 
                   if pl and pl.get('id') and pl.get('id') not in current_mapping]
        
        if not unmapped:
            print_success("All your Spotify playlists are already mapped!")
            pause()
            return
        
        print_info(f"Found {len(unmapped)} unmapped playlists")
        print()
        
        print("Playlists to create:")
        print_divider()
        for i, pl in enumerate(unmapped[:10], 1):
            safe_print(f"  {i}. {pl['name']}")
        if len(unmapped) > 10:
            print(f"  ... and {len(unmapped) - 10} more")
        print()
        
        if not dry_run:
            confirm = input(f"Create {len(unmapped)} playlists? (yes/no): ").strip().lower()
            if confirm not in ['yes', 'y']:
                print_warning("Cancelled.")
                pause()
                return
            
            print_info("Connecting to YouTube Music...")
            ytm = get_ytmusic_client()
            
            new_mappings = {}
            for pl in unmapped:
                try:
                    safe_print(f"  Creating: {pl['name']}")
                    yt_id = ytm.create_playlist(
                        title=pl['name'],
                        description=f"Synced from Spotify",
                        privacy_status='PRIVATE' if getattr(config, 'YTMUSIC_PLAYLIST_PRIVATE', True) else 'PUBLIC'
                    )
                    new_mappings[pl['id']] = yt_id
                    print_success(f"    Created (ID: {yt_id})")
                except Exception as e:
                    print_error(f"    Failed: {e}")
            
            if new_mappings:
                print_info("Updating config.py...")
                try:
                    added = append_playlist_mappings(new_mappings)
                    print_success(f"Added {added} new mappings to config.py!")
                except Exception as e:
                    print_error(f"Failed to update config: {e}")
        else:
            print_info(f"Dry run complete. Would create {len(unmapped)} playlists.")
        
    except Exception as e:
        print_error(str(e))
        import traceback
        traceback.print_exc()
    
    pause()


# =============================================================================
# SYNC FUNCTIONS
# =============================================================================

def run_sync(dry_run=False):
    """Run the playlist sync."""
    mode = "(DRY RUN)" if dry_run else ""
    print_header(f"RUNNING SYNC {mode}")
    
    mapping = get_playlist_mapping()
    if not mapping:
        print_error("No playlist mappings configured!")
        print_info("Go to Playlist Management to add some.")
        pause()
        return
    
    print_info(f"Syncing {len(mapping)} playlist(s)...")
    print()
    
    try:
        from sync_playlists import sync_playlists
        sync_playlists(dry_run=dry_run)
    except Exception as e:
        print_error(f"Error during sync: {e}")
    
    pause()


# =============================================================================
# MAIN MENU
# =============================================================================

def show_status():
    """Display current setup status."""
    spotify_ok = check_spotify_configured()
    ytmusic_ok = check_ytmusic_configured()
    playlists = get_playlist_mapping()
    
    # Check YTMusic header validity
    ytmusic_auth_valid = False
    ytmusic_status_msg = "Not configured"
    if ytmusic_ok:
        try:
            from utils.ytmusic_validator import check_ytmusic_auth
            is_valid, message, error_type = check_ytmusic_auth()
            ytmusic_auth_valid = is_valid
            if is_valid:
                ytmusic_status_msg = "Valid"
            elif error_type == 'expired':
                ytmusic_status_msg = "*** EXPIRED - REFRESH HEADERS ***"
            elif error_type == 'missing':
                ytmusic_status_msg = "*** NOT CONFIGURED ***"
            else:
                ytmusic_status_msg = "Unknown error"
        except:
            ytmusic_status_msg = "Unknown"
            ytmusic_auth_valid = True  # Assume valid if can't check
    
    # Get last sync time
    last_sync_msg = "Never"
    try:
        import os
        from datetime import datetime
        if os.path.exists("sync_log.txt"):
            with open("sync_log.txt", "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in reversed(lines):
                    if "SYNC STARTED" in line or "SYNC COMPLETE" in line:
                        # Extract timestamp from log line
                        if line.startswith("["):
                            timestamp_str = line[1:20]  # [2025-12-24 19:30:03]
                            try:
                                log_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                                now = datetime.now()
                                diff = now - log_time
                                
                                if diff.days > 0:
                                    last_sync_msg = f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
                                elif diff.seconds >= 3600:
                                    hours = diff.seconds // 3600
                                    last_sync_msg = f"{hours} hour{'s' if hours > 1 else ''} ago"
                                elif diff.seconds >= 60:
                                    minutes = diff.seconds // 60
                                    last_sync_msg = f"{minutes} minute{'s' if minutes > 1 else ''} ago"
                                else:
                                    last_sync_msg = "Just now"
                            except:
                                pass
                        break
    except:
        pass
    
    print("Current Status:")
    print_divider()
    print_status("Spotify (Scraper)", spotify_ok)
    
    # Show YTMusic status with header validity
    if ytmusic_ok:
        if ytmusic_auth_valid:
            print_status("YouTube Music", True)
            safe_print(f"  {Colors.DIM}Headers: {Colors.GREEN}{ytmusic_status_msg}{Colors.RESET}")
        else:
            safe_print(f"  YouTube Music: {Colors.RED}✗{Colors.RESET}")
            safe_print(f"  {Colors.RED}{Colors.BOLD}STATUS: {ytmusic_status_msg}{Colors.RESET}")
            print(f"  {Colors.YELLOW}Action: Run 'python setup_browser_auth.py'{Colors.RESET}")
    else:
        print_status("YouTube Music", False)
    
    print(f"  Playlists: {len(playlists)} mapped")
    print(f"  {Colors.DIM}Last sync: {last_sync_msg}{Colors.RESET}")
    print()
    
    return spotify_ok, ytmusic_ok and ytmusic_auth_valid


def show_welcome_if_needed():
    """Show welcome screen for first-time users."""
    # Check if this is first run (no credentials configured)
    if not check_spotify_configured() or not check_ytmusic_configured():
        print_header("WELCOME TO SPOTIFY → YOUTUBE MUSIC SYNC!", "Your music, synced effortlessly")
        
        print_box([
            "This tool syncs your Spotify playlists to YouTube Music automatically!",
            "",
            "Quick Setup (2 minutes):",
            "  1. Configure Spotify credentials",
            "  2. Setup YouTube Music headers",
            "  3. Map your playlists",
            "  4. Run your first sync!"
        ], "Getting Started")
        print()
        
        spotify_ok = check_spotify_configured()
        ytmusic_ok = check_ytmusic_configured()
        
        print("Setup Status:")
        print_divider()
        safe_print(f"  {Colors.GREEN}✓{Colors.RESET} Spotify  {Colors.DIM}(Scraper Mode active){Colors.RESET}")
        
        if not ytmusic_ok:
            safe_print(f"  {Colors.RED}✗{Colors.RESET} YouTube Music  {Colors.DIM}→ Select 'Setup YouTube Music' below{Colors.RESET}")
        else:
            safe_print(f"  {Colors.GREEN}✓{Colors.RESET} YouTube Music  {Colors.DIM}(configured){Colors.RESET}")
        print()
        
        print_info("💡 Tip: Complete the setup steps below to get started!")
        print()
        pause()


def main_menu():
    """Main application menu."""
    ensure_config_exists()
    
    # Show welcome screen for first-time users
    show_welcome_if_needed()
    
    while True:
        print_header("SPOTIFY TO YOUTUBE MUSIC SYNC", 
                    "Sync your Spotify playlists to YouTube Music")
        
        spotify_ok, ytmusic_ok = show_status()
        
        if not spotify_ok or not ytmusic_ok:
            print_warning("Setup required! Complete the setup below.")
            print()
        
        print_menu([
            "Sync Now",
            "Preview Sync (Dry Run)",
            "Manage Playlists",
            "YouTube Music Setup",
            "Spotify Scraper Info",
        ])
        
        choice = get_choice(5)
        
        if choice == 0:
            print("\nGoodbye!")
            break
        elif choice == 1:
            if not ytmusic_ok:
                print_error("Please set up YouTube Music first!")
                pause()
            else:
                run_sync(dry_run=False)
        elif choice == 2:
            if not ytmusic_ok:
                print_error("Please complete setup first!")
                pause()
            else:
                run_sync(dry_run=True)
        elif choice == 3:
            manage_playlists()
        elif choice == 4:
            setup_ytmusic()
        elif choice == 5:
            setup_spotify()


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
