#!/usr/bin/env python3
"""
YouTube Music Playlist Creator
================================
Create and manage YouTube Music playlists.
"""

import os
import sys
from ytmusicapi import YTMusic


def get_ytmusic_client():
    """
    Create and return an authenticated YouTube Music client.
    
    Returns:
        YTMusic client instance
    
    Raises:
        FileNotFoundError: If browser_auth.json doesn't exist
        Exception: If authentication fails
    """
    auth_file = 'browser_auth.json'
    
    if not os.path.exists(auth_file):
        raise FileNotFoundError(
            f"YouTube Music authentication file '{auth_file}' not found.\n"
            "Please run 'python setup_browser_auth.py' first."
        )
    
    try:
        ytm = YTMusic(auth_file)
        return ytm
    except Exception as e:
        raise Exception(f"Failed to authenticate with YouTube Music: {e}")


def create_playlist(playlist_name, description="", privacy_status="PRIVATE"):
    """
    Create a new YouTube Music playlist.
    
    Args:
        playlist_name (str): Name of the playlist to create
        description (str): Optional description for the playlist
        privacy_status (str): Privacy setting - "PRIVATE", "PUBLIC", or "UNLISTED"
    
    Returns:
        str: Playlist ID of the created playlist
    
    Raises:
        Exception: If playlist creation fails
    """
    try:
        ytm = get_ytmusic_client()
        
        # Create the playlist
        playlist_id = ytm.create_playlist(
            title=playlist_name,
            description=description,
            privacy_status=privacy_status
        )
        
        print(f"✓ Successfully created playlist: '{playlist_name}'")
        print(f"  Playlist ID: {playlist_id}")
        print(f"  Privacy: {privacy_status}")
        
        return playlist_id
        
    except Exception as e:
        raise Exception(f"Failed to create playlist: {e}")


def list_playlists(limit=25):
    """
    List all YouTube Music playlists for the authenticated user.
    
    Args:
        limit (int): Maximum number of playlists to retrieve
    
    Returns:
        list: List of playlist dictionaries with 'title' and 'playlistId' keys
    
    Raises:
        Exception: If fetching playlists fails
    """
    try:
        ytm = get_ytmusic_client()
        playlists = ytm.get_library_playlists(limit=limit)
        
        if not playlists:
            print("No playlists found.")
            return []
        
        print(f"\nFound {len(playlists)} playlist(s):")
        print("-" * 70)
        
        for i, pl in enumerate(playlists, 1):
            title = pl.get('title', 'Unknown')
            playlist_id = pl.get('playlistId', 'N/A')
            count = pl.get('count', '?')
            
            print(f"{i:2}. {title}")
            print(f"    ID: {playlist_id}")
            print(f"    Songs: {count}")
            print()
        
        return playlists
        
    except Exception as e:
        raise Exception(f"Failed to fetch playlists: {e}")


def interactive_create():
    """
    Interactive mode for creating a YouTube Music playlist.
    Prompts user for playlist details and creates the playlist.
    """
    print("=" * 70)
    print("  CREATE YOUTUBE MUSIC PLAYLIST")
    print("=" * 70)
    print()
    
    # Get playlist name
    playlist_name = input("Enter playlist name: ").strip()
    if not playlist_name:
        print("Error: Playlist name cannot be empty.")
        return None
    
    # Get description (optional)
    description = input("Enter description (optional, press Enter to skip): ").strip()
    
    # Get privacy setting
    print("\nPrivacy options:")
    print("  [1] Private (only you can see it)")
    print("  [2] Public (anyone can see it)")
    print("  [3] Unlisted (anyone with link can see it)")
    
    privacy_choice = input("Choose privacy (1-3, default=1): ").strip()
    
    privacy_map = {
        "1": "PRIVATE",
        "2": "PUBLIC",
        "3": "UNLISTED",
        "": "PRIVATE"  # Default
    }
    
    privacy_status = privacy_map.get(privacy_choice, "PRIVATE")
    
    # Confirm
    print("\n" + "-" * 70)
    print(f"Playlist Name: {playlist_name}")
    print(f"Description:   {description if description else '(none)'}")
    print(f"Privacy:       {privacy_status}")
    print("-" * 70)
    
    confirm = input("\nCreate this playlist? (y/n): ").strip().lower()
    
    if confirm != 'y':
        print("Cancelled.")
        return None
    
    try:
        playlist_id = create_playlist(playlist_name, description, privacy_status)
        return playlist_id
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return None


def main():
    """Main entry point for standalone usage."""
    if len(sys.argv) > 1:
        # Command-line mode
        command = sys.argv[1].lower()
        
        if command == "list":
            try:
                list_playlists()
            except Exception as e:
                print(f"Error: {e}")
                sys.exit(1)
        
        elif command == "create":
            if len(sys.argv) < 3:
                print("Usage: python create_ytmusic_playlist.py create <playlist_name> [description] [privacy]")
                print("Privacy options: PRIVATE, PUBLIC, UNLISTED (default: PRIVATE)")
                sys.exit(1)
            
            playlist_name = sys.argv[2]
            description = sys.argv[3] if len(sys.argv) > 3 else ""
            privacy = sys.argv[4].upper() if len(sys.argv) > 4 else "PRIVATE"
            
            if privacy not in ["PRIVATE", "PUBLIC", "UNLISTED"]:
                print(f"Invalid privacy setting: {privacy}")
                print("Valid options: PRIVATE, PUBLIC, UNLISTED")
                sys.exit(1)
            
            try:
                create_playlist(playlist_name, description, privacy)
            except Exception as e:
                print(f"Error: {e}")
                sys.exit(1)
        
        else:
            print(f"Unknown command: {command}")
            print("Available commands: list, create")
            sys.exit(1)
    
    else:
        # Interactive mode
        try:
            interactive_create()
        except KeyboardInterrupt:
            print("\n\nCancelled.")
            sys.exit(0)


if __name__ == "__main__":
    main()
