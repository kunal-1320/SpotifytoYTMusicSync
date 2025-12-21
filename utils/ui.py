"""
UI Module - Consistent terminal UI components
==============================================
Provides styled menus, prompts, and output formatting.
"""

import os
import sys


# =============================================================================
# ANSI COLOR CODES (works on Windows 10+, macOS, Linux)
# =============================================================================

class Colors:
    """ANSI color codes for terminal output."""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Colors
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    
    # Backgrounds
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_BLUE = '\033[44m'


def _enable_windows_ansi():
    """Enable ANSI escape sequences on Windows."""
    if os.name == 'nt':
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass


# Enable colors on Windows
_enable_windows_ansi()


# =============================================================================
# CORE UI FUNCTIONS
# =============================================================================

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def safe_print(message: str):
    """
    Print with fallback for Unicode issues on Windows.
    
    Args:
        message: Text to print (may contain Unicode/emoji)
    """
    try:
        print(message)
    except UnicodeEncodeError:
        # Replace problematic characters with ASCII alternatives
        safe = message.encode('ascii', errors='replace').decode('ascii')
        print(safe)


def pause():
    """Wait for user to press Enter."""
    input(f"\n{Colors.DIM}Press Enter to continue...{Colors.RESET}")


# =============================================================================
# HEADER AND MENU FUNCTIONS  
# =============================================================================

def print_header(title: str, subtitle: str = None):
    """
    Print a styled header with optional subtitle.
    
    Args:
        title: Main header text
        subtitle: Optional subtitle text
    """
    clear_screen()
    width = 60
    
    print(f"{Colors.CYAN}{'=' * width}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.WHITE}  {title}{Colors.RESET}")
    if subtitle:
        print(f"{Colors.DIM}  {subtitle}{Colors.RESET}")
    print(f"{Colors.CYAN}{'=' * width}{Colors.RESET}")
    print()


def print_menu(options: list, show_back: bool = True):
    """
    Print a numbered menu.
    
    Args:
        options: List of menu option strings
        show_back: Whether to show [0] Back/Exit option
    """
    for i, option in enumerate(options, 1):
        safe_print(f"  {Colors.CYAN}[{i}]{Colors.RESET} {option}")
    
    if show_back:
        print(f"  {Colors.DIM}[0] Back / Exit{Colors.RESET}")
    print()


def print_submenu(title: str, options: list):
    """
    Print a submenu with title and options.
    
    Args:
        title: Submenu title
        options: List of option strings
    """
    print(f"\n{Colors.BOLD}{title}{Colors.RESET}")
    print(f"{Colors.DIM}{'-' * 40}{Colors.RESET}")
    print_menu(options)


def get_choice(max_option: int, prompt: str = "Enter choice") -> int:
    """
    Get a validated numeric choice from user.
    
    Args:
        max_option: Maximum valid option number
        prompt: Prompt text to display
    
    Returns:
        User's choice as integer (0 to max_option)
    """
    while True:
        try:
            choice = input(f"{prompt}: ").strip()
            if choice == "":
                continue
            num = int(choice)
            if 0 <= num <= max_option:
                return num
            print_error(f"Please enter a number between 0 and {max_option}")
        except ValueError:
            print_error("Invalid input. Please enter a number.")


# =============================================================================
# STATUS OUTPUT FUNCTIONS
# =============================================================================

def print_status(label: str, is_ok: bool, detail: str = None):
    """
    Print a status line with OK/FAIL indicator.
    
    Args:
        label: What is being checked
        is_ok: Whether the status is good
        detail: Optional additional detail
    """
    icon = f"{Colors.GREEN}[OK]{Colors.RESET}" if is_ok else f"{Colors.RED}[X]{Colors.RESET}"
    status = f"{Colors.GREEN}Ready{Colors.RESET}" if is_ok else f"{Colors.RED}Not configured{Colors.RESET}"
    
    line = f"  {icon} {label}: {status}"
    if detail:
        line += f" {Colors.DIM}({detail}){Colors.RESET}"
    safe_print(line)


def print_success(message: str):
    """Print a success message."""
    safe_print(f"{Colors.GREEN}[OK] {message}{Colors.RESET}")


def print_error(message: str):
    """Print an error message."""
    safe_print(f"{Colors.RED}[X] {message}{Colors.RESET}")


def print_warning(message: str):
    """Print a warning message."""
    safe_print(f"{Colors.YELLOW}[!] {message}{Colors.RESET}")


def print_info(message: str):
    """Print an info message."""
    safe_print(f"{Colors.CYAN}[i] {message}{Colors.RESET}")


def print_divider(char: str = "-", width: int = 50):
    """Print a horizontal divider line."""
    print(f"{Colors.DIM}{char * width}{Colors.RESET}")


def print_box(lines: list, title: str = None):
    """
    Print text in a box.
    
    Args:
        lines: List of lines to display
        title: Optional box title
    """
    width = max(len(line) for line in lines) + 4
    if title:
        width = max(width, len(title) + 4)
    
    print(f"{Colors.CYAN}+{'-' * (width - 2)}+{Colors.RESET}")
    if title:
        print(f"{Colors.CYAN}|{Colors.RESET} {Colors.BOLD}{title:<{width - 4}}{Colors.RESET} {Colors.CYAN}|{Colors.RESET}")
        print(f"{Colors.CYAN}+{'-' * (width - 2)}+{Colors.RESET}")
    
    for line in lines:
        safe_print(f"{Colors.CYAN}|{Colors.RESET} {line:<{width - 4}} {Colors.CYAN}|{Colors.RESET}")
    
    print(f"{Colors.CYAN}+{'-' * (width - 2)}+{Colors.RESET}")


# =============================================================================
# PROGRESS DISPLAY
# =============================================================================

def print_progress(current: int, total: int, prefix: str = "Progress"):
    """
    Print a simple progress indicator.
    
    Args:
        current: Current item number
        total: Total items
        prefix: Text before the progress
    """
    percent = (current / total) * 100 if total > 0 else 0
    bar_width = 30
    filled = int(bar_width * current / total) if total > 0 else 0
    bar = '#' * filled + '.' * (bar_width - filled)
    
    print(f"\r{prefix}: {Colors.CYAN}{bar}{Colors.RESET} {current}/{total} ({percent:.0f}%)", end='', flush=True)
    
    if current == total:
        print()  # New line when complete


# Self-test
if __name__ == "__main__":
    print_header("UI Module Test", "Testing all UI components")
    
    print_status("Spotify", True, "user@example.com")
    print_status("YouTube Music", False)
    print()
    
    print_success("This is a success message")
    print_error("This is an error message")
    print_warning("This is a warning message")
    print_info("This is an info message")
    print()
    
    print_box(["Line 1", "Line 2 - longer", "Line 3"], "Sample Box")
    print()
    
    print_menu(["Option One", "Option Two", "Option Three"])
    
    print("\nProgress bar demo:")
    import time
    for i in range(1, 11):
        print_progress(i, 10, "Loading")
        time.sleep(0.1)
    
    print("\n[OK] All UI tests complete!")
