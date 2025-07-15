"""
Keyboard Input Handler for RecRadiko UI

Provides cross-platform keyboard input handling with arrow key navigation support.
Supports Windows (msvcrt) and Unix/Linux (termios + tty) platforms.

Design based on DETAILED_DESIGN.md specifications:
- Cross-platform key input detection
- Arrow key navigation (UP, DOWN, LEFT, RIGHT)
- Special key handling (ENTER, ESCAPE, PAGE_UP, PAGE_DOWN)
- ANSI escape sequence processing for Unix/Linux
"""

import sys
import logging
from typing import Optional


class KeyboardHandler:
    """
    Cross-platform keyboard input handler
    
    Provides unified interface for keyboard input across Windows and Unix/Linux platforms.
    Handles arrow keys, special keys, and regular character input.
    """
    
    def __init__(self):
        """Initialize keyboard handler"""
        self.logger = logging.getLogger(__name__)
        self._setup_platform_modules()
        
    def _setup_platform_modules(self):
        """Setup platform-specific modules"""
        self.is_windows = sys.platform.startswith('win')
        
        if self.is_windows:
            try:
                import msvcrt
                self.msvcrt = msvcrt
            except ImportError:
                self.logger.warning("msvcrt module not available - testing environment")
                self.msvcrt = None
        else:
            try:
                import tty
                import termios
                self.tty = tty
                self.termios = termios
            except ImportError:
                self.logger.warning("tty/termios modules not available - testing environment")
                self.tty = None
                self.termios = None
                
    def get_key(self) -> str:
        """
        Get single keypress from user
        
        Returns:
            str: Key identifier ('UP', 'DOWN', 'ENTER', 'ESCAPE', or character)
        """
        if self.is_windows:
            return self._get_key_windows()
        else:
            return self._get_key_unix()
            
    def _get_key_windows(self) -> str:
        """Get key input on Windows platform using msvcrt"""
        key = self.msvcrt.getch()
        
        # Handle special keys (arrow keys, function keys)
        if key == b'\xe0':  # Extended key prefix
            extended_key = self.msvcrt.getch()
            return self._map_windows_extended_key(extended_key)
        elif key == b'\x00':  # Function key prefix
            function_key = self.msvcrt.getch()
            return self._map_windows_function_key(function_key)
        else:
            # Regular key
            return self._map_regular_key(key)
            
    def _get_key_unix(self) -> str:
        """Get key input on Unix/Linux platform using termios"""
        # Save terminal settings
        fd = sys.stdin.fileno()
        old_settings = self.termios.tcgetattr(fd)
        
        try:
            # Set terminal to raw mode for single character input
            self.tty.setraw(fd)
            
            # Read first character
            char = sys.stdin.read(1)
            
            # Handle escape sequences (arrow keys, special keys)
            if char == '\x1b':  # ESC character
                # Try to read escape sequence
                try:
                    # Set short timeout for escape sequence
                    char2 = sys.stdin.read(1)
                    if char2 == '[':
                        char3 = sys.stdin.read(1)
                        return self._map_unix_escape_sequence(char3)
                    else:
                        # Just ESC key
                        return 'ESCAPE'
                except:
                    return 'ESCAPE'
            else:
                return self._map_regular_key(char.encode('utf-8'))
                
        finally:
            # Restore terminal settings
            self.termios.tcsetattr(fd, self.termios.TCSADRAIN, old_settings)
            
    def _map_windows_extended_key(self, key: bytes) -> str:
        """Map Windows extended key codes to key names"""
        extended_key_map = {
            b'H': 'UP',      # Up arrow
            b'P': 'DOWN',    # Down arrow
            b'K': 'LEFT',    # Left arrow
            b'M': 'RIGHT',   # Right arrow
            b'I': 'PAGE_UP', # Page Up
            b'Q': 'PAGE_DOWN'# Page Down
        }
        return extended_key_map.get(key, f'EXTENDED_{ord(key)}')
        
    def _map_windows_function_key(self, key: bytes) -> str:
        """Map Windows function key codes to key names"""
        # F1-F12 and other function keys
        return f'F{ord(key) - 58}' if 59 <= ord(key) <= 68 else f'FUNCTION_{ord(key)}'
        
    def _map_unix_escape_sequence(self, char: str) -> str:
        """Map Unix escape sequences to key names"""
        escape_map = {
            'A': 'UP',       # Up arrow
            'B': 'DOWN',     # Down arrow
            'C': 'RIGHT',    # Right arrow
            'D': 'LEFT',     # Left arrow
            '5': 'PAGE_UP',  # Page Up (followed by ~)
            '6': 'PAGE_DOWN' # Page Down (followed by ~)
        }
        return escape_map.get(char, f'ESCAPE_SEQ_{char}')
        
    def _map_regular_key(self, key: bytes) -> str:
        """Map regular key codes to key names or characters"""
        if isinstance(key, str):
            key = key.encode('utf-8')
            
        key_code = key[0] if key else 0
        
        # Common special keys
        if key_code == 13 or key_code == 10:  # Enter (CR or LF)
            return 'ENTER'
        elif key_code == 27:  # Escape
            return 'ESCAPE'
        elif key_code == 9:   # Tab
            return 'TAB'
        elif key_code == 8 or key_code == 127:  # Backspace
            return 'BACKSPACE'
        elif key_code == 32:  # Space
            return 'SPACE'
        elif 32 <= key_code <= 126:  # Printable ASCII
            return chr(key_code)
        else:
            # Non-printable character
            return f'CHAR_{key_code}'
            
    def is_arrow_key(self, key: str) -> bool:
        """
        Check if key is an arrow key
        
        Args:
            key: Key identifier
            
        Returns:
            bool: True if key is arrow key (UP, DOWN, LEFT, RIGHT)
        """
        return key in ('UP', 'DOWN', 'LEFT', 'RIGHT')
        
    def is_special_key(self, key: str) -> bool:
        """
        Check if key is a special key (non-printable control key)
        
        Args:
            key: Key identifier
            
        Returns:
            bool: True if key is special key
        """
        special_keys = {
            'ENTER', 'ESCAPE', 'TAB', 'BACKSPACE', 'SPACE',
            'PAGE_UP', 'PAGE_DOWN', 'HOME', 'END', 'INSERT', 'DELETE'
        }
        return key in special_keys or key.startswith(('F', 'EXTENDED_', 'FUNCTION_', 'ESCAPE_SEQ_', 'CHAR_'))
        
    def is_printable_key(self, key: str) -> bool:
        """
        Check if key represents a printable character
        
        Args:
            key: Key identifier
            
        Returns:
            bool: True if key is printable character
        """
        return len(key) == 1 and key.isprintable() and not self.is_special_key(key)