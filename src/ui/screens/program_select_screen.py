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
from datetime import date, timedelta
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
        self.items_per_page: int = 20  # 20番組ずつ表示に増加
        self.show_all_programs: bool = False  # 全番組表示フラグ
        
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
            error_msg = f"Station or date not set for program loading - station: {self.selected_station}, date: {self.selected_date}"
            self.logger.error(error_msg)
            self.ui_service.display_error("放送局または日付が正しく設定されていません。")
            return False
            
        try:
            # 詳細ログ出力
            self.logger.info(f"Loading programs - Station: {self.selected_station['name']} ({self.selected_station['id']}), Date: {self.selected_date} (type: {type(self.selected_date)})")
            
            self.display_loading_message()
            self.programs = self._fetch_programs_from_api(
                self.selected_station["id"], 
                self.selected_date
            )
            
            if not self.programs:
                error_msg = f"No programs found for {self.selected_station['id']} on {self.selected_date}"
                self.logger.warning(error_msg)
                self.ui_service.display_error(
                    f"番組が見つかりませんでした。\n"
                    f"放送局: {self.selected_station['name']}\n"
                    f"日付: {self.selected_date}\n"
                    f"別の日付を選択してください。"
                )
                return False
                
            self.logger.info(
                f"Successfully loaded {len(self.programs)} programs for {self.selected_station['id']} on {self.selected_date}"
            )
            self.current_page = 0  # Reset to first page
            return True
            
        except Exception as e:
            error_msg = f"Failed to load programs: {e}"
            self.logger.error(error_msg, exc_info=True)
            self.ui_service.display_error(
                f"番組の読み込みでエラーが発生しました：\n{str(e)}\n"
                f"ネットワーク接続またはサーバーの状態を確認してください。"
            )
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
        try:
            self.logger.debug(f"Initializing ProgramHistoryManager for station_id: {station_id}, target_date: {target_date}")
            program_history_manager = ProgramHistoryManager()
            
            # Convert date to string format (YYYY-MM-DD)
            date_str = target_date.strftime('%Y-%m-%d')
            self.logger.debug(f"Converted date to string: {date_str}")
            
            # Get ProgramInfo objects from API for the specified date
            self.logger.info(f"Calling get_programs_by_date for station {station_id} on {date_str}")
            program_infos = program_history_manager.get_programs_by_date(date_str, station_id)
            
            # Also get programs from the next day for midnight programs
            next_date = target_date + timedelta(days=1)
            next_date_str = next_date.strftime('%Y-%m-%d')
            self.logger.info(f"Calling get_programs_by_date for station {station_id} on {next_date_str} (for midnight programs)")
            
            try:
                next_day_programs = program_history_manager.get_programs_by_date(next_date_str, station_id)
                # Filter midnight programs (0:00-5:59) from next day
                midnight_programs = [p for p in next_day_programs if p.start_time.hour < 6]
                self.logger.info(f"Found {len(midnight_programs)} midnight programs from next day")
                
                # Add midnight programs to the main list
                program_infos.extend(midnight_programs)
                
            except Exception as e:
                self.logger.warning(f"Could not fetch next day programs for midnight shows: {e}")
            
            self.logger.info(f"API returned {len(program_infos)} program objects total")
            
            if not program_infos:
                self.logger.warning(f"No program info objects returned from API for {station_id} on {date_str}")
                return []
            
            # Convert ProgramInfo objects to dictionary format for UI
            programs = []
            for i, prog in enumerate(program_infos):
                try:
                    # For midnight programs, show them as belonging to the previous day
                    if prog.is_midnight_program:
                        # This is a midnight program, show it with a special marker
                        display_title = f"🌙 {prog.title}"
                        display_date = prog.display_date
                        self.logger.debug(f"Midnight program: {prog.title} on {display_date}")
                    else:
                        display_title = prog.title
                        display_date = prog.start_time.date().strftime('%Y-%m-%d')
                    
                    program_dict = {
                        'id': prog.program_id,
                        'title': display_title,
                        'start_time': prog.start_time.strftime('%H:%M'),
                        'end_time': prog.end_time.strftime('%H:%M'),
                        'performer': getattr(prog, 'performers', []),
                        'description': getattr(prog, 'description', ''),
                        'station_id': prog.station_id,
                        'station_name': prog.station_name,
                        'display_date': display_date,
                        'is_midnight': prog.is_midnight_program
                    }
                    programs.append(program_dict)
                    
                except Exception as prog_e:
                    self.logger.error(f"Error converting program {i} to dict: {prog_e}")
                    continue
            
            # Sort programs by start time for better display
            programs.sort(key=lambda x: x['start_time'])
            
            self.logger.info(f"Successfully converted {len(programs)} programs to dictionary format")
            return programs
            
        except Exception as e:
            self.logger.error(f"Error in _fetch_programs_from_api: {e}", exc_info=True)
            raise  # Re-raise the exception to be handled by calling method
        
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
        total_programs = len(self.programs)
        
        print(f"\\n放送局: {station_name}")
        print(f"日付: {date_str}")
        print(f"番組数: {total_programs}番組")
        
        # 番組数が少ない場合（30番組以下）は自動的に全表示
        if total_programs <= 30:
            self.show_all_programs = True
            
        print("=" * 40)
        
        # 全番組表示またはページング表示
        if self.show_all_programs:
            print("\\n📺 全番組表示")
            print("\\n番組を選択してください:\\n")
            
            # 全番組を表示
            program_displays = [self.format_program_for_display(prog) for prog in self.programs]
            
            # ページ表示モード切り替えオプションを追加（30番組以上の場合）
            if total_programs > 30:
                program_displays.append("═══════════════════════")
                program_displays.append("📄 ページ表示に切り替え")
            
            self.ui_service.set_menu_items(program_displays)
            self.ui_service.display_menu_with_highlight()
            
            print(f"\\n💡 操作方法: ↑↓キーで選択、Enterで確定")
                
        else:
            # ページング表示
            total_pages = self.get_total_pages()
            print(f"\\n📄 ページ表示 ({self.get_pagination_info()})")
            print("\\n番組を選択してください:\\n")
            
            # 現在のページの番組を表示
            page_programs = self.get_current_page_programs()
            program_displays = [self.format_program_for_display(prog) for prog in page_programs]
            
            # ページ移動オプションを番組リストに追加
            if total_pages > 1:
                program_displays.append("═══════════════════════")
                
                # 前のページオプション（最初のページでなければ表示）
                if self.current_page > 0:
                    program_displays.append("⬅️ 前のページ")
                
                # 次のページオプション（最後のページでなければ表示）
                if self.current_page < total_pages - 1:
                    program_displays.append("➡️ 次のページ")
            
            # 全表示切り替えオプションを追加
            program_displays.append("═══════════════════════")
            program_displays.append("📺 全番組表示に切り替え")
            
            self.ui_service.set_menu_items(program_displays)
            self.ui_service.display_menu_with_highlight()
            
            print(f"\\n💡 操作方法: ↑↓キーで選択、Enterで確定")
            
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
            
            # メニュー選択を取得
            selected_display = self.ui_service.get_user_selection()
            
            if selected_display is None:
                # Escapeキーまたはキャンセル
                return None
            
            # 特殊なメニュー項目かどうかをチェック
            if selected_display == "📄 ページ表示に切り替え":
                # 全表示からページ表示に切り替え
                self.show_all_programs = False
                self.ui_service.display_status("ページ表示に切り替えました")
                continue
                
            elif selected_display == "📺 全番組表示に切り替え":
                # ページ表示から全表示に切り替え
                self.show_all_programs = True
                self.ui_service.display_status("全番組表示に切り替えました")
                continue
                
            elif selected_display == "➡️ 次のページ":
                # 次のページに移動
                if self.next_page():
                    self.ui_service.display_status(f"ページ {self.current_page + 1} に移動しました")
                else:
                    self.ui_service.display_status("最後のページです")
                continue
                
            elif selected_display == "⬅️ 前のページ":
                # 前のページに移動
                if self.previous_page():
                    self.ui_service.display_status(f"ページ {self.current_page + 1} に移動しました")
                else:
                    self.ui_service.display_status("最初のページです")
                continue
                
            elif selected_display == "═══════════════════════":
                # 区切り線は無視
                continue
                
            elif selected_display in ('h', 'H'):
                # ヘルプ表示（旧キーサポート）
                self.show_help()
                continue
                
            else:
                # 通常の番組選択
                selected_program = self.get_program_by_display_text(selected_display)
                
                if selected_program:
                    return selected_program
                else:
                    # 番組が見つからない場合はスキップ（区切り線や特殊項目の可能性）
                    continue
                
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
        # 特殊なメニュー項目は番組検索から除外
        special_items = [
            "═══════════════════════",
            "📄 ページ表示に切り替え",
            "📺 全番組表示に切り替え",
            "➡️ 次のページ",
            "⬅️ 前のページ"
        ]
        
        if display_text in special_items:
            return None
        
        # 全表示モードか現在のページかに応じて検索範囲を決定
        if self.show_all_programs:
            search_programs = self.programs
        else:
            search_programs = self.get_current_page_programs()
        
        for program in search_programs:
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
        print("\\n📺 番組選択ヘルプ")
        print("=" * 30)
        print("🎯 基本操作:")
        print("  ↑/↓キー : 番組選択・メニュー移動")
        print("  Enterキー: 選択確定")
        print("  Escキー : 戻る")
        print("  Hキー   : このヘルプ")
        
        print("\\n📱 メニュー操作:")
        print("  メニューに表示される項目を↑↓キーで選択:")
        
        if self.show_all_programs:
            print("  • 番組名 - 録音する番組を選択")
            if len(self.programs) > 30:
                print("  • 📄 ページ表示に切り替え - ページ分割表示に変更")
        else:
            print("  • 番組名 - 録音する番組を選択")
            total_pages = self.get_total_pages()
            if total_pages > 1:
                if self.current_page > 0:
                    print("  • ⬅️ 前のページ - 前のページに移動")
                if self.current_page < total_pages - 1:
                    print("  • ➡️ 次のページ - 次のページに移動")
            print("  • 📺 全番組表示に切り替え - 1日分すべて表示")
        
        print("\\n💡 表示モード:")
        if self.show_all_programs:
            print("  現在: 📺 全番組表示 (1日分すべて表示)")
            print(f"  - {len(self.programs)}番組すべてを一度に表示")
            print("  - 長いリストもスクロールで確認可能")
        else:
            print(f"  現在: 📄 ページ表示 ({self.items_per_page}番組ずつ)")
            print(f"  - 現在 {self.current_page + 1}/{self.get_total_pages()} ページ")
            print("  - メニューで簡単にページ移動")
        
        print("\\n🔍 その他:")
        print("  Iキー   : 番組詳細情報")
        print("  Rキー   : 番組リスト更新")
        
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