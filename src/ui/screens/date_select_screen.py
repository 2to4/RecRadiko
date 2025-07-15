"""
Date Selection Screen for RecRadiko Keyboard Navigation UI

Provides date selection interface with keyboard navigation for RecRadiko timefree recording.
Handles timefree period validation and date formatting for user-friendly display.

Based on UI_SPECIFICATION.md:
- Date selection with timefree period support (7 days)
- Keyboard navigation for date selection
- Relative date descriptions (今日, 昨日, etc.)
- Integration with timefree recording workflow
"""

import logging
from datetime import datetime, timedelta, date
from typing import Optional, List, Dict, Any
import re
from src.ui.screen_base import ScreenBase


class DateSelectScreen(ScreenBase):
    """
    Date selection screen for RecRadiko timefree recording
    
    Provides date selection interface with:
    - Timefree period validation (7 days back from today)
    - User-friendly date formatting with relative descriptions
    - Keyboard navigation for date selection
    - Integration with station selection workflow
    """
    
    def __init__(self):
        """Initialize date selection screen"""
        super().__init__()
        self.set_title("録音日付選択")
        self.selected_station: Optional[Dict[str, Any]] = None
        self.available_dates: List[date] = []
        
    def set_station(self, station: Dict[str, Any]) -> None:
        """
        Set selected station and update title
        
        Args:
            station: Selected station dictionary
        """
        self.selected_station = station
        self.set_title(f"録音日付選択 - {station['name']}")
        self.available_dates = self.calculate_available_dates()
        
    def calculate_available_dates(self) -> List[date]:
        """
        Calculate available dates for timefree recording
        
        Returns:
            List of available dates (7 days including today)
        """
        today = datetime.now().date()
        dates = []
        
        # Include today and 6 days back (total 7 days)
        for i in range(7):
            target_date = today - timedelta(days=i)
            dates.append(target_date)
            
        return dates  # Return in descending order (newest first)
        
    def is_date_available(self, target_date: date) -> bool:
        """
        Check if date is available for timefree recording
        
        Args:
            target_date: Date to check
            
        Returns:
            True if date is within timefree period, False otherwise
        """
        today = datetime.now().date()
        
        # Check if date is within the last 7 days (including today)
        if target_date > today:
            return False  # Future dates not available
            
        days_ago = (today - target_date).days
        return days_ago <= 6  # 0-6 days ago (7 days total)
        
    def format_date_for_display(self, target_date: date) -> str:
        """
        Format date for user-friendly display
        
        Args:
            target_date: Date to format
            
        Returns:
            Formatted date string with relative description
        """
        # Japanese day of week mapping
        weekdays_jp = ['月', '火', '水', '木', '金', '土', '日']
        weekday_jp = weekdays_jp[target_date.weekday()]
        
        # Basic format
        date_str = target_date.strftime('%Y-%m-%d')
        relative_desc = self.get_relative_date_description(target_date)
        
        return f"{date_str} ({weekday_jp}) - {relative_desc}"
        
    def get_relative_date_description(self, target_date: date) -> str:
        """
        Get relative description for date (今日, 昨日, etc.)
        
        Args:
            target_date: Date to describe
            
        Returns:
            Relative description string
        """
        today = datetime.now().date()
        days_diff = (today - target_date).days
        
        if days_diff == 0:
            return "今日"
        elif days_diff == 1:
            return "昨日"
        elif days_diff == 2:
            return "一昨日"
        else:
            return f"{days_diff}日前"
            
    def display_content(self) -> None:
        """Display date selection content"""
        if not self.selected_station:
            self.ui_service.display_error(
                "放送局が選択されていません。\n"
                "メインメニューから録音を開始してください。"
            )
            self.ui_service.keyboard_handler.get_key()
            return
            
        print(f"\n放送局: {self.selected_station['name']}")
        print("=" * 40)
        print("\nタイムフリー録音可能期間: 過去7日間")
        print("録音したい日付を選択してください:\n")
        
        # Format dates for display
        date_options = [self.format_date_for_display(d) for d in self.available_dates]
        
        self.ui_service.set_menu_items(date_options)
        self.ui_service.display_menu_with_highlight()
        
    def run_date_selection_loop(self) -> Optional[date]:
        """
        Run date selection interaction loop
        
        Returns:
            Selected date, or None if cancelled
        """
        if not self.selected_station:
            return None
            
        while True:
            self.show()
            
            selected_display = self.ui_service.get_user_selection()
            
            if selected_display is None:
                # User cancelled (Escape key)
                return None
                
            # Parse date from display string
            selected_date = self.parse_date_from_display_string(selected_display)
            
            if selected_date and self.validate_selected_date(selected_date):
                return selected_date
            else:
                self.ui_service.display_error(f"無効な日付です: {selected_display}")
                
    def parse_date_from_display_string(self, display_string: str) -> Optional[date]:
        """
        Parse date from formatted display string
        
        Args:
            display_string: Formatted date display string
            
        Returns:
            Parsed date or None if parsing failed
        """
        try:
            # Extract date part (YYYY-MM-DD) from display string
            match = re.match(r'^(\d{4}-\d{2}-\d{2})', display_string)
            if match:
                date_str = match.group(1)
                return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
            
        return None
        
    def validate_selected_date(self, selected_date: date) -> bool:
        """
        Validate selected date
        
        Args:
            selected_date: Date to validate
            
        Returns:
            True if date is valid for recording, False otherwise
        """
        return self.is_date_available(selected_date)
        
    def refresh_available_dates(self) -> None:
        """Refresh available dates list"""
        self.available_dates = self.calculate_available_dates()
        self.logger.debug("Available dates refreshed")
        
    def show_date_info(self, target_date: date) -> None:
        """
        Show detailed information about selected date
        
        Args:
            target_date: Date to show info for
        """
        weekdays_jp = ['月', '火', '水', '木', '金', '土', '日']
        weekday_jp = weekdays_jp[target_date.weekday()]
        
        print(f"\n日付情報")
        print("=" * 20)
        print(f"日付: {target_date.strftime('%Y年%m月%d日')} ({weekday_jp}曜日)")
        print(f"相対表記: {self.get_relative_date_description(target_date)}")
        print(f"タイムフリー録音: {'可能' if self.is_date_available(target_date) else '不可'}")
        
        if self.is_date_available(target_date):
            print("\nこの日付の番組を録音できます。")
        else:
            print("\nこの日付はタイムフリー期間外です。")
            
        print("\n任意のキーを押して続行...")
        self.ui_service.keyboard_handler.get_key()
        
    def get_timefree_period_info(self) -> str:
        """
        Get timefree period information
        
        Returns:
            Information string about timefree period
        """
        return (
            "タイムフリー録音について:\n"
            "・過去7日間（今日を含む）の番組が録音可能\n"
            "・8日以前の番組は録音できません\n"
            "・未来の番組は録音できません"
        )
        
    def handle_shortcut_key(self, key: str) -> bool:
        """
        Handle shortcut keys
        
        Args:
            key: Key pressed by user
            
        Returns:
            True if key was handled, False otherwise
        """
        if key in ('i', 'I'):
            # Show info for current selection
            current_display = self.ui_service.get_current_item()
            if current_display:
                current_date = self.parse_date_from_display_string(current_display)
                if current_date:
                    self.show_date_info(current_date)
            return True
            
        elif key in ('r', 'R'):
            # Refresh dates
            self.refresh_available_dates()
            return True
            
        elif key in ('h', 'H'):
            # Show help
            print(f"\n{self.get_timefree_period_info()}")
            print("\nキーボード操作:")
            print("  ↑/↓: 日付選択")
            print("  Enter: 選択確定")
            print("  Esc: 戻る")
            print("  I: 日付詳細情報")
            print("  R: 日付リスト更新")
            print("  H: このヘルプ")
            print("\n任意のキーを押して続行...")
            self.ui_service.keyboard_handler.get_key()
            return True
            
        return False
        
    def get_selected_station_name(self) -> str:
        """
        Get selected station name for display
        
        Returns:
            Station name or "未選択" if not set
        """
        if self.selected_station:
            return self.selected_station['name']
        return "未選択"
        
    def get_date_count(self) -> int:
        """
        Get number of available dates
        
        Returns:
            Number of available dates
        """
        return len(self.available_dates)
        
    def has_valid_station(self) -> bool:
        """
        Check if valid station is selected
        
        Returns:
            True if station is selected, False otherwise
        """
        return self.selected_station is not None
        
    def get_date_range_description(self) -> str:
        """
        Get description of available date range
        
        Returns:
            Description string of date range
        """
        if not self.available_dates:
            return "利用可能な日付がありません"
            
        oldest = min(self.available_dates)
        newest = max(self.available_dates)
        
        return f"{oldest.strftime('%Y-%m-%d')} ～ {newest.strftime('%Y-%m-%d')}"
        
    def is_today_available(self) -> bool:
        """
        Check if today is available for recording
        
        Returns:
            True if today is in available dates, False otherwise
        """
        today = datetime.now().date()
        return today in self.available_dates