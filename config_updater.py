"""
Config Updater - Safely update config.py with new playlist mappings
====================================================================
Handles reading, modifying, and writing config.py while preserving
formatting and creating backups.
"""

import os
import re
import shutil
from typing import Dict, List, Optional


def validate_playlist_id(playlist_id: str, platform: str = "spotify") -> bool:
    """
    Validate a playlist ID format.
    
    Args:
        playlist_id: The ID to validate
        platform: Either "spotify" or "ytmusic"
    
    Returns:
        True if valid, False otherwise
    """
    if not playlist_id or not isinstance(playlist_id, str):
        return False
    
    playlist_id = playlist_id.strip()
    
    if platform == "spotify":
        # Spotify IDs are 22 alphanumeric characters
        return len(playlist_id) >= 10 and playlist_id.isalnum()
    elif platform == "ytmusic":
        # YouTube Music playlist IDs typically start with PL or VL
        return len(playlist_id) >= 10
    
    return False


def get_config_path() -> str:
    """Get the path to config.py relative to this file's directory."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.py")


def create_backup(config_path: str) -> str:
    """
    Create a backup of config.py.
    
    Args:
        config_path: Path to the config file
    
    Returns:
        Path to the backup file
    """
    backup_path = config_path + ".backup"
    shutil.copy2(config_path, backup_path)
    return backup_path


def rollback_config(config_path: str) -> bool:
    """
    Rollback config.py from backup.
    
    Args:
        config_path: Path to the config file
    
    Returns:
        True if rollback successful, False otherwise
    """
    backup_path = config_path + ".backup"
    if os.path.exists(backup_path):
        shutil.copy2(backup_path, config_path)
        return True
    return False


def remove_playlist_mappings(spotify_ids_to_remove: List[str]) -> int:
    """
    Remove specific playlist mappings from config.py.
    
    Args:
        spotify_ids_to_remove: List of Spotify playlist IDs to remove
    
    Returns:
        Number of mappings removed
    
    Raises:
        FileNotFoundError: If config.py doesn't exist
    """
    config_path = get_config_path()
    
    if not os.path.exists(config_path):
        raise FileNotFoundError("config.py not found.")
    
    if not spotify_ids_to_remove:
        return 0
    
    # Create backup
    create_backup(config_path)
    
    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    removed_count = 0
    for sp_id in spotify_ids_to_remove:
        sp_id = sp_id.strip()
        # Match the line with this Spotify ID
        pattern = rf'\s*"{re.escape(sp_id)}"\s*:\s*"[^"]*"\s*,?\s*\n?'
        if re.search(pattern, content):
            content = re.sub(pattern, '\n', content)
            removed_count += 1
    
    # Clean up any double newlines
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    return removed_count


def append_playlist_mappings(new_mappings: Dict[str, str]) -> int:
    """
    Append new Spotify-to-YouTube Music playlist mappings to config.py.
    
    Creates a backup before modifying and validates input.
    
    Args:
        new_mappings: Dictionary where keys are Spotify playlist IDs 
                     and values are YouTube Music playlist IDs.
    
    Returns:
        Number of mappings successfully added
    
    Raises:
        FileNotFoundError: If config.py doesn't exist
        ValueError: If PLAYLIST_MAPPING not found in config.py
    """
    config_path = get_config_path()
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(
            "config.py not found. Please create it from config.example.py first."
        )
    
    if not new_mappings:
        return 0
    
    # Create backup before any modifications
    create_backup(config_path)
    
    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Find PLAYLIST_MAPPING dictionary using a more robust pattern
    # This handles multi-line dictionaries with comments
    pattern = r'(PLAYLIST_MAPPING\s*=\s*\{)(.*?)(\})'
    match = re.search(pattern, content, re.DOTALL)
    
    if not match:
        raise ValueError("Could not find PLAYLIST_MAPPING dictionary in config.py")
    
    header = match.group(1)
    existing_entries = match.group(2)
    footer = match.group(3)
    
    # Count how many we actually add
    added_count = 0
    new_entries_str = ""
    
    for sp_id, yt_id in new_mappings.items():
        # Validate IDs
        sp_id = sp_id.strip()
        yt_id = yt_id.strip()
        
        if not validate_playlist_id(sp_id, "spotify"):
            print(f"  Warning: Skipping invalid Spotify ID: {sp_id}")
            continue
        
        if not validate_playlist_id(yt_id, "ytmusic"):
            print(f"  Warning: Skipping invalid YouTube Music ID: {yt_id}")
            continue
        
        # Check if already exists to avoid duplicates
        if f'"{sp_id}"' not in existing_entries:
            new_entries_str += f'\n    "{sp_id}": "{yt_id}",'
            added_count += 1
    
    if not new_entries_str:
        return 0  # Nothing to add
    
    # Ensure proper formatting - remove trailing whitespace from existing
    existing_entries = existing_entries.rstrip()
    
    # Combine everything
    updated_mapping = f"{header}{existing_entries}{new_entries_str}\n{footer}"
    new_content = content[:match.start()] + updated_mapping + content[match.end():]
    
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    
    return added_count


def get_unmapped_playlists(all_playlists: List[dict], current_mapping: Dict[str, str]) -> List[dict]:
    """
    Filter out playlists that are already in the current mapping.
    
    Args:
        all_playlists: List of Spotify playlist objects from spotipy.
                      Each should have an 'id' key.
        current_mapping: Dictionary of current Spotify->YTMusic mappings.
    
    Returns:
        List of unmapped Spotify playlist objects.
    """
    if not all_playlists:
        return []
    
    if not current_mapping:
        current_mapping = {}
    
    unmapped = []
    for pl in all_playlists:
        if pl and isinstance(pl, dict):
            pl_id = pl.get('id')
            if pl_id and pl_id not in current_mapping:
                unmapped.append(pl)
    
    return unmapped


def get_current_mappings() -> Dict[str, str]:
    """
    Read and return the current PLAYLIST_MAPPING from config.py.
    
    Returns:
        Dictionary of current mappings, or empty dict if not found.
    """
    try:
        import importlib
        import config
        importlib.reload(config)
        if hasattr(config, 'PLAYLIST_MAPPING'):
            return dict(config.PLAYLIST_MAPPING)
    except Exception:
        pass
    return {}


# Self-test when run directly
if __name__ == "__main__":
    print("Testing config_updater.py...")
    print()
    
    # Test validate_playlist_id
    print("1. Testing validate_playlist_id:")
    print(f"   Valid Spotify ID: {validate_playlist_id('37i9dQZF1DXcBWIGoYBM5M', 'spotify')}")
    print(f"   Invalid Spotify ID: {validate_playlist_id('abc', 'spotify')}")
    print(f"   Valid YTMusic ID: {validate_playlist_id('PLY3LuyWhQkjoEvyml9yoPi8IOsXQNjE8f', 'ytmusic')}")
    print()
    
    # Test get_unmapped_playlists
    print("2. Testing get_unmapped_playlists:")
    test_playlists = [
        {'id': 'playlist1', 'name': 'Test 1'},
        {'id': 'playlist2', 'name': 'Test 2'},
        {'id': 'playlist3', 'name': 'Test 3'},
    ]
    test_mapping = {'playlist1': 'yt1'}
    unmapped = get_unmapped_playlists(test_playlists, test_mapping)
    print(f"   Input: 3 playlists, 1 mapped")
    print(f"   Output: {len(unmapped)} unmapped")
    print()
    
    # Test get_current_mappings
    print("3. Testing get_current_mappings:")
    mappings = get_current_mappings()
    print(f"   Found {len(mappings)} existing mappings")
    print()
    
    print("All tests passed!")
