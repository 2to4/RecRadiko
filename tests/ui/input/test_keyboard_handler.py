"""
Test for KeyboardHandler class

Tests keyboard input handling with arrow key navigation support.
Following TDD approach: tests first, then implementation.
"""

import pytest
from unittest.mock import Mock, patch, call
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from src.ui.input.keyboard_handler import KeyboardHandler


class TestKeyboardHandler:
    """KeyboardHandler unit tests"""
    
    @pytest.fixture
    def keyboard_handler(self):
        """Create KeyboardHandler instance for testing"""
        return KeyboardHandler()
        
    def test_keyboard_handler_initialization(self, keyboard_handler):
        """Test KeyboardHandler initialization"""
        assert keyboard_handler is not None
        assert hasattr(keyboard_handler, 'get_key')
        assert hasattr(keyboard_handler, 'is_arrow_key')
        assert hasattr(keyboard_handler, 'is_special_key')
        
    def test_map_windows_extended_key_arrow_up(self, keyboard_handler):
        """Test Windows extended key mapping for UP arrow"""
        result = keyboard_handler._map_windows_extended_key(b'H')
        assert result == 'UP'
        
    def test_map_windows_extended_key_arrow_down(self, keyboard_handler):
        """Test Windows extended key mapping for DOWN arrow"""
        result = keyboard_handler._map_windows_extended_key(b'P')
        assert result == 'DOWN'
        
    def test_map_regular_key_enter(self, keyboard_handler):
        """Test regular key mapping for Enter"""
        result = keyboard_handler._map_regular_key(b'\r')
        assert result == 'ENTER'
        
    def test_map_regular_key_escape(self, keyboard_handler):
        """Test regular key mapping for Escape"""
        result = keyboard_handler._map_regular_key(b'\x1b')
        assert result == 'ESCAPE'
            
    def test_map_unix_escape_sequence_arrow_up(self, keyboard_handler):
        """Test Unix escape sequence mapping for UP arrow"""
        result = keyboard_handler._map_unix_escape_sequence('A')
        assert result == 'UP'
        
    def test_map_unix_escape_sequence_arrow_down(self, keyboard_handler):
        """Test Unix escape sequence mapping for DOWN arrow"""
        result = keyboard_handler._map_unix_escape_sequence('B')
        assert result == 'DOWN'
        
    def test_is_arrow_key_true(self, keyboard_handler):
        """Test arrow key detection returns True for arrow keys"""
        assert keyboard_handler.is_arrow_key('UP') == True
        assert keyboard_handler.is_arrow_key('DOWN') == True
        assert keyboard_handler.is_arrow_key('LEFT') == True
        assert keyboard_handler.is_arrow_key('RIGHT') == True
        
    def test_is_arrow_key_false(self, keyboard_handler):
        """Test arrow key detection returns False for non-arrow keys"""
        assert keyboard_handler.is_arrow_key('ENTER') == False
        assert keyboard_handler.is_arrow_key('ESCAPE') == False
        assert keyboard_handler.is_arrow_key('a') == False
        assert keyboard_handler.is_arrow_key('1') == False
        
    def test_is_special_key_true(self, keyboard_handler):
        """Test special key detection returns True for special keys"""
        assert keyboard_handler.is_special_key('ENTER') == True
        assert keyboard_handler.is_special_key('ESCAPE') == True
        assert keyboard_handler.is_special_key('PAGE_UP') == True
        assert keyboard_handler.is_special_key('PAGE_DOWN') == True
        
    def test_is_special_key_false(self, keyboard_handler):
        """Test special key detection returns False for regular keys"""
        assert keyboard_handler.is_special_key('a') == False
        assert keyboard_handler.is_special_key('1') == False
        assert keyboard_handler.is_special_key('q') == False