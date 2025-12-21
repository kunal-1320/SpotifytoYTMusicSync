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
    if not os.path.exists("config.py"):
        if os.path.exists("config.example.py"):
            import shutil
            shutil.copy("config.example.py", "config.py")
            return True
    return os.path.exists("config.py")


# =============================================================================
# SETUP FUNCTIONS
# =============================================================================

def setup_spotify():
    """Interactive Spotify setup."""
    print_header("SPOTIFY SETUP", "Configure your Spotify API credentials")
    
    print("You need to create a Spotify Developer App to use this tool.")
    print()
    print_box([
        "1. Go to: https://developer.spotify.com/dashboard",
        "2. Log in and click 'Create App'",
        "3. Fill in any name and description",
        "4. Set Redirect URI to: http://127.0.0.1:8888/callback",
        "5. Save and get your Client ID and Client Secret"
    ], "Steps")
    print()
    
    client_id = input("Enter your Spotify Client ID: ").strip()
    if not client_id:
        print_warning("Cancelled.")
        pause()
        return False
    
    client_secret = input("Enter your Spotify Client Secret: ").strip()
    if not client_secret:
        print_warning("Cancelled.")
        pause()
        return False
    
    # Update config.py
    try:
        ensure_config_exists()
        
        with open("config.py", "r") as f:
            content = f.read()
        
        import re
        content = re.sub(
            r'SPOTIFY_CLIENT_ID = "[^"]*"',
            f'SPOTIFY_CLIENT_ID = "{client_id}"',
            content
        )
        content = re.sub(
            r'SPOTIFY_CLIENT_SECRET = "[^"]*"',
            f'SPOTIFY_CLIENT_SECRET = "{client_secret}"',
            content
        )
        
        with open("config.py", "w") as f:
            f.write(content)
        
        print_success("Spotify credentials saved!")
        
        # Test connection
        print_info("Testing Spotify connection...")
        success, msg, user = test_spotify_connection()
        if success:
            print_success(msg)
        else:
            print_error(f"Connection failed: {msg}")
            print_info("Make sure your credentials are correct and Redirect URI is set.")
        
        pause()
        return success
    except Exception as e:
        print_error(f"Error saving config: {e}")
        pause()
        return False


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
        "  5. Copy the request headers"
    ])
    print()
    
    choice = input("Continue with quick setup here? (y/n): ").strip().lower()
    
    if choice != 'y':
        print_info("Run: python setup_browser_auth.py")
        pause()
        return False
    
    print("\nPaste your request headers below (press Enter twice when done):")
    print_divider()
    
    lines = []
    empty_count = 0
    while True:
        try:
            line = input()
            if line.strip() == "":
                empty_count += 1
                if empty_count >= 2:
                    break
            else:
                empty_count = 0
                lines.append(line)
        except (EOFError, KeyboardInterrupt):
            break
    
    headers_text = '\n'.join(lines)
    
    if not headers_text or len(headers_text) < 100:
        print_error("Headers too short or empty. Cancelled.")
        pause()
        return False
    
    try:
        from ytmusicapi import setup
        setup(filepath='browser_auth.json', headers_raw=headers_text)
        print_success("YouTube Music browser auth saved!")
        
        # Test connection
        print_info("Testing YouTube Music connection...")
        success, msg = test_ytmusic_connection()
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
            "Validate mappings (find broken ones)",
            "View Spotify playlists",
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
            view_spotify_playlists()
        elif choice == 5:
            view_ytmusic_playlists()
        elif choice == 6:
            create_ytmusic_playlist_interactive()


def add_playlist_mapping():
    """Add a new playlist mapping."""
    print_header("ADD PLAYLIST MAPPING")
    
    print_box([
        "Spotify ID: From playlist URL after /playlist/",
        "YT Music ID: From playlist URL after ?list= (starts with PL)"
    ], "How to find IDs")
    print()
    
    spotify_id = input("Spotify Playlist ID: ").strip()
    if not spotify_id:
        return
    
    ytmusic_id = input("YouTube Music Playlist ID: ").strip()
    if not ytmusic_id:
        return
    
    try:
        ensure_config_exists()
        
        with open("config.py", "r") as f:
            content = f.read()
        
        import re
        pattern = r'(PLAYLIST_MAPPING = \{[^}]*)'
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            old_mapping = match.group(1)
            new_entry = f'\n    "{spotify_id}": "{ytmusic_id}",'
            new_mapping = old_mapping + new_entry
            content = content.replace(old_mapping, new_mapping)
            
            with open("config.py", "w") as f:
                f.write(content)
            
            print_success("Mapping added!")
            print(f"   Spotify: {spotify_id}")
            print(f"   YT Music: {ytmusic_id}")
        else:
            print_error("Could not find PLAYLIST_MAPPING in config.py")
    except Exception as e:
        print_error(str(e))
    
    pause()


