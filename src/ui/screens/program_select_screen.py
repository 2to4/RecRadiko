"""
Program Selection Screen for RecRadiko Keyboard Navigation UI

Provides program selection interface with keyboard navigation for RecRadiko timefree recording.
Handles program list display, pagination, and program information viewing.

Based on UI_SPECIFICATION.md:
- Program selection with keyboard navigation
- Pagination support for large program lists
- Program information display
- Integration with timefree recording workflow
"""

import logging
from datetime import date
from typing import Optional, List, Dict, Any
import math
from src.ui.screen_base import ScreenBase
from src.program_history import ProgramHistoryManager


class ProgramSelectScreen(ScreenBase):
    """
    Program selection screen for RecRadiko timefree recording
    
    Provides program selection interface with:
    - Program list display with pagination
    - Keyboard navigation for program selection
    - Program information viewing
    - Integration with timefree recording workflow
    """
    
    def __init__(self):
        """Initialize program selection screen"""
        super().__init__()
        self.set_title("番組選択")
        self.selected_station: Optional[Dict[str, Any]] = None
        self.selected_date: Optional[date] = None
        self.programs: List[Dict[str, Any]] = []
        self.current_page: int = 0
        self.items_per_page: int = 10
        
    def set_station_and_date(self, station: Dict[str, Any], target_date: date) -> None:
        """
        Set selected station and date, update title
        
        Args:
            station: Selected station dictionary
            target_date: Selected date for program list
        """
        self.selected_station = station
        self.selected_date = target_date
        date_str = target_date.strftime('%Y-%m-%d')
        self.set_title(f"番組選択 - {station['name']} ({date_str})")
        
    def load_programs(self) -> bool:
        """
        Load programs for selected station and date
        
        Returns:
            True if programs loaded successfully, False otherwise
        """
        if not self.selected_station or not self.selected_date:
            self.logger.error("Station or date not set for program loading")
            return False
            
        try:
            self.display_loading_message()
            self.programs = self._fetch_programs_from_api(
                self.selected_station["id"], 
                self.selected_date
            )
            
            if not self.programs:
                self.logger.warning(
                    f"No programs found for {self.selected_station['id']} on {self.selected_date}"
                )
                return False
                
            self.logger.info(
                f"Loaded {len(self.programs)} programs for {self.selected_station['id']} on {self.selected_date}"
            )
            self.current_page = 0  # Reset to first page
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load programs: {e}")
            return False
            
    def _fetch_programs_from_api(self, station_id: str, target_date: date) -> List[Dict[str, Any]]:
        """
        Fetch programs from RecRadiko API
        
        Args:
            station_id: Station identifier
            target_date: Target date for programs
            
        Returns:
            List of program dictionaries
        """
        program_history_manager = ProgramHistoryManager()
        return program_history_manager.get_programs_for_date(station_id, target_date)
        
    def display_content(self) -> None:
        """Display program selection content"""
        if not self.selected_station or not self.selected_date:
            self.ui_service.display_error(
                "放送局または日付が選択されていません。\\n"
                "メインメニューから録音を開始してください。"
            )
            self.ui_service.keyboard_handler.get_key()
            return
            
        if not self.programs:
            self.display_no_programs_message()
            return
            
        station_name = self.selected_station["name"]
        date_str = self.selected_date.strftime('%Y年%m月%d日')
        
        print(f"\\n放送局: {station_name}")
        print(f"日付: {date_str}")
        print(f"番組数: {len(self.programs)}番組")
        print("=" * 40)
        
        # Display pagination info if needed
        if self.get_total_pages() > 1:
            print(f"\\n{self.get_pagination_info()}")
            
        print("\\n番組を選択してください:\\n")
        
        # Get current page programs and format for display
        page_programs = self.get_current_page_programs()
        program_displays = [self.format_program_for_display(prog) for prog in page_programs]
        
        self.ui_service.set_menu_items(program_displays)
        self.ui_service.display_menu_with_highlight()
        
        # Display pagination controls if needed
        if self.get_total_pages() > 1:
            print("\\nページ操作: N(次のページ) P(前のページ)")
            
    def run_program_selection_loop(self) -> Optional[Dict[str, Any]]:
        """
        Run program selection interaction loop
        
        Returns:
            Selected program dictionary, or None if cancelled
        """
        if not self.selected_station or not self.selected_date:
            return None
            
        while True:
            self.show()
            
            selected_display = self.ui_service.get_user_selection()
            
            if selected_display is None:
                # User cancelled (Escape key)
                return None
                
            # Find selected program
            selected_program = self.get_program_by_display_text(selected_display)
            
            if selected_program:
                return selected_program
            else:
                self.ui_service.display_error(f"番組が見つかりません: {selected_display}")
                
    def format_program_for_display(self, program: Dict[str, Any]) -> str:
        """
        Format program for display
        
        Args:
            program: Program dictionary
            
        Returns:
            Formatted display string
        """
        start_time = program.get("start_time", "")
        end_time = program.get("end_time", "")
        title = program.get("title", "")
        
        return f"{start_time}-{end_time} {title}"
        
    def get_program_by_display_text(self, display_text: str) -> Optional[Dict[str, Any]]:
        """
        Get program by display text
        
        Args:
            display_text: Program display text
            
        Returns:
            Program dictionary or None if not found
        """
        page_programs = self.get_current_page_programs()
        
        for program in page_programs:
            if self.format_program_for_display(program) == display_text:
                return program
        return None
        
    def get_current_page_programs(self) -> List[Dict[str, Any]]:
        """
        Get programs for current page
        
        Returns:
            List of programs for current page
        """
        start_idx = self.current_page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        return self.programs[start_idx:end_idx]
        
    def get_total_pages(self) -> int:
        """
        Get total number of pages
        
        Returns:
            Total number of pages
        """
        if not self.programs:
            return 0
        return math.ceil(len(self.programs) / self.items_per_page)
        
    def next_page(self) -> bool:
        """
        Move to next page
        
        Returns:
            True if moved to next page, False if already at last page
        """
        if self.current_page < self.get_total_pages() - 1:
            self.current_page += 1
            return True
        return False
        
    def previous_page(self) -> bool:
        """
        Move to previous page
        
        Returns:
            True if moved to previous page, False if already at first page
        """
        if self.current_page > 0:
            self.current_page -= 1
            return True
        return False
        
    def get_pagination_info(self) -> str:
        """
        Get pagination information string
        
        Returns:
            Pagination info string
        """
        if not self.programs:
            return "番組なし"
            
        total_pages = self.get_total_pages()
        current_page_num = self.current_page + 1
        
        start_item = self.current_page * self.items_per_page + 1
        end_item = min((self.current_page + 1) * self.items_per_page, len(self.programs))
        
        return f"ページ {current_page_num}/{total_pages} ({start_item}-{end_item}/{len(self.programs)}件)"
        
    def show_program_info(self, program: Dict[str, Any]) -> None:
        """
        Show detailed program information
        
        Args:
            program: Program dictionary
        """
        print(f"\\n番組詳細情報")
        print("=" * 20)
        print(f"番組名: {program.get('title', '')}")
        print(f"放送時間: {program.get('start_time', '')}-{program.get('end_time', '')}")
        
        if 'performer' in program and program['performer']:
            print(f"出演者: {program['performer']}")
            
        if 'description' in program and program['description']:
            print(f"番組内容: {program['description']}")
            
        print("\\n任意のキーを押して続行...")
        self.ui_service.keyboard_handler.get_key()
        
    def handle_shortcut_key(self, key: str) -> bool:
        """
        Handle shortcut keys
        
        Args:
            key: Key pressed by user
            
        Returns:
            True if key was handled, False otherwise
        """
        if key in ('i', 'I'):
            # Show program info for current selection
            current_display = self.ui_service.get_current_item()
            if current_display:
                program = self.get_program_by_display_text(current_display)
                if program:
                    self.show_program_info(program)
            return True
            
        elif key in ('n', 'N'):
            # Next page
            if self.next_page():
                self.ui_service.display_status("次のページに移動しました")
            else:
                self.ui_service.display_status("最後のページです")
            return True
            
        elif key in ('p', 'P'):
            # Previous page
            if self.previous_page():
                self.ui_service.display_status("前のページに移動しました")
            else:
                self.ui_service.display_status("最初のページです")
            return True
            
        elif key in ('r', 'R'):
            # Refresh programs
            success = self.refresh_programs()
            if success:
                self.ui_service.display_status("番組リストを更新しました")
            else:
                self.ui_service.display_error("番組リストの更新に失敗しました")
            return True
            
        elif key in ('h', 'H'):
            # Show help
            self.show_help()
            return True
            
        return False
        
    def show_help(self) -> None:
        """Show help information"""
        print("\\n番組選択ヘルプ")
        print("=" * 20)
        print("キーボード操作:")
        print("  ↑/↓: 番組選択")
        print("  Enter: 選択確定")
        print("  Esc: 戻る")
        print("  I: 番組詳細情報")
        print("  N: 次のページ")
        print("  P: 前のページ")
        print("  R: 番組リスト更新")
        print("  H: このヘルプ")
        print("\\n任意のキーを押して続行...")
        self.ui_service.keyboard_handler.get_key()
        
    def display_loading_message(self) -> None:
        """Display loading message"""
        print("\\n番組情報を読み込み中...")
        print("しばらくお待ちください...")
        
    def display_no_programs_message(self) -> None:
        """Display no programs available message"""
        self.ui_service.display_error(
            "この日付・放送局では番組が見つかりませんでした。\\n"
            "日付や放送局を変更してください。"
        )
        self.ui_service.keyboard_handler.get_key()
        
    def validate_program_data(self, program: Dict[str, Any]) -> bool:
        """
        Validate program data
        
        Args:
            program: Program dictionary to validate
            
        Returns:
            True if program data is valid, False otherwise
        """
        required_fields = ['title', 'start_time', 'end_time']
        return all(field in program and program[field] for field in required_fields)
        
    def get_program_count(self) -> int:
        """
        Get number of loaded programs
        
        Returns:
            Number of programs
        """
        return len(self.programs)
        
    def has_programs(self) -> bool:
        """
        Check if programs are loaded
        
        Returns:
            True if programs are loaded, False otherwise
        """
        return len(self.programs) > 0
        
    def refresh_programs(self) -> bool:
        """
        Refresh program list for current station and date
        
        Returns:
            True if refresh successful, False otherwise
        """
        if not self.selected_station or not self.selected_date:
            return False
            
        return self.load_programs()
        
    def get_current_selection_info(self) -> str:
        """
        Get current selection information for display
        
        Returns:
            Current selection info string
        """
        if not self.selected_station or not self.selected_date:
            return "選択情報なし"
            
        station_name = self.selected_station["name"]
        date_str = self.selected_date.strftime('%Y-%m-%d')
        program_count = len(self.programs)
        
        return f"{station_name} / {date_str} / {program_count}番組"
        
    def filter_programs_by_keyword(self, keyword: str) -> List[Dict[str, Any]]:
        """
        Filter programs by keyword
        
        Args:
            keyword: Search keyword
            
        Returns:
            List of matching programs
        """
        if not keyword:
            return self.programs
            
        keyword_lower = keyword.lower()
        return [
            program for program in self.programs
            if keyword_lower in program.get('title', '').lower() or
               keyword_lower in program.get('performer', '').lower() or
               keyword_lower in program.get('description', '').lower()
        ]
        
    def get_program_time_range(self) -> str:
        """
        Get time range of all programs
        
        Returns:
            Time range description string
        """
        if not self.programs:
            return "番組なし"
            
        start_times = [prog.get('start_time', '') for prog in self.programs if prog.get('start_time')]
        end_times = [prog.get('end_time', '') for prog in self.programs if prog.get('end_time')]
        
        if start_times and end_times:
            earliest = min(start_times)
            latest = max(end_times)
            return f"{earliest} ～ {latest}"
        else:
            return "時間情報なし"