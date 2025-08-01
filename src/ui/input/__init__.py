# Keyboard Input Module for RecRadiko UI

"""
Keyboard Input Handling Module

Provides cross-platform keyboard input handling with arrow key navigation support.
Supports Windows (msvcrt) and Unix/Linux (termios + tty) platforms.
"""

from typing import List
from .keyboard_handler import KeyboardHandler

__all__: List[str] = ['KeyboardHandler']