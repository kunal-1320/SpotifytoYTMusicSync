"""
Utils Package - Shared utilities for Spotify to YouTube Music Sync
"""

from .clients import (
    get_spotify_client,
    get_ytmusic_client,
    test_spotify_connection,
    test_ytmusic_connection,
)

from .ui import (
    clear_screen,
    print_header,
    print_menu,
    print_submenu,
    get_choice,
    pause,
    safe_print,
    print_status,
    print_success,
    print_error,
    print_warning,
    print_info,
)

__all__ = [
    # Clients
    'get_spotify_client',
    'get_ytmusic_client', 
    'test_spotify_connection',
    'test_ytmusic_connection',
    # UI
    'clear_screen',
    'print_header',
    'print_menu',
    'print_submenu',
    'get_choice',
    'pause',
    'safe_print',
    'print_status',
    'print_success',
    'print_error',
    'print_warning',
    'print_info',
]