def remove_playlist_mapping():
    """Remove a playlist mapping."""
    mapping = get_playlist_mapping()
    if not mapping:
        print_warning("No mappings to remove.")
        pause()
        return
    
    print_header("REMOVE PLAYLIST MAPPING")
    print("Select a mapping to remove:")
    print()
    
    items = list(mapping.items())
    for i, (sp_id, yt_id) in enumerate(items, 1):
        print(f"  [{i}] {sp_id[:40]}...")
    print("  [0] Cancel")
    print()
    
    choice = get_choice(len(items))
    if choice == 0:
        return
    
    sp_id_to_remove = items[choice - 1][0]
    
    try:
        with open("config.py", "r") as f:
            content = f.read()
        
        import re
        pattern = rf'\s*"{re.escape(sp_id_to_remove)}"\s*:\s*"[^"]*"\s*,?\s*\n?'
        content = re.sub(pattern, '\n', content)
        
        with open("config.py", "w") as f:
            f.write(content)
        
        print_success(f"Removed: {sp_id_to_remove[:40]}...")
    except Exception as e:
        print_error(str(e))
    
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
        ytm = get_ytmusic_client()
        
        # Get user's YTMusic playlists
        print_info("Fetching your YouTube Music playlists...")
        yt_playlists = ytm.get_library_playlists(limit=100)
        valid_yt_ids = set()
        if yt_playlists:
            for pl in yt_playlists:
                if pl and pl.get('playlistId'):
                    valid_yt_ids.add(pl['playlistId'])
        
        # Check each mapping
        broken_mappings = []
        valid_count = 0
        
        for sp_id, yt_id in mapping.items():
            if yt_id in valid_yt_ids:
                valid_count += 1
            else:
                # Try to fetch the playlist directly to confirm it's broken
                try:
                    ytm.get_playlist(yt_id, limit=1)
                    valid_count += 1
                    valid_yt_ids.add(yt_id)
                except Exception:
                    broken_mappings.append((sp_id, yt_id))
        
        print()
        print_divider()
        print_success(f"Valid mappings: {valid_count}")
        
        if broken_mappings:
            print_warning(f"Broken mappings: {len(broken_mappings)}")
            print()
            print("The following YouTube Music playlists no longer exist:")
            print_divider()
            for sp_id, yt_id in broken_mappings:
                safe_print(f"  Spotify: {sp_id[:35]}...")
                safe_print(f"  YTMusic: {Colors.RED}{yt_id}{Colors.RESET} (NOT FOUND)")
                print()
            
            confirm = input("Remove these broken mappings from config? (y/n): ").strip().lower()
            if confirm == 'y':
                from config_updater import remove_playlist_mappings
                sp_ids_to_remove = [sp_id for sp_id, _ in broken_mappings]
                removed = remove_playlist_mappings(sp_ids_to_remove)
                print_success(f"Removed {removed} broken mappings!")
                print_info("Backup saved as config.py.backup")
            else:
                print_info("No changes made.")
        else:
            print_success("All mappings are valid!")
        
    except Exception as e:
        print_error(str(e))
        import traceback
        traceback.print_exc()
    
    pause()


def view_spotify_playlists():
    """View user's Spotify playlists."""
    print_header("YOUR SPOTIFY PLAYLISTS")
    
    try:
        sp = get_spotify_client()
        playlists = sp.current_user_playlists(limit=20)
        
        print(f"Found {len(playlists['items'])} playlists:")
        print_divider()
        
        for pl in playlists['items']:
            safe_print(f"  {Colors.BOLD}{pl['name']}{Colors.RESET}")
            print(f"  {Colors.DIM}ID: {pl['id']}{Colors.RESET}")
            print()
    except Exception as e:
        print_error(str(e))
    
    pause()


def view_ytmusic_playlists():
    """View user's YouTube Music playlists."""
    print_header("YOUR YOUTUBE MUSIC PLAYLISTS")
    
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
        print_error(str(e))
    
    pause()


def create_ytmusic_playlist_interactive():
    """Create a new YouTube Music playlist."""
    print_header("CREATE YOUTUBE MUSIC PLAYLIST")
    
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
        print_error(str(e))
    
    pause()


# =============================================================================
# AUTO-CREATE YOUTUBE MUSIC PLAYLISTS
# =============================================================================

def auto_create_menu():
    """Submenu for auto-creating YouTube Music playlists."""
    while True:
        print_header("AUTO-CREATE YOUTUBE MUSIC PLAYLISTS", 
                    "Create YTM playlists from your Spotify library")
        
        print_box([
            "This feature will:",
            "  1. Fetch all your Spotify playlists",
            "  2. Create matching playlists on YouTube Music",
            "  3. Update config.py with the mappings"
        ])
        print()
        
        print_menu([
            "Preview (Dry Run - see what would be created)",
            "Create Playlists (actually create them)",
        ])
        
        choice = get_choice(2)
        
        if choice == 0:
            break
        elif choice == 1:
            auto_create_ytm_playlists(dry_run=True)
        elif choice == 2:
            auto_create_ytm_playlists(dry_run=False)


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
    
    print("Current Status:")
    print_divider()
    print_status("Spotify", spotify_ok)
    print_status("YouTube Music", ytmusic_ok)
    print(f"  Playlists: {len(playlists)} mapped")
    print()
    
    return spotify_ok, ytmusic_ok


def main_menu():
    """Main application menu."""
    ensure_config_exists()
    
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
            "Setup Spotify",
            "Setup YouTube Music",
            "Auto-create YouTube Music Playlists",
        ])
        
        choice = get_choice(6)
        
        if choice == 0:
            print("\nGoodbye!")
            break
        elif choice == 1:
            if not spotify_ok:
                print_error("Please set up Spotify first!")
                pause()
            elif not ytmusic_ok:
                print_error("Please set up YouTube Music first!")
                pause()
            else:
                run_sync(dry_run=False)
        elif choice == 2:
            if not spotify_ok or not ytmusic_ok:
                print_error("Please complete setup first!")
                pause()
            else:
                run_sync(dry_run=True)
        elif choice == 3:
            manage_playlists()
        elif choice == 4:
            setup_spotify()
        elif choice == 5:
            setup_ytmusic()
        elif choice == 6:
            auto_create_menu()


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
